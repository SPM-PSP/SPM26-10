import json
import os
import re
import secrets
from sqlalchemy import select, func, text, and_, inspect
from fastapi import APIRouter, HTTPException, Depends, status, Header,Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any, Literal
import uuid # 用于生成唯一ID
import hashlib # 用于密码哈希
import time
from src.backend.core.llm_manager import generate_text_with_qwen3, initialize_llm_runtime, stream_text_with_qwen3
from src.backend.rag_pipeline.vector_store_manager import initialize_vector_store

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.backend.database import (
    User, LessonPlanTimeLog, CorrectionTimeLog, get_db, Resource, Course, UserActivityLog,
    StudentPerformance, Classroom, ClassMember, Paper, PaperSection, PaperQuestion,
    PaperPublication, PaperSubmission, PaperSubmissionAnswer, GeneratedQuestion
)
from src.backend.api.models import (
    LoginRequest, LoginResponse,LessonPlanRequest, LessonPlanResponse,
    AssessmentQuestionRequest, AssessmentQuestionResponse,StudentAnswerCorrectionRequest, CorrectionFeedbackResponse,
    StudentQuestionRequest, StudentQuestionResponse,PracticeQuestionRequest, PracticeQuestionResponse,DashboardMetrics,
    UserCreateRequest, UserCreateResponse, UserResponse,ResourceMetadata, DashboardMetrics,ResourceContentResponse,
UserInfoResponse, ClassCreateRequest, ClassJoinRequest, ClassResponse, ClassDetailResponse,
    ClassMemberResponse, PaperFromLessonPlanRequest, PaperUpdateRequest, PaperPublicationRequest,
    PaperResponse, PaperSectionResponse, PaperQuestionResponse, PaperPublicationResponse,
    StudentPaperListItem, StudentPaperDetailResponse, PaperSubmissionRequest,
    PaperSubmissionResponse, PaperSubmissionAnswerResponse, TeacherPaperSubmissionSummary,
    GeneratedQuestionResponse, GeneratedQuestionSetResponse, LessonPlanDetailResponse,
    LessonPlanUpdateRequest, LessonPlanReviseRequest, AppendGeneratedQuestionsRequest,
    PracticeSubmissionRequest, PracticeSubmissionResponse, PracticeSubmissionAnswerResponse
)
from datetime import datetime, timedelta, timezone

router = APIRouter()


# --- 全局资源初始化（由 main.py 中的 initialize_endpoints_global_resources 填充）---
_vectorstore = None
_embeddings_model = None

# --- 全局内存会话管理---
# 存储 session_id -> User 对象的映射。ps：这在服务器重启后会丢失所有会话！
active_sessions: Dict[str, User] = {}
VALID_QUESTION_TYPES = {"选择题", "填空题", "简答题", "编程题"}

# 简单的密码哈希函数
def hash_password_simple(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password_simple(plain_password: str, hashed_password: str) -> bool:
    return hash_password_simple(plain_password) == hashed_password

# 在 FastAPI 应用启动时调用的初始化函数
def initialize_global_resources():
    global _vectorstore,_embeddings_model

    # 初始化 LLM 运行模式：local 会预加载本地模型，api/hybrid 只校验远程配置
    try:
        initialize_llm_runtime()
        print("LLM 运行时初始化完成。")
    except Exception as e:
        print(f"应用启动时LLM模型预加载失败: {e}")
        raise RuntimeError("LLM 模型预加载失败，应用无法启动。")

    #加载嵌入模型
    try:
        # initialize_vector_store() 内部有单例模式，确保只加载一次
        _vectorstore, _embeddings_model = initialize_vector_store()
        print("向量数据库和嵌入模型已在应用启动时预加载。")
    except Exception as e:
        print(f"警告：向量数据库预加载失败: {e}。RAG 相关功能可能受限。")
        _vectorstore = None  # 如果加载失败，将 _vectorstore 设置为 None，后续 RAG 请求会报错
        # 抛出异常会阻止应用启动
        raise RuntimeError(f"向量数据库预加载失败，RAG 功能无法使用: {e}")

#辅助函数---------------------

#封装对CodeGeeX4的调用，并处理 LLM 侧的异常
async def _get_llm_response(system_instruction: str,user_question: str,retrieved_documents_content: List[str],
        final_instruction: str,max_new_tokens: int | None = None,temperature: float = 0.7,top_p: float = 0.9) -> str:
    try:
        started_at = time.perf_counter()
        response = generate_text_with_qwen3(
            system_instruction=system_instruction,
            user_question=user_question,
            retrieved_documents_content=retrieved_documents_content,
            final_instruction=final_instruction,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p
        )
        elapsed = time.perf_counter() - started_at
        print(f"LLM 生成完成: elapsed={elapsed:.2f}s, docs={len(retrieved_documents_content)}, question_preview={user_question[:60]!r}")
        return response
    except Exception as e:
        print(f"LLM 生成失败: {e}")
        # 这里捕获 generate_text_with_codegeex 内部的异常，转化为 HTTP 500 错误
        raise HTTPException(status_code=500, detail=f"LLM 内容生成失败: {e}")

#封装知识库检索，并处理向量数据库未初始化的情况
async def _get_retrieved_docs(query: str, k: int = 5) -> List[str]:
    global _vectorstore  # 确保访问的是全局变量
    if _vectorstore is None:
        raise HTTPException(status_code=500, detail="向量数据库未初始化或加载失败。RAG 功能不可用。")

    try:
        started_at = time.perf_counter()
        retriever = _vectorstore.as_retriever(search_kwargs={"k": k})
        all_retrieved_docs_objects = retriever.invoke(query)
        docs = [doc.page_content for doc in all_retrieved_docs_objects]
        elapsed = time.perf_counter() - started_at
        first_preview = docs[0][:120].replace("\n", " ") if docs else ""
        print(
            f"Chroma 检索完成: elapsed={elapsed:.2f}s, k={k}, hits={len(docs)}, "
            f"query={query[:60]!r}, first_hit_preview={first_preview!r}"
        )
        return docs
    except Exception as e:
        print(f"知识库检索失败: {e}")
        raise HTTPException(status_code=500, detail=f"知识库检索失败: {e}")

#简易认证依赖：验证 session_id，并返回当前用户对象（服务器重启会话丢失）
async def get_current_user_simple(
    session_id: str = Header(None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db)
) -> User:
    print(f"验证会话: session_id={session_id}")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": "需要会话ID (X-Session-ID) 进行认证"}
        )
    user = active_sessions.get(session_id)
    if not user:
        print(f"未找到会话: session_id={session_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": "会话无效或已过期，请重新登录"}
        )
    result = await db.execute(select(User).filter(User.id == user.id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        print(f"用户不存在: user_id={user.id}")
        del active_sessions[session_id]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": "用户不存在"}
        )
    print(f"会话验证成功: user={db_user.username}")
    return db_user
# 记录用户活动日志
async def _log_user_activity(db: AsyncSession, user_id: uuid.UUID, activity_type: str, details: Optional[Dict[str, Any]] = None):
    new_log = UserActivityLog(
        user_id=user_id,
        activity_type=activity_type,
        metadata_json=details
    )
    db.add(new_log)
    try:
        await db.commit()
        await db.refresh(new_log)
    except Exception as e:
        await db.rollback()
        print(f"Failed to log user activity {activity_type} for user {user_id}: {e}")


def _generate_class_code(length: int = 6) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _create_unique_class_code(db: AsyncSession) -> str:
    while True:
        class_code = _generate_class_code()
        result = await db.execute(select(Classroom).where(Classroom.class_code == class_code))
        if result.scalar_one_or_none() is None:
            return class_code


def _read_resource_file(file_path: Optional[str]) -> str:
    if not file_path:
        return ""
    if not os.path.isabs(file_path):
        file_path = os.path.join(os.getcwd(), file_path)
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def _write_resource_file(file_path: Optional[str], content: str) -> None:
    if not file_path:
        raise HTTPException(status_code=500, detail="资源文件路径无效。")
    if not os.path.isabs(file_path):
        file_path = os.path.join(os.getcwd(), file_path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)


def _delete_resource_file(file_path: Optional[str]) -> None:
    if not file_path:
        return
    if not os.path.isabs(file_path):
        file_path = os.path.join(os.getcwd(), file_path)
    if os.path.exists(file_path):
        os.remove(file_path)


def _extract_markdown_sections(markdown_text: str, max_sections: int = 4) -> List[Dict[str, str]]:
    heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(markdown_text))
    sections: List[Dict[str, str]] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown_text)
        title = match.group(2).strip()
        content = markdown_text[start:end].strip()
        if content:
            sections.append({"title": title, "content": content})
        if len(sections) >= max_sections:
            break

    if sections:
        return sections

    fallback_chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", markdown_text) if chunk.strip()]
    for index, chunk in enumerate(fallback_chunks[:max_sections], start=1):
        sections.append({"title": f"模块 {index}", "content": chunk})
    return sections


def _strip_json_fence(text_value: str) -> str:
    cleaned = text_value.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _normalize_question_type(raw_value: Optional[str], requested_type: str = "简答题") -> Literal["选择题", "填空题", "简答题", "编程题"]:
    if raw_value in VALID_QUESTION_TYPES:
        return raw_value  # type: ignore[return-value]
    if requested_type in VALID_QUESTION_TYPES:
        return requested_type  # type: ignore[return-value]
    return "简答题"


def _normalize_options(raw_value: Any) -> List[str]:
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    if isinstance(raw_value, str) and raw_value.strip():
        return [part.strip() for part in re.split(r"\n+|；|;|\|", raw_value) if part.strip()]
    return []


def _render_questions_markdown(title: str, questions: List[Dict[str, Any]]) -> str:
    lines = [f"# {title}", ""]
    for index, question in enumerate(questions, start=1):
        question_type = str(question.get("question_type") or "简答题")
        question_content = str(question.get("question_content") or "").strip()
        reference_answer = str(question.get("reference_answer") or "").strip()
        options = _normalize_options(question.get("options"))

        lines.append(f"## 题目{index}（{question_type}）")
        lines.append(question_content or "暂无题目内容")

        if question_type == "选择题" and options:
            lines.append("")
            for option_index, option in enumerate(options):
                option_label = chr(ord("A") + option_index)
                lines.append(f"{option_label}. {option}")

        lines.append("")
        lines.append(f"参考答案{index}: {reference_answer or '暂无参考答案'}")
        lines.append("")

    return "\n".join(lines).strip()


def _generated_question_to_response(question: GeneratedQuestion) -> GeneratedQuestionResponse:
    return GeneratedQuestionResponse(
        id=question.id,
        resource_id=question.resource_id,
        question_type=_normalize_question_type(question.question_type),
        question_content=question.question_content,
        options=_normalize_options(question.options_json),
        reference_answer=question.reference_answer,
        score=question.score,
        difficulty_level=question.difficulty_level,
        sort_order=question.sort_order,
        metadata_json=question.metadata_json
    )


def _resource_to_generated_question_set_response(resource: Resource, content: Optional[str] = None) -> GeneratedQuestionSetResponse:
    ordered_questions = sorted(resource.generated_questions or [], key=lambda item: item.sort_order)
    return GeneratedQuestionSetResponse(
        id=resource.id,
        title=resource.title,
        resource_type=resource.resource_type,
        created_by_user_id=resource.created_by_user_id,
        created_at=resource.created_at,
        subject=resource.subject,
        metadata_json=resource.metadata_json,
        content=content if content is not None else _read_resource_file(resource.file_path),
        questions=[_generated_question_to_response(question) for question in ordered_questions]
    )


async def _replace_generated_questions(
    db: AsyncSession,
    resource_id: str,
    questions: List[Dict[str, Any]]
) -> None:
    existing_result = await db.execute(select(GeneratedQuestion).where(GeneratedQuestion.resource_id == resource_id))
    for existing in existing_result.scalars().all():
        await db.delete(existing)

    for index, question in enumerate(questions, start=1):
        db.add(
            GeneratedQuestion(
                resource_id=resource_id,
                question_type=_normalize_question_type(str(question.get("question_type") or "")),
                question_content=str(question.get("question_content") or "").strip(),
                options_json=_normalize_options(question.get("options")),
                reference_answer=str(question.get("reference_answer") or "").strip() or None,
                score=float(question.get("score") or 10.0),
                difficulty_level=str(question.get("difficulty_level") or "").strip() or None,
                sort_order=int(question.get("sort_order") or index),
                metadata_json=question.get("metadata_json") if isinstance(question.get("metadata_json"), dict) else None
            )
        )


