import os
from sqlalchemy import select, func, text, and_
from fastapi import APIRouter, HTTPException, Depends, status, Header,Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import uuid # 用于生成唯一ID
import hashlib # 用于密码哈希
import time
from src.backend.core.llm_manager import generate_text_with_qwen3, initialize_llm_runtime, stream_text_with_qwen3
from src.backend.rag_pipeline.vector_store_manager import initialize_vector_store

from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.database import User, LessonPlanTimeLog, CorrectionTimeLog,get_db, Resource,Course,UserActivityLog,StudentPerformance
from src.backend.api.models import (
    LoginRequest, LoginResponse,LessonPlanRequest, LessonPlanResponse,
    AssessmentQuestionRequest, AssessmentQuestionResponse,StudentAnswerCorrectionRequest, CorrectionFeedbackResponse,
    StudentQuestionRequest, StudentQuestionResponse,PracticeQuestionRequest, PracticeQuestionResponse,DashboardMetrics,
    UserCreateRequest, UserCreateResponse, UserResponse,ResourceMetadata, DashboardMetrics,ResourceContentResponse,
UserInfoResponse
)
from datetime import datetime, timedelta, timezone

router = APIRouter()


# --- 全局资源初始化（由 main.py 中的 initialize_endpoints_global_resources 填充）---
_vectorstore = None
_embeddings_model = None

# --- 全局内存会话管理---
# 存储 session_id -> User 对象的映射。ps：这在服务器重启后会丢失所有会话！
active_sessions: Dict[str, User] = {}

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
        final_instruction: str,max_new_tokens: int | None = 512,temperature: float = 0.7,top_p: float = 0.9) -> str:
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

#教师API(所有教师侧API都需要教师或管理员权限)-----------------

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

    # --- 存储生成的备课内容到数据库 ---
    resource_id = str(uuid.uuid4())
    file_path = f"generated_resources/lesson_plans/{resource_id}.md"

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

    # --- 根据 question_type 动态生成格式示例 ---
    format_example_content = ""
    if request.question_type == "选择题":
        format_example_content = """
    题目1: [题目内容]
    A. 选项A
    B. 选项B
    C. 选项C
    D. 选项D
    参考答案1: [正确选项，例如：A]

    题目2: ...
    参考答案2: ...
    """
    elif request.question_type == "编程题":
        # 确保代码块语言是小写，例如 "python" 而不是 "Python"
        lang_for_code_block = request.programming_language.lower() if request.programming_language else "python"
        format_example_content = f"""
    题目1: [题目内容]
    参考答案1:
    ```{lang_for_code_block}
    <完整的可运行代码>
    ```
    代码解释: [详细解释代码的逻辑和每部分的作用，包括必要的库导入和错误处理建议]

    题目2: ...
    参考答案2: ...
    """
    else:  # 填空题、简答题、问答题等通用格式
        format_example_content = """
    题目1: [题目内容]
    参考答案1: [参考答案内容]

    题目2: ...
    参考答案2: ...
    """

    # 构建 LLM 的系统指令 (System Instruction)
    system_instruction = f"你是一位专业的嵌入式Linux开发实践教程命题专家，擅长生成各种类型和难度的考核题目及参考答案。"

    # 构建 LLM 的用户问题 (User Question)
    user_question = f"""请为主题“{request.topic}”生成 {request.num_questions} 道{request.difficulty_level}难度的{request.question_type}。
    {programming_lang_hint}
    要求每道题目清晰，具有代表性。如果生成编程题，请同时提供完整的、**可直接运行**的参考代码和**详细的解释**，并**包含所有必要的库导入**和**常见错误处理**。

    请严格按照以下格式生成题目和答案，**确保只生成 {request.num_questions} 道题目，不多也不少**：
    ---
    {format_example_content.strip()}
    ---
    """
    # 构建 LLM 的最终指令 (Final Instruction)
    final_instruction = "请严格按照上述格式生成题目和答案，不要包含任何额外说明或分析文字。只返回题目和答案内容本身。"

    assessment_content = await _get_llm_response(
        system_instruction=system_instruction,
        user_question=user_question,
        retrieved_documents_content=retrieved_docs_content,
        final_instruction=final_instruction,
        max_new_tokens=2000,
        temperature=0.7,
        top_p=0.9
    )

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
    await db.commit()
    await db.refresh(new_resource)

    # --- 记录用户活动日志 ---
    await _log_user_activity(db, current_user_id, "generate_assessment",
                             {"resource_id": str(new_resource.id),
                              # "subject": request.subject, # 如果 request.subject 不存在，请将其改为 request.topic
                              "subject": request.subject if request.subject else request.topic, # <-- 推荐的修改
                              "question_type": request.question_type,
                              "difficulty_level": request.difficulty_level})

    return AssessmentQuestionResponse(status="success", assessment_content=assessment_content,
                                      generated_at=datetime.now(), resource_id=new_resource.id)

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
        max_new_tokens=700,
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
        max_new_tokens=800,
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
                max_new_tokens=800,
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

    system_instruction = "你是一名专业的教学助手，擅长根据知识点生成合适的练习题目。"
    topic_hint = f"（侧重知识点：{request.topic_focus}）" if request.topic_focus else ""

    # --- 根据 request.question_type 动态调整题目类型提示 ---
    type_instruction = ""
    if request.question_type == "混合":
        type_instruction = "题目可以是选择题、填空题、简答题或小型编程片段。"
    elif request.question_type == "编程题":
        type_instruction = "只生成小型编程题目。"
    else:
        type_instruction = f"只生成{request.question_type}。"

    user_question = f"""请为学生ID为“{current_user_id}”生成 {request.num_questions} 道关于《嵌入式Linux开发实践教程》的随练题目{topic_hint}。
    {type_instruction} 请给出题目和参考答案。

    生成格式示例（请按此格式返回）：
    ---
    题目1: [题目内容]
    参考答案1: [参考答案内容]
    [编程题：
    ```<lang>
    <代码>
    ```
    代码解释：...]

    题目2: ...
    参考答案2: ...
    ---
    """
    final_instruction = "请严格按照上述格式生成题目和答案。"

    practice_content = await _get_llm_response(
        system_instruction=system_instruction,
        user_question=user_question,
        retrieved_documents_content=retrieved_docs_content,
        final_instruction=final_instruction,
        max_new_tokens=800,
        temperature=0.7,
        top_p=0.9
    )

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
    await db.commit()
    await db.refresh(new_resource)

    # --- 记录用户活动日志 ---
    await _log_user_activity(db, current_user_id, "generate_practice",
                             {"resource_id": str(new_resource.id),
                              "topic_focus": request.topic_focus,
                              "num_questions": request.num_questions,
                              "question_type": request.question_type}) # 记录题型

    return PracticeQuestionResponse(status="success", practice_questions=practice_content,
                                    generated_at=datetime.now(), resource_id=new_resource.id)

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
            max_new_tokens=500,
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
            max_new_tokens=500,
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