async def _generate_structured_questions(
    *,
    topic_or_title: str,
    source_content: str,
    question_type: str,
    difficulty_level: str,
    num_questions: int,
    retrieved_documents_content: List[str]
) -> List[Dict[str, Any]]:
    requested_type = question_type if question_type in VALID_QUESTION_TYPES else "混合"
    type_requirement = (
        "题目类型可以混合，但每一道题的 question_type 字段必须严格填写为“选择题”“填空题”“简答题”或“编程题”之一，绝不能填写“混合”。"
        if requested_type == "混合"
        else f"所有题目的 question_type 字段都必须严格填写为“{requested_type}”。"
    )

    system_instruction = "你是一位严谨的课程命题老师，请严格按 JSON 生成题目数据。"
    user_question = f"""请围绕以下主题生成 {num_questions} 道{difficulty_level}难度题目。

主题：{topic_or_title}
内容材料：
{source_content[:3500] if source_content else topic_or_title}

{type_requirement}

请返回一个 JSON 数组，每个元素必须包含以下字段：
- question_type
- question_content
- options（仅选择题需要，其他题型返回空数组）
- reference_answer
- score
- difficulty_level

要求：
1. 只返回合法 JSON。
2. 选择题必须提供 4 个选项。
3. 不能把“混合”当作具体题型值。
4. 编程题的参考答案可以是关键代码或核心思路。
"""
    final_instruction = "只返回合法 JSON 数组，不要输出任何解释。"

    llm_response = await _get_llm_response(
        system_instruction=system_instruction,
        user_question=user_question,
        retrieved_documents_content=retrieved_documents_content,
        final_instruction=final_instruction,
        max_new_tokens=None,
        temperature=0.5,
        top_p=0.8
    )
    cleaned = _strip_json_fence(llm_response)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            normalized: List[Dict[str, Any]] = []
            for index, item in enumerate(parsed[:num_questions], start=1):
                if not isinstance(item, dict):
                    continue
                actual_type = _normalize_question_type(str(item.get("question_type") or ""), requested_type if requested_type != "混合" else "简答题")
                options = _normalize_options(item.get("options"))
                if actual_type == "选择题" and len(options) < 2:
                    options = ["选项A", "选项B", "选项C", "选项D"]
                normalized.append(
                    {
                        "question_type": actual_type,
                        "question_content": str(item.get("question_content") or "").strip(),
                        "options": options if actual_type == "选择题" else [],
                        "reference_answer": str(item.get("reference_answer") or "").strip(),
                        "score": float(item.get("score") or 10),
                        "difficulty_level": str(item.get("difficulty_level") or difficulty_level),
                        "sort_order": index
                    }
                )
            if normalized:
                return normalized
    except Exception as exc:
        print(f"解析结构化题目 JSON 失败: {exc}")

    fallback_questions: List[Dict[str, Any]] = []
    fallback_types = [requested_type] if requested_type in VALID_QUESTION_TYPES else ["选择题", "填空题", "简答题", "编程题"]
    for index in range(num_questions):
        actual_type = fallback_types[index % len(fallback_types)]
        fallback_questions.append(
            {
                "question_type": actual_type,
                "question_content": f"{topic_or_title} - 题目 {index + 1}\n请围绕给定内容进行作答。",
                "options": ["选项A", "选项B", "选项C", "选项D"] if actual_type == "选择题" else [],
                "reference_answer": source_content[:400] or topic_or_title,
                "score": 10.0,
                "difficulty_level": difficulty_level,
                "sort_order": index + 1
            }
        )
    return fallback_questions


async def _generate_questions_for_section(
    section_title: str,
    section_content: str,
    question_type: str,
    difficulty_level: str,
    questions_per_section: int
) -> List[Dict[str, Any]]:
    return await _generate_structured_questions(
        topic_or_title=section_title,
        source_content=section_content,
        question_type=question_type,
        difficulty_level=difficulty_level,
        num_questions=questions_per_section,
        retrieved_documents_content=[]
    )


async def _grade_answer_with_model(
    *,
    question_type: str,
    question_content: str,
    reference_answer: Optional[str],
    score: float,
    student_answer: str,
    options: Optional[List[str]] = None
) -> Dict[str, Any]:
    system_instruction = "你是一位严格的课程阅卷老师，请根据题目和参考答案对学生答案评分，并返回 JSON。"
    max_score = float(score)
    option_text = ""
    if options:
        option_text = "\n".join([f"{chr(ord('A') + idx)}. {item}" for idx, item in enumerate(options)])
    user_question = f"""请批改以下试卷题目答案。

题目类型：{question_type}
题目内容：{question_content}
{f"选项：{option_text}" if option_text else ""}
参考答案：{reference_answer or '无'}
题目满分：{score}
学生答案：{student_answer}

请返回一个 JSON 对象，字段如下：
- score：数值，范围 0 到 {score}
- is_correct：布尔值
- auto_feedback：文字反馈
- error_tags_json：对象，至少包含 errors 数组和 summary 字段

不要输出任何解释，只返回 JSON。"""
    final_instruction = "只返回合法 JSON 对象。"
    llm_response = await _get_llm_response(
        system_instruction=system_instruction,
        user_question=user_question,
        retrieved_documents_content=[],
        final_instruction=final_instruction,
        max_new_tokens=None,
        temperature=0.3,
        top_p=0.8
    )
    cleaned = _strip_json_fence(llm_response)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            parsed_score = float(parsed.get("score", 0))
            parsed_score = max(0.0, min(parsed_score, max_score))
            return {
                "score": parsed_score,
                "is_correct": bool(parsed.get("is_correct", parsed_score >= max_score * 0.6)),
                "auto_feedback": str(parsed.get("auto_feedback") or "").strip(),
                "error_tags_json": parsed.get("error_tags_json") if isinstance(parsed.get("error_tags_json"), dict) else None
            }
    except Exception as exc:
        print(f"解析批改 JSON 失败: {exc}")

    return {
        "score": 0.0,
        "is_correct": False,
        "auto_feedback": "系统未能稳定解析本题批改结果，请教师复核。",
        "error_tags_json": {"errors": ["批改解析失败"], "summary": "需要人工复核"}
    }


async def _grade_paper_answer(question: PaperQuestion, student_answer: str) -> Dict[str, Any]:
    return await _grade_answer_with_model(
        question_type=question.question_type,
        question_content=question.question_content,
        reference_answer=question.reference_answer,
        score=float(question.score),
        student_answer=student_answer,
        options=_normalize_options((question.metadata_json or {}).get("options")) if isinstance(question.metadata_json, dict) else None
    )


def _paper_question_to_response(question: PaperQuestion) -> PaperQuestionResponse:
    return PaperQuestionResponse(
        id=question.id,
        question_type=question.question_type,
        question_content=question.question_content,
        reference_answer=question.reference_answer,
        score=question.score,
        difficulty_level=question.difficulty_level,
        sort_order=question.sort_order,
        metadata_json=question.metadata_json
    )


def _paper_section_to_response(section: PaperSection) -> PaperSectionResponse:
    questions = sorted(section.questions, key=lambda item: item.sort_order)
    return PaperSectionResponse(
        id=section.id,
        section_title=section.section_title,
        source_module_name=section.source_module_name,
        sort_order=section.sort_order,
        questions=[_paper_question_to_response(question) for question in questions]
    )


def _paper_to_response(paper: Paper) -> PaperResponse:
    sections = sorted(paper.sections, key=lambda item: item.sort_order)
    state = inspect(paper)
    publication_count = 0 if "publications" in state.unloaded else len(paper.publications or [])
    return PaperResponse(
        id=paper.id,
        title=paper.title,
        source_resource_id=paper.source_resource_id,
        created_by_teacher_id=paper.created_by_teacher_id,
        class_id=paper.class_id,
        status=paper.status,
        total_score=paper.total_score,
        metadata_json=paper.metadata_json,
        created_at=paper.created_at,
        updated_at=paper.updated_at,
        sections=[_paper_section_to_response(section) for section in sections],
        publication_count=publication_count
    )


def _paper_to_student_response(paper: Paper) -> PaperResponse:
    base_response = _paper_to_response(paper)
    sanitized_sections: List[PaperSectionResponse] = []
    for section in base_response.sections:
        sanitized_sections.append(
            PaperSectionResponse(
                id=section.id,
                section_title=section.section_title,
                source_module_name=section.source_module_name,
                sort_order=section.sort_order,
                questions=[
                    PaperQuestionResponse(
                        id=question.id,
                        question_type=question.question_type,
                        question_content=question.question_content,
                        reference_answer=None,
                        score=question.score,
                        difficulty_level=question.difficulty_level,
                        sort_order=question.sort_order,
                        metadata_json=question.metadata_json
                    )
                    for question in section.questions
                ]
            )
        )
    return PaperResponse(**base_response.model_dump(exclude={"sections"}), sections=sanitized_sections)


def _class_to_response(classroom: Classroom, member_count: Optional[int] = None) -> ClassResponse:
    state = inspect(classroom)
    teacher = None if "teacher" in state.unloaded else classroom.teacher
    members = [] if "members" in state.unloaded else list(classroom.members or [])
    active_members = [member for member in members if member.status == "active"]
    return ClassResponse(
        id=classroom.id,
        name=classroom.name,
        description=classroom.description,
        class_code=classroom.class_code,
        teacher_id=classroom.teacher_id,
        teacher_name=teacher.username if teacher else None,
        status=classroom.status,
        created_at=classroom.created_at,
        updated_at=classroom.updated_at,
        member_count=member_count if member_count is not None else len(active_members)
    )

# 认证接口-----------------------
#用户登录接口（对应前端fetchLogin)
#成功后返回一个临时的会话ID (Session ID)；请将此 Session ID 存储在前端，并在后续请求中通过 X-Session-ID 头发送
@router.post("/login", response_model=LoginResponse, summary="用户登录并获取会话ID")
async def login_api(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    print(f"Attempting login for username: {request.username}")
    try:
        user_result = await db.execute(select(User).filter(User.username == request.username))
        user = user_result.scalar_one_or_none()
        if not user:
            print(f"User '{request.username}' not found in database.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": 401, "message": "用户名或密码不正确"}
            )
        is_password_correct = verify_password_simple(request.password, user.hashed_password)
        if not is_password_correct:
            print(f"Password verification failed for user '{user.username}'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": 401, "message": "用户名或密码不正确"}
            )
        session_id = str(uuid.uuid4())
        active_sessions[session_id] = user  # 暂时保留内存存储，建议替换为数据库/Redis
        print(f"用户 {user.username} 登录成功，会话ID: {session_id}")
        return LoginResponse(
            status="success",
            message="登录成功",
            session_id=session_id
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"登录过程中发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "message": f"服务器内部错误: {str(e)}"}
        )

#用户信息接口（对应前端fetchUserInfo）
@router.get("/getUserInfo", response_model=UserInfoResponse)
async def get_user_info(session_id: str = Header(..., alias="X-Session-ID")):
    user = active_sessions.get(session_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话无效或已过期"
        )
    print(f"获取用户信息请求，当前用户: {user.username}")
    return UserInfoResponse(
        userId=user.id,
        userName=user.username,
        userRole=user.role
    )

#用户注销接口，清除服务器内存中的会话
@router.post("/logout", summary="用户注销会话")
async def logout_api(session_id: str = Header(..., alias="X-Session-ID")):
    """
    用户注销接口，清除服务器内存中的会话。
    """
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"status": "success", "message": "注销成功。"}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的会话ID。")

# 班级与试卷 API-----------------

@router.post("/teacher/classes", response_model=ClassResponse, summary="教师创建班级")
async def create_class_api(
    request: ClassCreateRequest,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无教师或管理员权限。")

    classroom = Classroom(
        name=request.name,
        description=request.description,
        class_code=await _create_unique_class_code(db),
        teacher_id=current_user.id,
        status="active"
    )
    db.add(classroom)
    await db.commit()
    await db.refresh(classroom)
    await _log_user_activity(db, current_user.id, "create_class", {"class_id": classroom.id, "class_code": classroom.class_code})
    return _class_to_response(classroom, member_count=0)


@router.get("/teacher/classes", response_model=List[ClassResponse], summary="教师获取自己的班级列表")
async def get_teacher_classes_api(
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无教师或管理员权限。")

    query = select(Classroom).options(selectinload(Classroom.teacher), selectinload(Classroom.members))
    if current_user.role == "teacher":
        query = query.where(Classroom.teacher_id == current_user.id)
    query = query.where(Classroom.status != "dissolved")
    result = await db.execute(query.order_by(Classroom.created_at.desc()))
    classrooms = result.scalars().unique().all()
    return [_class_to_response(classroom) for classroom in classrooms]


@router.get("/teacher/classes/{class_id}", response_model=ClassDetailResponse, summary="教师获取班级详情和成员")
async def get_teacher_class_detail_api(
    class_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无教师或管理员权限。")

    result = await db.execute(
        select(Classroom)
        .options(selectinload(Classroom.teacher), selectinload(Classroom.members).selectinload(ClassMember.student))
        .where(Classroom.id == class_id)
    )
    classroom = result.scalar_one_or_none()
    if classroom is None:
        raise HTTPException(status_code=404, detail="班级不存在。")
    if classroom.status == "dissolved":
        raise HTTPException(status_code=400, detail="班级已解散。")
    if current_user.role == "teacher" and classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该班级。")

    members = [
        ClassMemberResponse(
            id=member.id,
            student_id=member.student_id,
            student_name=member.student.username if member.student else f"学生{member.student_id}",
            joined_at=member.joined_at,
            status=member.status
        )
        for member in classroom.members if member.status == "active"
    ]
    base = _class_to_response(classroom)
    return ClassDetailResponse(**base.model_dump(), members=members)


@router.post("/teacher/classes/{class_id}/dissolve", response_model=ClassResponse, summary="教师解散班级")
async def dissolve_teacher_class_api(
    class_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    result = await db.execute(
        select(Classroom).options(selectinload(Classroom.teacher), selectinload(Classroom.members)).where(Classroom.id == class_id)
    )
    classroom = result.scalar_one_or_none()
    if classroom is None:
        raise HTTPException(status_code=404, detail="班级不存在。")
    if current_user.role == "teacher" and classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权解散该班级。")
    if classroom.status == "dissolved":
        return _class_to_response(classroom, member_count=0)

    classroom.status = "dissolved"
    for member in classroom.members:
        if member.status == "active":
            member.status = "removed"

    await db.commit()
    await db.refresh(classroom)
    await _log_user_activity(db, current_user.id, "dissolve_class", {"class_id": class_id})
    return _class_to_response(classroom, member_count=0)


@router.delete("/teacher/classes/{class_id}/members/{student_id}", response_model=ClassDetailResponse, summary="教师移除班级成员")
async def remove_student_from_class_api(
    class_id: str,
    student_id: int,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    result = await db.execute(
        select(Classroom)
        .options(selectinload(Classroom.teacher), selectinload(Classroom.members).selectinload(ClassMember.student))
        .where(Classroom.id == class_id)
    )
    classroom = result.scalar_one_or_none()
    if classroom is None:
        raise HTTPException(status_code=404, detail="班级不存在。")
    if current_user.role == "teacher" and classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权管理该班级成员。")

    target_member = next((member for member in classroom.members if member.student_id == student_id and member.status == "active"), None)
    if target_member is None:
        raise HTTPException(status_code=404, detail="该学生不在当前班级中。")

    target_member.status = "removed"
    await db.commit()
    await db.refresh(classroom)
    await _log_user_activity(db, current_user.id, "remove_class_member", {"class_id": class_id, "student_id": student_id})

    members = [
        ClassMemberResponse(
            id=member.id,
            student_id=member.student_id,
            student_name=member.student.username if member.student else f"学生{member.student_id}",
            joined_at=member.joined_at,
            status=member.status
        )
        for member in classroom.members if member.status == "active"
    ]
    return ClassDetailResponse(**_class_to_response(classroom).model_dump(), members=members)


@router.post("/student/classes/join", response_model=ClassResponse, summary="学生通过班级码加入班级")
async def join_class_api(
    request: ClassJoinRequest,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可加入班级。")

    result = await db.execute(
        select(Classroom).options(selectinload(Classroom.teacher), selectinload(Classroom.members))
        .where(Classroom.class_code == request.class_code.upper())
    )
    classroom = result.scalar_one_or_none()
    if classroom is None:
        raise HTTPException(status_code=404, detail="班级码无效。")
    if classroom.status == "dissolved":
        raise HTTPException(status_code=400, detail="该班级已解散，无法加入。")

    exists_result = await db.execute(
        select(ClassMember).where(ClassMember.class_id == classroom.id, ClassMember.student_id == current_user.id)
    )
    existing_member = exists_result.scalar_one_or_none()
    if existing_member:
        if existing_member.status == "active":
            raise HTTPException(status_code=400, detail="你已加入该班级。")
        existing_member.status = "active"
        existing_member.joined_at = datetime.now(timezone.utc)
    else:
        db.add(ClassMember(class_id=classroom.id, student_id=current_user.id, status="active"))
    await db.commit()
    await db.refresh(classroom)
    await _log_user_activity(db, current_user.id, "join_class", {"class_id": classroom.id, "class_code": classroom.class_code})
    active_member_count = len([member for member in (classroom.members or []) if member.status == "active"]) + (0 if existing_member else 1)
    return _class_to_response(classroom, member_count=active_member_count)


@router.get("/student/classes", response_model=List[ClassResponse], summary="学生获取已加入班级列表")
async def get_student_classes_api(
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可查看自己的班级。")

    result = await db.execute(
        select(ClassMember)
        .options(selectinload(ClassMember.classroom).selectinload(Classroom.teacher), selectinload(ClassMember.classroom).selectinload(Classroom.members))
        .where(ClassMember.student_id == current_user.id, ClassMember.status == "active")
        .order_by(ClassMember.joined_at.desc())
    )
    memberships = result.scalars().all()
    return [_class_to_response(member.classroom) for member in memberships if member.classroom and member.classroom.status == "active"]


@router.post("/student/classes/{class_id}/leave", response_model=ClassResponse, summary="学生退出班级")
async def leave_class_api(
    class_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可退出班级。")

    class_result = await db.execute(select(Classroom).options(selectinload(Classroom.teacher), selectinload(Classroom.members)).where(Classroom.id == class_id))
    classroom = class_result.scalar_one_or_none()
    if classroom is None:
        raise HTTPException(status_code=404, detail="班级不存在。")

    membership_result = await db.execute(
        select(ClassMember).where(ClassMember.class_id == class_id, ClassMember.student_id == current_user.id, ClassMember.status == "active")
    )
    membership = membership_result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=400, detail="你当前不在该班级中。")

    membership.status = "left"
    await db.commit()
    await db.refresh(classroom)
    await _log_user_activity(db, current_user.id, "leave_class", {"class_id": class_id})
    return _class_to_response(classroom)


@router.get("/teacher/resources", response_model=List[ResourceMetadata], summary="教师获取自己的资源列表")
async def get_teacher_resources_api(
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db),
    resource_type: Optional[str] = Query(None)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    query = select(Resource)
    if current_user.role == "teacher":
        query = query.where(Resource.created_by_user_id == current_user.id)
    if resource_type:
        query = query.where(Resource.resource_type == resource_type)

    result = await db.execute(query.order_by(Resource.created_at.desc()))
    resources = result.scalars().all()
    return [ResourceMetadata.model_validate(resource) for resource in resources]


@router.get("/teacher/lesson-plans", response_model=List[LessonPlanDetailResponse], summary="教师获取教学计划列表")
async def get_teacher_lesson_plans_api(
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    query = select(Resource).where(Resource.resource_type == "lesson_plan")
    if current_user.role == "teacher":
        query = query.where(Resource.created_by_user_id == current_user.id)

    result = await db.execute(query.order_by(Resource.created_at.desc()))
    resources = result.scalars().all()
    return [
        LessonPlanDetailResponse(
            id=resource.id,
            title=resource.title,
            created_by_user_id=resource.created_by_user_id,
            created_at=resource.created_at,
            metadata_json=resource.metadata_json,
            subject=resource.subject,
            content=_read_resource_file(resource.file_path)
        )
        for resource in resources
    ]


@router.get("/teacher/lesson-plans/{resource_id}", response_model=LessonPlanDetailResponse, summary="教师获取教学计划详情")
async def get_teacher_lesson_plan_detail_api(
    resource_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    result = await db.execute(select(Resource).where(Resource.id == resource_id, Resource.resource_type == "lesson_plan"))
    resource = result.scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=404, detail="教学计划不存在。")
    if current_user.role == "teacher" and resource.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该教学计划。")

    return LessonPlanDetailResponse(
        id=resource.id,
        title=resource.title,
        created_by_user_id=resource.created_by_user_id,
        created_at=resource.created_at,
        metadata_json=resource.metadata_json,
        subject=resource.subject,
        content=_read_resource_file(resource.file_path)
    )


@router.put("/teacher/lesson-plans/{resource_id}", response_model=LessonPlanDetailResponse, summary="教师手动修改教学计划")
async def update_teacher_lesson_plan_api(
    resource_id: str,
    request: LessonPlanUpdateRequest,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    result = await db.execute(select(Resource).where(Resource.id == resource_id, Resource.resource_type == "lesson_plan"))
    resource = result.scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=404, detail="教学计划不存在。")
    if current_user.role == "teacher" and resource.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改该教学计划。")

    _write_resource_file(resource.file_path, request.content)
    resource.title = request.title
    metadata = dict(resource.metadata_json or {})
    metadata["last_manual_update_at"] = datetime.now(timezone.utc).isoformat()
    resource.metadata_json = metadata
    await db.commit()
    await db.refresh(resource)
    await _log_user_activity(db, current_user.id, "update_lesson_plan", {"resource_id": resource.id})

    return LessonPlanDetailResponse(
        id=resource.id,
        title=resource.title,
        created_by_user_id=resource.created_by_user_id,
        created_at=resource.created_at,
        metadata_json=resource.metadata_json,
        subject=resource.subject,
        content=request.content
    )


@router.post("/teacher/lesson-plans/{resource_id}/revise", response_model=LessonPlanDetailResponse, summary="教师基于意见二次修改教学计划")
async def revise_teacher_lesson_plan_api(
    resource_id: str,
    request: LessonPlanReviseRequest,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    result = await db.execute(select(Resource).where(Resource.id == resource_id, Resource.resource_type == "lesson_plan"))
    resource = result.scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=404, detail="教学计划不存在。")
    if current_user.role == "teacher" and resource.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改该教学计划。")

    original_content = _read_resource_file(resource.file_path)
    if not original_content:
        raise HTTPException(status_code=400, detail="教学计划内容为空，无法继续修改。")

    revised_content = await _get_llm_response(
        system_instruction="你是一位严谨的教学设计专家，请根据原教学计划和修改意见，输出完整的新教学计划。",
        user_question=f"""原教学计划如下：
{original_content}

修改意见如下：
{request.revision_instruction}

请在保留原教学目标完整性的前提下，根据修改意见输出一份完整的新教学计划。""",
        retrieved_documents_content=[],
        final_instruction="请直接输出完整的新教学计划 Markdown 内容，不要附加解释。",
        max_new_tokens=None,
        temperature=0.6,
        top_p=0.9
    )

    if request.save_as_new:
        new_resource_id = str(uuid.uuid4())
        file_dir = "generated_resources/lesson_plans"
        os.makedirs(file_dir, exist_ok=True)
        new_file_path = os.path.join(file_dir, f"{new_resource_id}.md")
        _write_resource_file(new_file_path, revised_content)
        new_resource = Resource(
            id=new_resource_id,
            title=request.title or f"{resource.title} - 修订版",
            resource_type="lesson_plan",
            created_by_user_id=current_user.id,
            file_path=new_file_path,
            metadata_json={**(resource.metadata_json or {}), "revision_of": resource.id, "revision_instruction": request.revision_instruction},
            subject=resource.subject
        )
        db.add(new_resource)
        await db.commit()
        await db.refresh(new_resource)
        await _log_user_activity(db, current_user.id, "revise_lesson_plan", {"resource_id": new_resource.id, "source_resource_id": resource.id})
        return LessonPlanDetailResponse(
            id=new_resource.id,
            title=new_resource.title,
            created_by_user_id=new_resource.created_by_user_id,
            created_at=new_resource.created_at,
            metadata_json=new_resource.metadata_json,
            subject=new_resource.subject,
            content=revised_content
        )

    _write_resource_file(resource.file_path, revised_content)
    if request.title:
        resource.title = request.title
    metadata = dict(resource.metadata_json or {})
    metadata["last_revision_instruction"] = request.revision_instruction
    metadata["last_revision_at"] = datetime.now(timezone.utc).isoformat()
    resource.metadata_json = metadata
    await db.commit()
    await db.refresh(resource)
    await _log_user_activity(db, current_user.id, "revise_lesson_plan", {"resource_id": resource.id})
    return LessonPlanDetailResponse(
        id=resource.id,
        title=resource.title,
        created_by_user_id=resource.created_by_user_id,
        created_at=resource.created_at,
        metadata_json=resource.metadata_json,
        subject=resource.subject,
        content=revised_content
    )


@router.delete("/teacher/lesson-plans/{resource_id}", response_model=UserCreateResponse, summary="教师删除教学计划")
async def delete_teacher_lesson_plan_api(
    resource_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    result = await db.execute(select(Resource).where(Resource.id == resource_id, Resource.resource_type == "lesson_plan"))
    resource = result.scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=404, detail="教学计划不存在。")
    if current_user.role == "teacher" and resource.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除该教学计划。")

    paper_result = await db.execute(select(func.count(Paper.id)).where(Paper.source_resource_id == resource_id, Paper.status != "deleted"))
    if (paper_result.scalar_one_or_none() or 0) > 0:
        raise HTTPException(status_code=400, detail="该教学计划已被试卷引用，请先删除或调整相关试卷。")

    _delete_resource_file(resource.file_path)
    await db.delete(resource)
    await db.commit()
    await _log_user_activity(db, current_user.id, "delete_lesson_plan", {"resource_id": resource_id})
    return UserCreateResponse(status="success", message="教学计划删除成功。")


@router.get("/teacher/generated-assessments", response_model=List[GeneratedQuestionSetResponse], summary="教师获取已生成考核题列表")
async def get_teacher_generated_assessments_api(
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    query = select(Resource).options(selectinload(Resource.generated_questions)).where(Resource.resource_type == "assessment")
    if current_user.role == "teacher":
        query = query.where(Resource.created_by_user_id == current_user.id)
    result = await db.execute(query.order_by(Resource.created_at.desc()))
    resources = result.scalars().unique().all()
    return [_resource_to_generated_question_set_response(resource) for resource in resources]


@router.get("/teacher/generated-assessments/{resource_id}", response_model=GeneratedQuestionSetResponse, summary="教师获取考核题详情")
async def get_teacher_generated_assessment_detail_api(
    resource_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    result = await db.execute(
        select(Resource).options(selectinload(Resource.generated_questions)).where(Resource.id == resource_id, Resource.resource_type == "assessment")
    )
    resource = result.scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=404, detail="考核题资源不存在。")
    if current_user.role == "teacher" and resource.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该考核题资源。")
    return _resource_to_generated_question_set_response(resource)


@router.delete("/teacher/generated-assessments/{resource_id}", response_model=UserCreateResponse, summary="教师删除已生成考核题")
async def delete_teacher_generated_assessment_api(
    resource_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    result = await db.execute(
        select(Resource).options(selectinload(Resource.generated_questions)).where(Resource.id == resource_id, Resource.resource_type == "assessment")
    )
    resource = result.scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=404, detail="考核题资源不存在。")
    if current_user.role == "teacher" and resource.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除该考核题资源。")

    _delete_resource_file(resource.file_path)
    for question in resource.generated_questions or []:
        await db.delete(question)
    await db.delete(resource)
    await db.commit()
    await _log_user_activity(db, current_user.id, "delete_generated_assessment", {"resource_id": resource_id})
    return UserCreateResponse(status="success", message="考核题删除成功。")


@router.get("/student/generated-practices", response_model=List[GeneratedQuestionSetResponse], summary="学生获取已生成练习列表")
async def get_student_generated_practices_api(
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可查看自己的练习。")

    result = await db.execute(
        select(Resource)
        .options(selectinload(Resource.generated_questions))
        .where(Resource.resource_type == "practice", Resource.created_by_user_id == current_user.id)
        .order_by(Resource.created_at.desc())
    )
    resources = result.scalars().unique().all()
    return [_resource_to_generated_question_set_response(resource) for resource in resources]


@router.get("/student/generated-practices/{resource_id}", response_model=GeneratedQuestionSetResponse, summary="学生获取练习详情")
async def get_student_generated_practice_detail_api(
    resource_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可查看自己的练习。")

    result = await db.execute(
        select(Resource)
        .options(selectinload(Resource.generated_questions))
        .where(Resource.id == resource_id, Resource.resource_type == "practice", Resource.created_by_user_id == current_user.id)
    )
    resource = result.scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=404, detail="练习资源不存在。")
    return _resource_to_generated_question_set_response(resource)


@router.delete("/student/generated-practices/{resource_id}", response_model=UserCreateResponse, summary="学生删除已生成练习")
async def delete_student_generated_practice_api(
    resource_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可删除自己的练习。")

    result = await db.execute(
        select(Resource)
        .options(selectinload(Resource.generated_questions))
        .where(Resource.id == resource_id, Resource.resource_type == "practice", Resource.created_by_user_id == current_user.id)
    )
    resource = result.scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=404, detail="练习资源不存在。")

    _delete_resource_file(resource.file_path)
    for question in resource.generated_questions or []:
        await db.delete(question)
    await db.delete(resource)
    await db.commit()
    await _log_user_activity(db, current_user.id, "delete_generated_practice", {"resource_id": resource_id})
    return UserCreateResponse(status="success", message="练习删除成功。")


@router.post("/teacher/papers/from-lesson-plan", response_model=PaperResponse, summary="教师基于教学计划生成试卷草稿")
async def create_paper_from_lesson_plan_api(
    request: PaperFromLessonPlanRequest,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    resource_result = await db.execute(select(Resource).where(Resource.id == request.source_resource_id))
    resource = resource_result.scalar_one_or_none()
    if resource is None or resource.resource_type != "lesson_plan":
        raise HTTPException(status_code=404, detail="教学计划资源不存在。")
    if current_user.role == "teacher" and resource.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权使用该教学计划生成试卷。")

    lesson_plan_content = _read_resource_file(resource.file_path)
    if not lesson_plan_content:
        raise HTTPException(status_code=400, detail="教学计划内容为空或文件不存在。")

    sections_data = _extract_markdown_sections(lesson_plan_content, max_sections=request.max_sections)
    if not sections_data:
        raise HTTPException(status_code=400, detail="未能从教学计划中提取有效模块。")

    paper = Paper(
        title=request.title or f"{resource.title} - 试卷草稿",
        source_resource_id=resource.id,
        created_by_teacher_id=current_user.id,
        status="draft",
        metadata_json={
            "question_type": request.question_type,
            "difficulty_level": request.difficulty_level,
            "questions_per_section": request.questions_per_section
        }
    )
    db.add(paper)
    await db.flush()

    total_score = 0.0
    for section_index, section_data in enumerate(sections_data, start=1):
        paper_section = PaperSection(
            paper_id=paper.id,
            section_title=section_data["title"],
            source_module_name=section_data["title"],
            sort_order=section_index
        )
        db.add(paper_section)
        await db.flush()

        generated_questions = await _generate_questions_for_section(
            section_title=section_data["title"],
            section_content=section_data["content"],
            question_type=request.question_type,
            difficulty_level=request.difficulty_level,
            questions_per_section=request.questions_per_section
        )

        for question_index, question_data in enumerate(generated_questions, start=1):
            score = float(question_data.get("score") or 10.0)
            total_score += score
            db.add(
                PaperQuestion(
                    paper_id=paper.id,
                    section_id=paper_section.id,
                    question_type=_normalize_question_type(question_data.get("question_type"), "简答题"),
                    question_content=question_data["question_content"],
                    reference_answer=question_data.get("reference_answer"),
                    score=score,
                    difficulty_level=question_data.get("difficulty_level"),
                    sort_order=question_index,
                    metadata_json={
                        "source_module_name": section_data["title"],
                        "options": _normalize_options(question_data.get("options"))
                    }
                )
            )

    paper.total_score = total_score
    await db.commit()

    result = await db.execute(
        select(Paper)
        .options(
            selectinload(Paper.sections).selectinload(PaperSection.questions),
            selectinload(Paper.publications)
        )
        .where(Paper.id == paper.id)
    )
    created_paper = result.scalar_one()
    await _log_user_activity(db, current_user.id, "create_paper_from_lesson_plan", {"paper_id": created_paper.id, "resource_id": resource.id})
    return _paper_to_response(created_paper)


@router.get("/teacher/papers", response_model=List[PaperResponse], summary="教师获取试卷列表")
async def get_teacher_papers_api(
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    query = select(Paper).options(
        selectinload(Paper.sections).selectinload(PaperSection.questions),
        selectinload(Paper.publications)
    )
    if current_user.role == "teacher":
        query = query.where(Paper.created_by_teacher_id == current_user.id)
    query = query.where(Paper.status != "deleted")
    result = await db.execute(query.order_by(Paper.created_at.desc()))
    papers = result.scalars().unique().all()
    return [_paper_to_response(paper) for paper in papers]


@router.get("/teacher/papers/{paper_id}", response_model=PaperResponse, summary="教师获取试卷详情")
async def get_teacher_paper_detail_api(
    paper_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    result = await db.execute(
        select(Paper)
        .options(
            selectinload(Paper.sections).selectinload(PaperSection.questions),
            selectinload(Paper.publications)
        )
        .where(Paper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    if paper is None:
        raise HTTPException(status_code=404, detail="试卷不存在。")
    if current_user.role == "teacher" and paper.created_by_teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该试卷。")
    return _paper_to_response(paper)


@router.put("/teacher/papers/{paper_id}", response_model=PaperResponse, summary="教师修改试卷草稿")
async def update_teacher_paper_api(
    paper_id: str,
    request: PaperUpdateRequest,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    result = await db.execute(
        select(Paper)
        .options(selectinload(Paper.sections).selectinload(PaperSection.questions), selectinload(Paper.publications))
        .where(Paper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    if paper is None:
        raise HTTPException(status_code=404, detail="试卷不存在。")
    if current_user.role == "teacher" and paper.created_by_teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改该试卷。")

    paper.title = request.title
    if request.status:
        paper.status = request.status

    for existing_section in paper.sections:
        for existing_question in existing_section.questions:
            await db.delete(existing_question)
        await db.delete(existing_section)
    await db.flush()

    total_score = 0.0
    for section_index, section_input in enumerate(request.sections, start=1):
        section = PaperSection(
            paper_id=paper.id,
            section_title=section_input.section_title,
            source_module_name=section_input.source_module_name,
            sort_order=section_input.sort_order or section_index
        )
        db.add(section)
        await db.flush()
        for question_index, question_input in enumerate(section_input.questions, start=1):
            total_score += float(question_input.score)
            db.add(
                PaperQuestion(
                    paper_id=paper.id,
                    section_id=section.id,
                    question_type=_normalize_question_type(question_input.question_type, "简答题"),
                    question_content=question_input.question_content,
                    reference_answer=question_input.reference_answer,
                    score=question_input.score,
                    difficulty_level=question_input.difficulty_level,
                    sort_order=question_input.sort_order or question_index,
                    metadata_json={
                        **(question_input.metadata_json or {}),
                        "options": _normalize_options((question_input.metadata_json or {}).get("options"))
                    }
                )
            )

    paper.total_score = total_score
    await db.commit()
    refreshed = await db.execute(
        select(Paper)
        .options(selectinload(Paper.sections).selectinload(PaperSection.questions), selectinload(Paper.publications))
        .where(Paper.id == paper.id)
    )
    updated_paper = refreshed.scalar_one()
    return _paper_to_response(updated_paper)


@router.post("/teacher/papers/{paper_id}/append-generated-questions", response_model=PaperResponse, summary="教师将已生成考核题追加到试卷草稿")
async def append_generated_questions_to_paper_api(
    paper_id: str,
    request: AppendGeneratedQuestionsRequest,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    paper_result = await db.execute(
        select(Paper).options(selectinload(Paper.sections).selectinload(PaperSection.questions), selectinload(Paper.publications)).where(Paper.id == paper_id)
    )
    paper = paper_result.scalar_one_or_none()
    if paper is None:
        raise HTTPException(status_code=404, detail="试卷不存在。")
    if current_user.role == "teacher" and paper.created_by_teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改该试卷。")
    if paper.status != "draft":
        raise HTTPException(status_code=400, detail="只有草稿试卷可以追加题目。")

    resource_result = await db.execute(
        select(Resource)
        .options(selectinload(Resource.generated_questions))
        .where(Resource.id == request.resource_id, Resource.resource_type == "assessment")
    )
    resource = resource_result.scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=404, detail="未找到可追加的考核题资源。")
    if current_user.role == "teacher" and resource.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能追加自己生成的考核题。")

    generated_questions = sorted(resource.generated_questions or [], key=lambda item: item.sort_order)
    if not generated_questions:
        raise HTTPException(status_code=400, detail="该考核题资源没有结构化题目，无法追加。")

    next_section_order = max([section.sort_order for section in paper.sections] or [0]) + 1
    section = PaperSection(
        paper_id=paper.id,
        section_title=request.section_title or resource.title,
        source_module_name=resource.title,
        sort_order=next_section_order
    )
    db.add(section)
    await db.flush()

    total_score = paper.total_score
    for question_index, generated_question in enumerate(generated_questions, start=1):
        total_score += float(generated_question.score)
        db.add(
            PaperQuestion(
                paper_id=paper.id,
                section_id=section.id,
                question_type=generated_question.question_type,
                question_content=generated_question.question_content,
                reference_answer=generated_question.reference_answer,
                score=generated_question.score,
                difficulty_level=generated_question.difficulty_level,
                sort_order=question_index,
                metadata_json={
                    **(generated_question.metadata_json or {}),
                    "options": _normalize_options(generated_question.options_json),
                    "generated_resource_id": resource.id
                }
            )
        )

    paper.total_score = total_score
    await db.commit()
    refreshed = await db.execute(
        select(Paper).options(selectinload(Paper.sections).selectinload(PaperSection.questions), selectinload(Paper.publications)).where(Paper.id == paper.id)
    )
    updated_paper = refreshed.scalar_one()
    await _log_user_activity(db, current_user.id, "append_generated_questions_to_paper", {"paper_id": paper.id, "resource_id": resource.id})
    return _paper_to_response(updated_paper)


@router.delete("/teacher/papers/{paper_id}", response_model=PaperResponse, summary="教师删除或归档试卷")
async def delete_teacher_paper_api(
    paper_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    result = await db.execute(
        select(Paper).options(selectinload(Paper.sections).selectinload(PaperSection.questions), selectinload(Paper.publications)).where(Paper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    if paper is None:
        raise HTTPException(status_code=404, detail="试卷不存在。")
    if current_user.role == "teacher" and paper.created_by_teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除该试卷。")

    if paper.publications:
        paper.status = "archived"
        await db.commit()
        await db.refresh(paper)
        await _log_user_activity(db, current_user.id, "archive_paper", {"paper_id": paper.id})
        return _paper_to_response(paper)

    for section in paper.sections:
        for question in section.questions:
            await db.delete(question)
        await db.delete(section)
    await db.delete(paper)
    await db.commit()

    archived_stub = Paper(
        id=paper.id,
        title=paper.title,
        source_resource_id=paper.source_resource_id,
        created_by_teacher_id=paper.created_by_teacher_id,
        class_id=paper.class_id,
        status="deleted",
        total_score=paper.total_score,
        metadata_json=paper.metadata_json,
        created_at=paper.created_at,
        updated_at=paper.updated_at,
        sections=[],
        publications=[]
    )
    await _log_user_activity(db, current_user.id, "delete_paper", {"paper_id": paper_id})
    return _paper_to_response(archived_stub)


@router.post("/teacher/papers/{paper_id}/publish", response_model=PaperPublicationResponse, summary="教师发布试卷到班级")
async def publish_teacher_paper_api(
    paper_id: str,
    request: PaperPublicationRequest,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    paper_result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = paper_result.scalar_one_or_none()
    if paper is None:
        raise HTTPException(status_code=404, detail="试卷不存在。")
    if current_user.role == "teacher" and paper.created_by_teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权发布该试卷。")

    class_result = await db.execute(select(Classroom).options(selectinload(Classroom.teacher)).where(Classroom.id == request.class_id))
    classroom = class_result.scalar_one_or_none()
    if classroom is None:
        raise HTTPException(status_code=404, detail="班级不存在。")
    if current_user.role == "teacher" and classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能发布到自己的班级。")

    publication = PaperPublication(
        paper_id=paper.id,
        class_id=classroom.id,
        published_by=current_user.id,
        deadline=request.deadline,
        status="published"
    )
    db.add(publication)
    paper.class_id = classroom.id
    paper.status = "published"
    await db.commit()
    await db.refresh(publication)
    await _log_user_activity(db, current_user.id, "publish_paper", {"paper_id": paper.id, "class_id": classroom.id})
    return PaperPublicationResponse(
        id=publication.id,
        paper_id=publication.paper_id,
        class_id=publication.class_id,
        class_name=classroom.name,
        published_by=publication.published_by,
        published_at=publication.published_at,
        deadline=publication.deadline,
        status=publication.status
    )


@router.get("/teacher/classes/{class_id}/papers", response_model=List[PaperPublicationResponse], summary="教师查看班级已发布试卷")
async def get_teacher_class_papers_api(
    class_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    class_result = await db.execute(select(Classroom).options(selectinload(Classroom.teacher)).where(Classroom.id == class_id))
    classroom = class_result.scalar_one_or_none()
    if classroom is None:
        raise HTTPException(status_code=404, detail="班级不存在。")
    if current_user.role == "teacher" and classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该班级试卷。")

    result = await db.execute(
        select(PaperPublication)
        .options(selectinload(PaperPublication.classroom))
        .where(PaperPublication.class_id == class_id)
        .order_by(PaperPublication.published_at.desc())
    )
    publications = result.scalars().all()
    return [
        PaperPublicationResponse(
            id=publication.id,
            paper_id=publication.paper_id,
            class_id=publication.class_id,
            class_name=publication.classroom.name if publication.classroom else classroom.name,
            published_by=publication.published_by,
            published_at=publication.published_at,
            deadline=publication.deadline,
            status=publication.status
        )
        for publication in publications
    ]


@router.get("/student/classes/{class_id}/papers", response_model=List[StudentPaperListItem], summary="学生查看班级已发布试卷")
async def get_student_class_papers_api(
    class_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可查看班级试卷。")

    membership_result = await db.execute(
        select(ClassMember).where(ClassMember.class_id == class_id, ClassMember.student_id == current_user.id, ClassMember.status == "active")
    )
    if membership_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="你未加入该班级。")

    result = await db.execute(
        select(PaperPublication)
        .options(
            selectinload(PaperPublication.paper),
            selectinload(PaperPublication.classroom),
            selectinload(PaperPublication.publisher)
        )
        .where(PaperPublication.class_id == class_id, PaperPublication.status == "published")
        .order_by(PaperPublication.published_at.desc())
    )
    publications = result.scalars().all()
    return [
        StudentPaperListItem(
            id=publication.paper.id,
            publication_id=publication.id,
            title=publication.paper.title,
            class_name=publication.classroom.name if publication.classroom else "",
            teacher_name=publication.publisher.username if publication.publisher else "",
            published_at=publication.published_at,
            deadline=publication.deadline,
            status=publication.status,
            total_score=publication.paper.total_score
        )
        for publication in publications if publication.paper
    ]


@router.get("/student/papers/{publication_id}", response_model=StudentPaperDetailResponse, summary="学生获取试卷详情")
async def get_student_paper_detail_api(
    publication_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可查看试卷。")

    result = await db.execute(
        select(PaperPublication)
        .options(
            selectinload(PaperPublication.classroom),
            selectinload(PaperPublication.publisher),
            selectinload(PaperPublication.paper).selectinload(Paper.sections).selectinload(PaperSection.questions)
        )
        .where(PaperPublication.id == publication_id)
    )
    publication = result.scalar_one_or_none()
    if publication is None or publication.paper is None:
        raise HTTPException(status_code=404, detail="试卷不存在。")

    membership_result = await db.execute(
        select(ClassMember).where(
            ClassMember.class_id == publication.class_id,
            ClassMember.student_id == current_user.id,
            ClassMember.status == "active"
        )
    )
    if membership_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="你未加入该班级。")

    return StudentPaperDetailResponse(
        publication_id=publication.id,
        paper=_paper_to_student_response(publication.paper),
        class_name=publication.classroom.name if publication.classroom else "",
        teacher_name=publication.publisher.username if publication.publisher else "",
        published_at=publication.published_at,
        deadline=publication.deadline
    )


@router.post("/student/papers/{publication_id}/submit", response_model=PaperSubmissionResponse, summary="学生提交试卷并即时批改")
async def submit_student_paper_api(
    publication_id: str,
    request: PaperSubmissionRequest,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可提交试卷。")

    result = await db.execute(
        select(PaperPublication)
        .options(
            selectinload(PaperPublication.paper).selectinload(Paper.sections).selectinload(PaperSection.questions),
            selectinload(PaperPublication.classroom)
        )
        .where(PaperPublication.id == publication_id)
    )
    publication = result.scalar_one_or_none()
    if publication is None or publication.paper is None:
        raise HTTPException(status_code=404, detail="试卷不存在。")

    membership_result = await db.execute(
        select(ClassMember).where(
            ClassMember.class_id == publication.class_id,
            ClassMember.student_id == current_user.id,
            ClassMember.status == "active"
        )
    )
    if membership_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="你未加入该班级。")

    existing_result = await db.execute(
        select(PaperSubmission).where(PaperSubmission.publication_id == publication.id, PaperSubmission.student_id == current_user.id)
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="该试卷已提交，不可重复提交。")

    answer_map = {item.question_id: item.student_answer for item in request.answers}
    all_questions = [question for section in publication.paper.sections for question in section.questions]
    if not all_questions:
        raise HTTPException(status_code=400, detail="试卷没有题目。")

    submission = PaperSubmission(
        paper_id=publication.paper.id,
        publication_id=publication.id,
        student_id=current_user.id,
        submitted_at=datetime.now(timezone.utc),
        status="submitted"
    )
    db.add(submission)
    await db.flush()

    total_score = 0.0
    max_score = 0.0
    error_items: List[Dict[str, Any]] = []
    answer_responses: List[PaperSubmissionAnswerResponse] = []

    for question in sorted(all_questions, key=lambda item: (item.section.sort_order if item.section else 0, item.sort_order)):
        student_answer = answer_map.get(question.id, "").strip()
        grading = await _grade_paper_answer(question, student_answer)
        max_score += float(question.score)
        total_score += grading["score"]

        if grading["error_tags_json"]:
            error_items.append({
                "question_id": question.id,
                "question_type": question.question_type,
                "summary": grading["error_tags_json"].get("summary"),
                "errors": grading["error_tags_json"].get("errors", [])
            })

        submission_answer = PaperSubmissionAnswer(
            submission_id=submission.id,
            question_id=question.id,
            student_answer=student_answer,
            auto_feedback=grading["auto_feedback"],
            score=grading["score"],
            is_correct=grading["is_correct"],
            error_tags_json=grading["error_tags_json"],
            corrected_at=datetime.now(timezone.utc)
        )
        db.add(submission_answer)
        await db.flush()

        answer_responses.append(
            PaperSubmissionAnswerResponse(
                id=submission_answer.id,
                question_id=question.id,
                question_content=question.question_content,
                question_type=question.question_type,
                reference_answer=question.reference_answer,
                student_answer=student_answer,
                auto_feedback=grading["auto_feedback"],
                score=grading["score"],
                max_score=question.score,
                is_correct=grading["is_correct"],
                error_tags_json=grading["error_tags_json"],
                corrected_at=submission_answer.corrected_at
            )
        )

    submission.total_score = total_score
    submission.correctness_percentage = (total_score / max_score) if max_score > 0 else 0.0
    submission.error_analysis_json = {"items": error_items}

    db.add(
        StudentPerformance(
            student_id=current_user.id,
            resource_id=publication.paper.source_resource_id,
            score=total_score,
            total_score=max_score,
            correctness_percentage=submission.correctness_percentage,
            error_analysis_json=submission.error_analysis_json,
            assessment_type="paper_submission"
        )
    )

    await db.commit()
    await db.refresh(submission)
    await _log_user_activity(db, current_user.id, "submit_paper", {"publication_id": publication.id, "paper_id": publication.paper.id, "total_score": total_score})

    return PaperSubmissionResponse(
        id=submission.id,
        paper_id=submission.paper_id,
        publication_id=submission.publication_id,
        student_id=submission.student_id,
        student_name=current_user.username,
        submitted_at=submission.submitted_at,
        status=submission.status,
        total_score=total_score,
        max_score=max_score,
        correctness_percentage=submission.correctness_percentage,
        error_analysis_json=submission.error_analysis_json,
        answers=answer_responses
    )


@router.get("/student/submissions/{submission_id}", response_model=PaperSubmissionResponse, summary="学生查看自己的试卷批改结果")
async def get_student_submission_api(
    submission_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可查看提交结果。")

    result = await db.execute(
        select(PaperSubmission)
        .options(
            selectinload(PaperSubmission.answers).selectinload(PaperSubmissionAnswer.question),
            selectinload(PaperSubmission.student)
        )
        .where(PaperSubmission.id == submission_id, PaperSubmission.student_id == current_user.id)
    )
    submission = result.scalar_one_or_none()
    if submission is None:
        raise HTTPException(status_code=404, detail="提交记录不存在。")

    max_score = sum((answer.question.score if answer.question else 0) for answer in submission.answers)
    return PaperSubmissionResponse(
        id=submission.id,
        paper_id=submission.paper_id,
        publication_id=submission.publication_id,
        student_id=submission.student_id,
        student_name=submission.student.username if submission.student else current_user.username,
        submitted_at=submission.submitted_at,
        status=submission.status,
        total_score=submission.total_score,
        max_score=max_score,
        correctness_percentage=submission.correctness_percentage,
        error_analysis_json=submission.error_analysis_json,
        answers=[
            PaperSubmissionAnswerResponse(
                id=answer.id,
                question_id=answer.question_id,
                question_content=answer.question.question_content if answer.question else "",
                question_type=answer.question.question_type if answer.question else "",
                reference_answer=answer.question.reference_answer if answer.question else None,
                student_answer=answer.student_answer,
                auto_feedback=answer.auto_feedback,
                score=answer.score,
                max_score=answer.question.score if answer.question else 0,
                is_correct=answer.is_correct,
                error_tags_json=answer.error_tags_json,
                corrected_at=answer.corrected_at
            )
            for answer in submission.answers
        ]
    )


@router.get("/teacher/papers/{paper_id}/submissions", response_model=List[TeacherPaperSubmissionSummary], summary="教师查看试卷提交情况")
async def get_teacher_paper_submissions_api(
    paper_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    paper_result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = paper_result.scalar_one_or_none()
    if paper is None:
        raise HTTPException(status_code=404, detail="试卷不存在。")
    if current_user.role == "teacher" and paper.created_by_teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该试卷提交情况。")

    result = await db.execute(
        select(PaperSubmission)
        .options(selectinload(PaperSubmission.answers).selectinload(PaperSubmissionAnswer.question), selectinload(PaperSubmission.student))
        .where(PaperSubmission.paper_id == paper_id)
        .order_by(PaperSubmission.submitted_at.desc())
    )
    submissions = result.scalars().all()
    return [
        TeacherPaperSubmissionSummary(
            id=submission.id,
            student_id=submission.student_id,
            student_name=submission.student.username if submission.student else f"学生{submission.student_id}",
            submitted_at=submission.submitted_at,
            total_score=submission.total_score,
            max_score=sum((answer.question.score if answer.question else 0) for answer in submission.answers),
            correctness_percentage=submission.correctness_percentage,
            status=submission.status
        )
        for submission in submissions
    ]


@router.get("/teacher/submissions/{submission_id}", response_model=PaperSubmissionResponse, summary="教师查看单份试卷批改详情")
async def get_teacher_submission_detail_api(
    submission_id: str,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无教师或管理员权限。")

    result = await db.execute(
        select(PaperSubmission)
        .options(
            selectinload(PaperSubmission.paper),
            selectinload(PaperSubmission.answers).selectinload(PaperSubmissionAnswer.question),
            selectinload(PaperSubmission.student)
        )
        .where(PaperSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if submission is None or submission.paper is None:
        raise HTTPException(status_code=404, detail="提交记录不存在。")
    if current_user.role == "teacher" and submission.paper.created_by_teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该提交记录。")

    max_score = sum((answer.question.score if answer.question else 0) for answer in submission.answers)
    return PaperSubmissionResponse(
        id=submission.id,
        paper_id=submission.paper_id,
        publication_id=submission.publication_id,
        student_id=submission.student_id,
        student_name=submission.student.username if submission.student else f"学生{submission.student_id}",
        submitted_at=submission.submitted_at,
        status=submission.status,
        total_score=submission.total_score,
        max_score=max_score,
        correctness_percentage=submission.correctness_percentage,
        error_analysis_json=submission.error_analysis_json,
        answers=[
            PaperSubmissionAnswerResponse(
                id=answer.id,
                question_id=answer.question_id,
                question_content=answer.question.question_content if answer.question else "",
                question_type=answer.question.question_type if answer.question else "",
                reference_answer=answer.question.reference_answer if answer.question else None,
                student_answer=answer.student_answer,
                auto_feedback=answer.auto_feedback,
                score=answer.score,
                max_score=answer.question.score if answer.question else 0,
                is_correct=answer.is_correct,
                error_tags_json=answer.error_tags_json,
                corrected_at=answer.corrected_at
            )
            for answer in submission.answers
        ]
    )


#教师API(所有教师侧API都需要教师或管理员权限)-----------------

# 流式生成教学内容并在完成后自动保存
@router.post("/teacher/lesson_plan/generate/stream", summary="流式生成教学内容和备课计划")
async def generate_lesson_plan_stream_api(
    request: LessonPlanRequest,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无教师或管理员权限。")

    current_user_id = current_user.id
    start_time_log = datetime.now(timezone.utc)

    system_instruction = f"你是一位资深的{request.course_level}级别《嵌入式Linux开发实践教程》课程设计师和教育专家。"
    user_question = f"""请根据以下课程大纲，设计一份详细的教学内容。
    内容应包括：
    1. 知识讲解点（条理清晰，有深度，可分多级标题）
    2. 相关的实训练习建议（具体，可操作，包含目标、步骤和预期结果）
    3. 时间分布建议（例如，每部分大致需要多长时间，总时长{'约' + str(request.expected_duration_hours) + '小时' if request.expected_duration_hours else '合理分配'}）

    课程大纲：
    ---
    {request.course_outline}
    ---
    """
    final_instruction = (
        "请给出完整、详细且可直接使用的课程设计，格式清晰，便于教师直接使用。"
        "如果内容较长，也必须完整输出，不要中途省略、不要用“以下略”“后续同理”等简写结束。"
        "请确保最后一节内容、实践安排和时间分配完整收尾。"
    )

    async def generate():
        chunks: List[str] = []
        for chunk in stream_text_with_qwen3(
            system_instruction=system_instruction,
            user_question=user_question,
            retrieved_documents_content=[],
            final_instruction=final_instruction,
            max_new_tokens=None,
            temperature=0.7,
            top_p=0.9
        ):
            chunks.append(chunk)
            yield chunk

        lesson_plan_content = "".join(chunks).strip()
        if not lesson_plan_content:
            return

        resource_id = str(uuid.uuid4())
        file_dir = "generated_resources/lesson_plans"
        os.makedirs(file_dir, exist_ok=True)
        file_path = os.path.join(file_dir, f"{resource_id}.md")
        _write_resource_file(file_path, lesson_plan_content)

        new_resource = Resource(
            id=resource_id,
            title=request.course_outline[:200],
            resource_type="lesson_plan",
            created_by_user_id=current_user_id,
            subject=request.subject,
            file_path=file_path,
            metadata_json={
                "course_level": request.course_level,
                "expected_duration_hours": request.expected_duration_hours,
                "generated_by": "stream"
            }
        )
        db.add(new_resource)
        await db.flush()

        lesson_plan_log_entry = LessonPlanTimeLog(
            user_id=current_user_id,
            resource_id=new_resource.id,
            start_time=start_time_log,
            end_time=datetime.now(timezone.utc)
        )
        db.add(lesson_plan_log_entry)
        await db.commit()
        await _log_user_activity(
            db,
            current_user_id,
            "generate_lesson_plan_stream",
            {"resource_id": str(new_resource.id), "subject": request.subject}
        )

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")

#根据课程大纲、知识库、课程级别和期望时长，自动生成详细的教学内容（知识讲解、实训练习、时间分布）
@router.post("/teacher/lesson_plan/generate", response_model=LessonPlanResponse, summary="生成教学内容和备课计划")
async def generate_lesson_plan_api(request: LessonPlanRequest,current_user: User = Depends(get_current_user_simple),db: AsyncSession = Depends(get_db)):
    if current_user.role not in ["teacher", "admin"]:  # 权限判断
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无教师或管理员权限。")

    current_user_id = current_user.id

    start_time_log = datetime.now(timezone.utc)
    # --- 记录开始时间 ---
    lesson_plan_log_entry = LessonPlanTimeLog(
        user_id=current_user_id,
        resource_id=None,
        start_time=start_time_log
    )
    db.add(lesson_plan_log_entry)
    await db.flush()  # 立即分配ID,不提交

#生成LLM内容
    retrieved_docs_content = []

    system_instruction = f"你是一位资深的{request.course_level}级别《嵌入式Linux开发实践教程》课程设计师和教育专家。"
    user_question = f"""请根据以下课程大纲，设计一份详细的教学内容。
    内容应包括：
    1. 知识讲解点（条理清晰，有深度，可分多级标题）
    2. 相关的实训练习建议（具体，可操作，包含目标、步骤和预期结果）
    3. 时间分布建议（例如，每部分大致需要多长时间，总时长{'约' + str(request.expected_duration_hours) + '小时' if request.expected_duration_hours else '合理分配'}）

    课程大纲：
    ---
    {request.course_outline}
    ---
    """
    final_instruction = (
        "请给出完整、详细且可直接使用的课程设计，格式清晰，便于教师直接使用。"
        "如果内容较长，也必须完整输出，不要中途省略、不要用“以下略”“后续同理”等简写结束。"
        "请确保最后一节内容、实践安排和时间分配完整收尾。"
    )

    lesson_plan_content = await _get_llm_response(
        system_instruction=system_instruction,
        user_question=user_question,
        retrieved_documents_content=retrieved_docs_content,
        final_instruction=final_instruction,
        max_new_tokens=None,
        temperature=0.7,
        top_p=0.9
    )

    # --- 存储生成的备课内容到文件 ---
    resource_id = str(uuid.uuid4())
    file_dir = "generated_resources/lesson_plans"
    # 确保目录存在，如果不存在则创建
    os.makedirs(file_dir, exist_ok=True)
    file_path = os.path.join(file_dir, f"{resource_id}.md")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(lesson_plan_content)
        print(f"备课计划内容已成功写入到: {file_path}")
    except IOError as e:
        print(f"写入备课计划内容到文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件写入失败: {e}")

    new_resource = Resource(
        id=resource_id,
        title=request.course_outline[:200],
        resource_type="lesson_plan",
        created_by_user_id=current_user_id,
        subject=request.subject,
        file_path=file_path,
        metadata_json={
            "course_level": request.course_level,
            "expected_duration_hours": request.expected_duration_hours
        }
    )
    db.add(new_resource)

    await db.commit()
    await db.refresh(new_resource)

    # 记录备课时间日志
    lesson_plan_log_entry = LessonPlanTimeLog(
        user_id=current_user_id,
        resource_id=new_resource.id,  # 正确关联已生成的资源ID
        start_time=start_time_log,  # 使用之前记录的开始时间
        end_time=datetime.now(timezone.utc)  # 记录结束时间
    )

    db.add(lesson_plan_log_entry)
    await db.flush()

    await db.commit()
    await db.refresh(lesson_plan_log_entry)

    #记录用户活动日志
    await _log_user_activity(db, current_user_id, "generate_lesson_plan",
                             {"resource_id": str(new_resource.id), "subject": request.subject})


    return LessonPlanResponse(status="success", lesson_plan=lesson_plan_content, generated_at=datetime.now(),
                              resource_id=new_resource.id)


# 自动生成多样化考核题目及参考答案，尤其包括计算机类编程题和答案。
@router.post("/teacher/assessment/generate", response_model=AssessmentQuestionResponse,summary="生成考核题目及参考答案")
async def generate_assessment_api(request: AssessmentQuestionRequest,current_user: User = Depends(get_current_user_simple),db: AsyncSession = Depends(get_db)):
    if current_user.role not in ["teacher", "admin"]:  # 权限判断
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无教师或管理员权限。")

    current_user_id = current_user.id

    retrieved_docs_content = await _get_retrieved_docs(request.topic, k=5)

    # 根据编程语言提供提示，如果指定了的话
    programming_lang_hint = f"使用 {request.programming_language} 语言" if request.programming_language else ""

    generated_questions = await _generate_structured_questions(
        topic_or_title=request.topic,
        source_content=f"{request.topic}\n{programming_lang_hint}",
        question_type=request.question_type,
        difficulty_level=request.difficulty_level,
        num_questions=request.num_questions,
        retrieved_documents_content=retrieved_docs_content
    )
    assessment_content = _render_questions_markdown(f"{request.topic} - {request.question_type}考核题", generated_questions)

    # --- 新增：存储生成的考核内容到文件系统 ---
    resource_id = str(uuid.uuid4())
    file_dir = "generated_resources/assessments"
    # 确保目录存在，如果不存在则创建
    os.makedirs(file_dir, exist_ok=True)
    full_file_path = os.path.join(file_dir, f"{resource_id}.md")

    try:
        with open(full_file_path, "w", encoding="utf-8") as f:
            f.write(assessment_content)
        print(f"考核题目内容已成功写入到: {full_file_path}")
    except IOError as e:
        print(f"写入考核题目内容到文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件写入失败: {e}")


    # --- 存储生成的考核内容到数据库 ---
    new_resource = Resource(
        id=resource_id,
        title=f"{request.topic}-{request.question_type}-{request.difficulty_level}",
        resource_type="assessment",
        created_by_user_id=current_user_id,
        file_path=full_file_path, # <-- 确保这里存储的是完整的文件路径
        metadata_json={
            "question_type": request.question_type,
            "difficulty_level": request.difficulty_level,
            "num_questions": request.num_questions,
            "programming_language": request.programming_language
        },
        # subject = request.subject # 如果 request.subject 不存在，请将其改为 request.topic
        subject = request.subject if request.subject else request.topic # <-- 推荐的修改：优先使用 request.subject，否则使用 request.topic
    )
    db.add(new_resource)
    await db.flush()
    await _replace_generated_questions(db, new_resource.id, generated_questions)
    await db.commit()
    await db.refresh(new_resource)

    # --- 记录用户活动日志 ---
    await _log_user_activity(db, current_user_id, "generate_assessment",
                             {"resource_id": str(new_resource.id),
                              # "subject": request.subject, # 如果 request.subject 不存在，请将其改为 request.topic
                              "subject": request.subject if request.subject else request.topic, # <-- 推荐的修改
                              "question_type": request.question_type,
                              "difficulty_level": request.difficulty_level})

    refreshed = await db.execute(
        select(Resource).options(selectinload(Resource.generated_questions)).where(Resource.id == new_resource.id)
    )
    refreshed_resource = refreshed.scalar_one()
    return AssessmentQuestionResponse(
        status="success",
        assessment_content=assessment_content,
        generated_at=datetime.now(),
        resource_id=new_resource.id,
        questions=[_generated_question_to_response(question) for question in sorted(refreshed_resource.generated_questions, key=lambda item: item.sort_order)]
    )

#自动化检测学生答案，提供错误定位与修正建议；分析学生整体数据，总结知识掌握情况
@router.post("/teacher/student_answer/correct", response_model=CorrectionFeedbackResponse, summary="自动化检测学生答案，提供错误定位与修正建议")
async def correct_student_answer_api(request: StudentAnswerCorrectionRequest,current_user: User = Depends(get_current_user_simple),db: AsyncSession = Depends(get_db)):
    if current_user.role not in ["teacher", "admin"]: # 权限判断
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无教师或管理员权限。")

    current_user_id = current_user.id
    # --- 记录开始时间 ---
    correction_log_entry = CorrectionTimeLog(
        user_id=current_user_id,
        start_time=datetime.now(timezone.utc)
    )
    db.add(correction_log_entry)
    await db.flush()  # 立即分配ID

    # 获取知识库内容
    query_for_retrieval = request.question
    if request.reference_answer:
        query_for_retrieval += " " + request.reference_answer
    retrieved_docs_content = await _get_retrieved_docs(query_for_retrieval, k=3)

    # 构建LLM请求
    system_instruction = "你是一位严格且专业的批改老师和学习指导专家，擅长找出学生答案中的问题并给出清晰的修正建议。"
    user_question = f"""请批改学生的回答，并给出详细的错误定位和修正建议。
    原始问题：{request.question}
    学生回答：{request.student_answer}
    {f"参考答案：{request.reference_answer}" if request.reference_answer else ""}

    批改内容应包括（请严格按照以下格式输出）：
    ---
    评分: [例如：8/10]
    优点: [简要说明学生回答的亮点]
    错误定位: [指出具体错误点，如概念混淆、逻辑不清晰、代码错误等，并详细解释]
    修正建议: [给出具体的修改方案，代码错误需提供修正后的代码示例]
    知识点掌握情况总结: [评估学生对该知识点的掌握程度，如：基本掌握，概念模糊，需要加强实践等]
    ---
    """
    final_instruction = "请按照上述结构清晰地给出批改结果。"

    # 获取LLM反馈
    correction_feedback = await _get_llm_response(
        system_instruction=system_instruction,
        user_question=user_question,
        retrieved_documents_content=retrieved_docs_content,
        final_instruction=final_instruction,
        max_new_tokens=None,
        temperature=0.7,
        top_p=0.9
    )

    # --- 记录结束时间 ---
    correction_log_entry.end_time = datetime.now(timezone.utc)
    await db.commit()  # 提交时间日志
    await db.refresh(correction_log_entry)

    # --- 解析反馈并存储 StudentPerformance ---
    parsed_score = None
    parsed_errors = []
    # 简单的文本解析，实际应用中可能需要更健壮的解析或LLM返回结构化JSON
    for line in correction_feedback.split('\n'):
        if line.startswith("评分:"):
            try:
                score_parts = line.split(":")[-1].strip().split('/')
                if len(score_parts) == 2:
                    score = float(score_parts[0])
                    total = float(score_parts[1])
                    if total > 0:
                        parsed_score = score / total
            except ValueError:
                pass
        elif line.startswith("错误定位:"):
            # 简单提取错误点，可以根据需要优化LLM提示词让其输出更结构化
            error_detail = line.replace("错误定位:", "").strip()
            if error_detail:
                # 假设 LLM 可能会提及知识点，这里做简单提取
                # 实际应用中，LLM应该返回 {"topic": "概念混淆", "count": 1} 这样的结构化数据
                parsed_errors.append({"topic": error_detail, "count": 1})
        elif line.startswith("知识点掌握情况总结:"):
            mastery_summary = line.replace("知识点掌握情况总结:", "").strip()
            if mastery_summary:
                # 可以根据掌握情况总结生成更具体的错误主题
                if "概念模糊" in mastery_summary or "需要加强实践" in mastery_summary:
                    # 尝试从原始问题或学生答案中提取主题，这里简化为通用主题
                    if not parsed_errors:  # 如果前面没提取到具体错误点，添加一个通用总结
                        parsed_errors.append({"topic": mastery_summary, "count": 1})

    new_performance = StudentPerformance(
        student_id=request.student_id,
        assessment_type="teacher_correction",
        correctness_percentage=parsed_score,
        error_analysis_json=parsed_errors if parsed_errors else None,
        course_id=request.course_id,  # 假设请求中包含课程ID
        resource_id=request.resource_id if hasattr(request, 'resource_id') else None
    )
    db.add(new_performance)
    await db.commit()
    await db.refresh(new_performance)
    # --- 存储 StudentPerformance 结束 ---

    # --- 记录用户活动日志 ---
    await _log_user_activity(db, current_user_id, "correct_answer",
                             {"type": "teacher", "score": parsed_score, "student_id": str(request.student_id)})
    # --- 记录用户活动日志结束 ---

    return CorrectionFeedbackResponse(status="success", feedback=correction_feedback, corrected_at=datetime.now())

#学生API(所有学生侧 API 都需要认证)----------------------------

#结合教学内容解答学生提出的问题
@router.post("/student/ask", response_model=StudentQuestionResponse, summary="在线学习助手：解答学生提出的问题")
async def ask_student_assistant_api(request: StudentQuestionRequest,current_user: User = Depends(get_current_user_simple), db: AsyncSession = Depends(get_db)):
    # 任何已认证用户都可以提问
    student_id = current_user.id
    print(f"用户 {student_id} 提出了问题: {request.question}")
    started_at = time.perf_counter()

    retrieved_docs_content = await _get_retrieved_docs(request.question, k=5)

    system_instruction = "你是一名专业的《嵌入式Linux开发实践教程》学习助手。请根据以下提供的知识库内容，简洁、准确、清晰地回答用户的问题。如果知识库中没有直接答案，请说明你无法根据当前知识库回答，并鼓励学生继续探索。"
    final_instruction = "请给出你的回答："

    answer = await _get_llm_response(
        system_instruction=system_instruction,
        user_question=request.question,
        retrieved_documents_content=retrieved_docs_content,
        final_instruction=final_instruction,
        max_new_tokens=None,
        temperature=0.7,
        top_p=0.9
    )
    elapsed = time.perf_counter() - started_at
    print(
        f"学生问答完成: total_elapsed={elapsed:.2f}s, user_id={student_id}, "
        f"docs={len(retrieved_docs_content)}, answer_preview={answer[:120]!r}"
    )
    await _log_user_activity(db, student_id, "ask_question", {"question": request.question[:100]})

    return StudentQuestionResponse(status="success", question=request.question, answer=answer)


@router.post("/student/ask/stream", summary="在线学习助手：流式解答学生提出的问题")
async def ask_student_assistant_stream_api(
    request: StudentQuestionRequest,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    student_id = current_user.id
    print(f"用户 {student_id} 发起流式问答: {request.question}")
    started_at = time.perf_counter()

    retrieved_docs_content = await _get_retrieved_docs(request.question, k=5)
    system_instruction = "你是一名专业的《嵌入式Linux开发实践教程》学习助手。请根据以下提供的知识库内容，简洁、准确、清晰地回答用户的问题。如果知识库中没有直接答案，请说明你无法根据当前知识库回答，并鼓励学生继续探索。"
    final_instruction = "请给出你的回答："

    def generate():
        answer_chunks: List[str] = []
        try:
            for chunk in stream_text_with_qwen3(
                system_instruction=system_instruction,
                user_question=request.question,
                retrieved_documents_content=retrieved_docs_content,
                final_instruction=final_instruction,
                max_new_tokens=None,
                temperature=0.7,
                top_p=0.9
            ):
                answer_chunks.append(chunk)
                yield chunk
        finally:
            full_answer = "".join(answer_chunks)
            elapsed = time.perf_counter() - started_at
            print(
                f"学生流式问答完成: total_elapsed={elapsed:.2f}s, user_id={student_id}, "
                f"docs={len(retrieved_docs_content)}, answer_preview={full_answer[:120]!r}"
            )

    await _log_user_activity(db, student_id, "ask_question_stream", {"question": request.question[:100]})
    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")

# 根据学生历史练习和要求生成随练题目（基于主题和数量生成，未集成复杂的学生历史练习数据分析）
@router.post("/student/practice/generate", response_model=PracticeQuestionResponse, summary="实时练习评测助手：生成随练题目")
async def generate_practice_question_api(request: PracticeQuestionRequest,current_user: User = Depends(get_current_user_simple),db: AsyncSession = Depends(get_db)):
    if current_user.role != "student":  # 权限判断
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无学生权限。")

    # 注意：这里的 current_user.id 假设是 UUID 类型
    # request.student_id 假设是字符串类型
    if str(request.student_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权为其他学生生成练习。")

    current_user_id = current_user.id

    retrieved_docs_content = []
    if request.topic_focus:
        retrieved_docs_content = await _get_retrieved_docs(request.topic_focus, k=3)

    generated_questions = await _generate_structured_questions(
        topic_or_title=request.topic_focus or "综合练习",
        source_content=request.topic_focus or "请围绕当前课程知识点生成练习题。",
        question_type=request.question_type or "混合",
        difficulty_level="中等",
        num_questions=request.num_questions,
        retrieved_documents_content=retrieved_docs_content
    )
    practice_content = _render_questions_markdown(f"{request.topic_focus or '综合'}练习题", generated_questions)

    # --- 存储生成的练习内容到文件系统 ---
    resource_id = str(uuid.uuid4())
    file_dir = "generated_resources/practices"
    # 确保目录存在，如果不存在则创建
    os.makedirs(file_dir, exist_ok=True)
    full_file_path = os.path.join(file_dir, f"{resource_id}.md")

    try:
        with open(full_file_path, "w", encoding="utf-8") as f:
            f.write(practice_content)
        print(f"练习题目内容已成功写入到: {full_file_path}")
    except IOError as e:
        print(f"写入练习题目内容到文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件写入失败: {e}")

    # --- 存储生成的练习内容到数据库 ---
    new_resource = Resource(
        id=resource_id,
        title=f"随练题目 - {request.topic_focus or '通用'} - 学生{current_user_id}",
        resource_type="practice",
        created_by_user_id=current_user_id,
        file_path=full_file_path, # <-- 确保这里存储的是完整的文件路径
        metadata_json={
            "student_id": str(current_user_id),
            "topic_focus": request.topic_focus,
            "num_questions": request.num_questions,
            "question_type": request.question_type # <-- 新增：保存题型
        },
        subject=request.topic_focus
    )
    db.add(new_resource)
    await db.flush()
    await _replace_generated_questions(db, new_resource.id, generated_questions)
    await db.commit()
    await db.refresh(new_resource)

    # --- 记录用户活动日志 ---
    await _log_user_activity(db, current_user_id, "generate_practice",
                             {"resource_id": str(new_resource.id),
                              "topic_focus": request.topic_focus,
                              "num_questions": request.num_questions,
                              "question_type": request.question_type}) # 记录题型

    refreshed = await db.execute(
        select(Resource).options(selectinload(Resource.generated_questions)).where(Resource.id == new_resource.id)
    )
    refreshed_resource = refreshed.scalar_one()
    return PracticeQuestionResponse(
        status="success",
        practice_questions=practice_content,
        generated_at=datetime.now(),
        resource_id=new_resource.id,
        questions=[_generated_question_to_response(question) for question in sorted(refreshed_resource.generated_questions, key=lambda item: item.sort_order)]
    )


@router.post("/student/practices/{resource_id}/submit", response_model=PracticeSubmissionResponse, summary="学生提交结构化练习并即时批改")
async def submit_generated_practice_api(
    resource_id: str,
    request: PracticeSubmissionRequest,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可提交自己的练习。")

    result = await db.execute(
        select(Resource)
        .options(selectinload(Resource.generated_questions))
        .where(Resource.id == resource_id, Resource.resource_type == "practice", Resource.created_by_user_id == current_user.id)
    )
    resource = result.scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=404, detail="练习资源不存在。")

    questions = sorted(resource.generated_questions or [], key=lambda item: item.sort_order)
    if not questions:
        raise HTTPException(status_code=400, detail="该练习没有结构化题目。")

    answer_map = {item.question_id: item.student_answer for item in request.answers}
    total_score = 0.0
    max_score = 0.0
    responses: List[PracticeSubmissionAnswerResponse] = []

    for question in questions:
        student_answer = (answer_map.get(question.id) or "").strip()
        grading = await _grade_answer_with_model(
            question_type=question.question_type,
            question_content=question.question_content,
            reference_answer=question.reference_answer,
            score=float(question.score),
            student_answer=student_answer,
            options=_normalize_options(question.options_json)
        )
        total_score += grading["score"]
        max_score += float(question.score)
        responses.append(
            PracticeSubmissionAnswerResponse(
                question_id=question.id,
                question_content=question.question_content,
                question_type=question.question_type,
                reference_answer=question.reference_answer,
                student_answer=student_answer,
                auto_feedback=grading["auto_feedback"],
                score=grading["score"],
                max_score=float(question.score),
                is_correct=grading["is_correct"],
                error_tags_json=grading["error_tags_json"]
            )
        )

    correctness_percentage = (total_score / max_score) if max_score > 0 else 0.0
    db.add(
        StudentPerformance(
            student_id=current_user.id,
            resource_id=resource.id,
            score=total_score,
            total_score=max_score,
            correctness_percentage=correctness_percentage,
            error_analysis_json={"items": [item.error_tags_json for item in responses if item.error_tags_json]},
            assessment_type="practice_submission"
        )
    )
    await db.commit()
    await _log_user_activity(db, current_user.id, "submit_practice", {"resource_id": resource_id, "total_score": total_score})
    return PracticeSubmissionResponse(
        resource_id=resource.id,
        total_score=total_score,
        max_score=max_score,
        correctness_percentage=correctness_percentage,
        answers=responses
    )

#学生题目修改
@router.post("/student/practice/correct", response_model=CorrectionFeedbackResponse, summary="实时练习评测助手：纠错学生练习答案")
async def correct_practice_answer_api(
    request: StudentAnswerCorrectionRequest,
    current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)
):
    print(f"用户 {current_user.id} 提交了练习答案进行批改。")

    if str(request.student_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权为其他学生批改练习。")

    current_user_id = current_user.id

    # --- Database Transaction Start ---
    try:
        correction_log_entry = CorrectionTimeLog(
            user_id=current_user_id,
            start_time=datetime.now(timezone.utc)
        )
        db.add(correction_log_entry)

        query_for_retrieval = request.question
        retrieved_docs_content = await _get_retrieved_docs(query_for_retrieval, k=3)

        reference_answer_system_instruction = "你是一位知识渊博的专家，请根据给定的问题，提供一个清晰、准确、完整的参考答案。确保答案专业且易于理解。"
        reference_answer_user_question = f"请为以下问题生成一个详细的参考答案：\n问题：{request.question}"
        reference_answer_final_instruction = "请直接给出参考答案，不要包含任何额外信息或前缀。"

        generated_reference_answer = await _get_llm_response(
            system_instruction=reference_answer_system_instruction,
            user_question=reference_answer_user_question,
            retrieved_documents_content=retrieved_docs_content,
            final_instruction=reference_answer_final_instruction,
            max_new_tokens=None,
            temperature=0.5,
            top_p=0.8
        )
        print(f"后端生成的参考答案：\n{generated_reference_answer}")

        # --- Build LLM Correction Request (MODIFIED FOR SCORING) ---
        system_instruction = "你是一名专业的学习指导助手，擅长对学生练习进行快速批改和提供易于理解的修正建议。"
        user_question = f"""请对学生的练习回答进行批改，并给出详细的错误定位、修正建议和**百分制评分**。
        练习题目：{request.question}
        学生回答：{request.student_answer}
        参考答案：{generated_reference_answer}

        批改内容应包括（请严格按照以下格式输出）：
        ---
        评分: [例如：85/100, 70/100, 40/100，只输出数字和斜杠符号，不带解释]
        评估: [例如：优秀、良好、需改进，简要概括总体表现]
        错误点: [指出具体错误，若有，并简要解释]
        修正方法: [给出具体的纠正步骤或知识点回顾建议]
        ---
        """
        final_instruction = "请按照上述结构简洁明了地给出批改结果。"

        correction_feedback = await _get_llm_response(
            system_instruction=system_instruction,
            user_question=user_question,
            retrieved_documents_content=retrieved_docs_content,
            final_instruction=final_instruction,
            max_new_tokens=None,
            temperature=0.7,
            top_p=0.9
        )

        # --- Parse Feedback (MODIFIED FOR SCORING) ---
        parsed_score_str = ""
        parsed_assessment = ""
        parsed_errors = ""
        parsed_correction_method = ""
        correctness_percentage = None
        error_topics = []

        parts = correction_feedback.split("---")
        if len(parts) >= 3:
            content_lines = parts[1].strip().split('\n')
            for line in content_lines:
                if line.startswith("评分:"):
                    parsed_score_str = line.replace("评分:", "").strip().split('/')[0] # Extract only the number
                    try:
                        score = int(parsed_score_str)
                        correctness_percentage = score / 100.0 # Convert to a percentage (0.0 to 1.0)
                    except ValueError:
                        correctness_percentage = None # Handle cases where parsing fails
                elif line.startswith("评估:"):
                    parsed_assessment = line.replace("评估:", "").strip()
                elif line.startswith("错误点:"):
                    parsed_errors = line.replace("错误点:", "").strip()
                elif line.startswith("修正方法:"):
                    parsed_correction_method = line.replace("修正方法:", "").strip()

        # If score couldn't be parsed, fallback to qualitative assessment for correctness_percentage
        if correctness_percentage is None:
            if "正确" in parsed_assessment or "优秀" in parsed_assessment:
                correctness_percentage = 1.0
            elif "部分正确" in parsed_assessment or "良好" in parsed_assessment:
                correctness_percentage = 0.5
            elif "需改进" in parsed_assessment or "不正确" in parsed_assessment:
                correctness_percentage = 0.0
            else:
                correctness_percentage = 0.0 # Default if no clear assessment

        if parsed_errors:
            error_topics.append({"topic": parsed_errors, "count": 1})

        correction_log_entry.end_time = datetime.now(timezone.utc)

        new_performance = StudentPerformance(
            student_id=current_user_id,
            assessment_type="practice_correction",
            correctness_percentage=correctness_percentage,
            error_analysis_json=error_topics if error_topics else None,
            course_id=request.course_id,
            resource_id=request.resource_id
        )
        db.add(new_performance)

        await _log_user_activity(db, current_user_id, "correct_answer",
                                 {"type": "student_practice",
                                  "correctness": correctness_percentage,
                                  "resource_id": str(request.resource_id) if request.resource_id else None,
                                  "question": request.question[:50],
                                  "score": parsed_score_str # Also log the raw score string
                                  })

        await db.commit()
        await db.refresh(correction_log_entry)
        await db.refresh(new_performance)

    except Exception as e:
        await db.rollback()
        print(f"数据库提交失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"数据保存失败: {e}")

    return CorrectionFeedbackResponse(status="success", feedback=correction_feedback, corrected_at=datetime.now(timezone.utc))



# --- 管理侧 API(所有管理侧 API 都需要管理员权限) ---

#创建新的用户账户，并分配角色（管理员、教师、学生）
@router.post("/admin/users/create", response_model=UserCreateResponse, summary="创建用户账户（管理员/教师/学生）")
async def create_user_api(request: UserCreateRequest,current_user: User = Depends(get_current_user_simple),db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin": # 权限判断
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无管理员权限。")

    # 检查用户名是否已存在
    result = await db.execute(select(User).filter(User.username == request.username))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在。")

    # 哈希密码
    hashed_password = hash_password_simple(request.password) # 使用简易哈希函数

    new_user = User(
        username=request.username,
        hashed_password=hashed_password,
        role=request.role
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserCreateResponse(status="success", message=f"用户 '{new_user.username}' ({new_user.role}) 账户创建成功。", user_id=new_user.id)


#获取所有用户账户的列表
@router.get("/admin/users", response_model=List[UserResponse], summary="获取所有用户列表")
async def get_all_users_api(current_user: User = Depends(get_current_user_simple),db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin": # 权限判断
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无管理员权限。")

    result = await db.execute(select(User))
    users = result.scalars().all()
    return [UserResponse.model_validate(user) for user in users]

#获取所有教师生成的课件和练习资源的元数据列表
@router.get("/admin/resources", response_model=List[ResourceMetadata], summary="获取所有课件资源列表")
async def get_all_resources_api(current_user: User = Depends(get_current_user_simple),db: AsyncSession = Depends(get_db),subject: Optional[str] = Query(None, description="按学科筛选资源。") # 新增查询参数
):
    if current_user.role not in ["admin", "teacher", "student"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限查看资源列表。")

    query = select(Resource)
    if subject:
        query = query.where(Resource.subject == subject) # 根据学科过滤

    if current_user.role == "student":
        query = query.where(Resource.created_by_user_id == current_user.id)

    result = await db.execute(query)
    resources = result.scalars().all()

    # 确保 ResourceMetadata 能够正确映射 Resource 对象的 subject 字段
    return [ResourceMetadata.model_validate(resource) for resource in resources]

#获取特定的资源
@router.get("/resources/content",response_model=List[ResourceContentResponse],summary="获取指定资源ID的详细内容，用于前端生成PDF或显示")
async def get_resources_content_for_export(
    resource_ids: List[str] = Query(..., description="要获取内容的资源UUID列表。"),current_user: User = Depends(get_current_user_simple),
    db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(Resource).filter(Resource.id.in_(resource_ids)))
    resources = result.scalars().all()

    if not resources:
        raise HTTPException(status_code=404, detail="未找到任何指定的资源。")

    response_list = []
    for resource in resources:
        resource_content = None
        if resource.file_path and os.path.exists(resource.file_path):
            try:
                with open(resource.file_path, "r", encoding="utf-8") as f:
                    resource_content = f.read()
            except Exception as e:
                print(f"读取文件失败: {resource.file_path}, 错误: {e}")
                # 可以选择在这里抛出异常或返回空内容，根据需求决定
        else:
            print(f"资源文件不存在或路径无效: {resource.file_path}")

        response_list.append(ResourceContentResponse(
            id=resource.id,
            title=resource.title,
            resource_type=resource.resource_type,
            created_by_user_id=resource.created_by_user_id,
            created_at=resource.created_at,
            file_path=resource.file_path,
            metadata_json=resource.metadata_json,
            content=resource_content,  # <-- 传递文件内容
            subject=resource.subject  # 确保包含 subject 字段
        ))
    return response_list

#统计并展示教师/学生使用次数、活跃板块、教学效率和学生学习效果数据
@router.get("/admin/dashboard/metrics", response_model=DashboardMetrics, summary="获取系统大屏概览数据")
async def get_dashboard_metrics_api(current_user: User = Depends(get_current_user_simple),db: AsyncSession = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可查看系统概览数据。")

    # --- 获取当前时间，用于计算当日/本周活跃度 ---
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())  # weekday() returns 0 for Monday

    # --- 1. 用户总数 (教师/学生) ---
    total_teachers_query = await db.execute(
        select(func.count(User.id)).where(User.role == "teacher")
    )
    total_teachers = total_teachers_query.scalar_one_or_none() or 0

    total_students_query = await db.execute(
        select(func.count(User.id)).where(User.role == "student")
    )
    total_students = total_students_query.scalar_one_or_none() or 0

    # --- 2. 课程总数 ---
    total_courses_query = await db.execute(
        select(func.count(Course.id))
    )
    total_courses = total_courses_query.scalar_one_or_none() or 0

    # --- 3. LLM 使用次数统计/活跃板块 (当日/本周) ---
    llm_usage_count = {
        "备课内容生成": 0,
        "考核题目生成": 0,
        "学生问答": 0,
        "练习题目生成": 0,
        "学生答案批改": 0,
    }

    # 映射 UserActivityLog 中的 activity_type 到 DashboardMetrics 的统计项
    activity_type_mapping = {
        "generate_lesson_plan": "备课内容生成",
        "generate_assessment": "考核题目生成",
        "ask_question": "学生问答",
        "generate_practice": "练习题目生成",
        "correct_answer": "学生答案批改",
    }

    # 统计当日活跃教师数
    active_teachers_today_query = await db.execute(
        select(func.count(func.distinct(UserActivityLog.user_id)))
        .join(User, User.id == UserActivityLog.user_id)  # 确保加入User表进行角色过滤
        .where(and_(
            UserActivityLog.timestamp >= today_start,
            User.role == "teacher"
        ))
    )
    active_teachers_today = active_teachers_today_query.scalar_one_or_none() or 0

    # 统计当日活跃学生数
    active_students_today_query = await db.execute(
        select(func.count(func.distinct(UserActivityLog.user_id)))
        .join(User, User.id == UserActivityLog.user_id)
        .where(and_(
            UserActivityLog.timestamp >= today_start,
            User.role == "student"
        ))
    )
    active_students_today = active_students_today_query.scalar_one_or_none() or 0

    # 统计本周活跃教师数
    active_teachers_week_query = await db.execute(
        select(func.count(func.distinct(UserActivityLog.user_id)))
        .join(User, User.id == UserActivityLog.user_id)
        .where(and_(
            UserActivityLog.timestamp >= week_start,
            User.role == "teacher"
        ))
    )
    active_teachers_week = active_teachers_week_query.scalar_one_or_none() or 0

    # 统计本周活跃学生数
    active_students_week_query = await db.execute(
        select(func.count(func.distinct(UserActivityLog.user_id)))
        .join(User, User.id == UserActivityLog.user_id)
        .where(and_(
            UserActivityLog.timestamp >= week_start,
            User.role == "student"
        ))
    )
    active_students_week = active_students_week_query.scalar_one_or_none() or 0

    # --- 4. 教学效率指数 ---
    # 平均备课耗时
    avg_prep_time_query = await db.execute(
        select(func.avg(
            text("TIMESTAMPDIFF(SECOND, lesson_plan_time_logs.start_time, lesson_plan_time_logs.end_time) / 3600")))
        .select_from(LessonPlanTimeLog.__table__)
        .where(LessonPlanTimeLog.end_time.isnot(None))
    )
    avg_prep_time_hours = avg_prep_time_query.scalar_one_or_none() or 0.0

    # 平均批改耗时
    avg_correction_time_query = await db.execute(
        select(func.avg(
            text("TIMESTAMPDIFF(SECOND, correction_time_logs.start_time, correction_time_logs.end_time) / 60")))
        .select_from(CorrectionTimeLog.__table__)  # <-- 【非常重要，请添加这一行！】
        .where(CorrectionTimeLog.end_time.isnot(None))
    )
    avg_correction_time_minutes = avg_correction_time_query.scalar_one_or_none() or 0.0

    # 课程优化方向建议 - 查询平均正确率最低的课程
    course_optimization_suggestions = []
    low_pass_courses_query = await db.execute(
        select(
            Course.title,
            func.avg(StudentPerformance.correctness_percentage).label("avg_correctness")
        )
        .join(StudentPerformance, Course.id == StudentPerformance.course_id)
        .group_by(Course.id, Course.title)
        .order_by(func.avg(StudentPerformance.correctness_percentage))
        .limit(3)  # 取正确率最低的3门课程
    )
    low_pass_courses_results = low_pass_courses_query.all()

    if low_pass_courses_results:
        for course_title, avg_correctness in low_pass_courses_results:
            course_optimization_suggestions.append(
                f"课程 '{course_title}' 平均正确率偏低 ({avg_correctness:.2%})，建议优化教学内容或方法。"
            )
    else:
        course_optimization_suggestions.append("暂无明确课程优化方向数据。")  # 如果没有数据，提供默认提示

    # --- 5. 学生学习效果 ---
    # 学生平均正确率
    avg_student_accuracy_query = await db.execute(
        select(func.avg(StudentPerformance.correctness_percentage))
        .where(StudentPerformance.correctness_percentage.isnot(None))
    )
    avg_student_accuracy = avg_student_accuracy_query.scalar_one_or_none() or 0.0

    # 高频错误知识点 - 汇总 error_analysis_json
    all_error_jsons_query = await db.execute(
        select(StudentPerformance.error_analysis_json)
        .where(StudentPerformance.error_analysis_json.isnot(None))
    )
    all_error_jsons = all_error_jsons_query.scalars().all()

    error_counts = {}
    for error_json in all_error_jsons:
        if isinstance(error_json, dict) and "topic" in error_json:
            topic = error_json["topic"]
            count = error_json.get("count", 1)
            error_counts[topic] = error_counts.get(topic, 0) + count
        elif isinstance(error_json, list):  # 兼容列表形式的错误分析
            for item in error_json:
                if isinstance(item, dict) and "topic" in item:
                    topic = item["topic"]
                    count = item.get("count", 1)
                    error_counts[topic] = error_counts.get(topic, 0) + count

    top_common_errors = sorted(error_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    top_common_errors_list = [topic for topic, _ in top_common_errors]
    if not top_common_errors_list:
        top_common_errors_list = ["暂无高频错误知识点数据。"]

    # 构造并返回 DashboardMetrics 实例
    dashboard_metrics = DashboardMetrics(
        total_teachers=total_teachers,
        total_students=total_students,
        total_courses=total_courses,
        avg_prep_time_hours=round(avg_prep_time_hours, 2),
        avg_correction_time_minutes=round(avg_correction_time_minutes, 2),
        avg_student_accuracy=round(avg_student_accuracy, 2),
        top_common_errors=top_common_errors_list,
        active_teachers_today=active_teachers_today,
        active_students_today=active_students_today,
        active_teachers_week=active_teachers_week,
        active_students_week=active_students_week,
        course_optimization_suggestions=course_optimization_suggestions
    )

    return dashboard_metrics
