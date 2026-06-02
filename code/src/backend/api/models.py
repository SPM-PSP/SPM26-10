# Pydantic 模型定义（用于请求和响应数据校验）

import datetime
import uuid
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict

# 登录相关模型-------------------

#记录用户登录请求（用户名+密码）
class LoginRequest(BaseModel):
    username: str
    password: str

#返回登录状态、消息和会话 ID
class LoginResponse(BaseModel):
    status: str
    message: str
    session_id: Optional[str] = None # 返回会话ID

class UserInfoResponse(BaseModel):
    userId: int
    userName: str
    userRole: str

# 教师侧模型-------------------

#教师生成教案的请求参数（课程大纲、年级、时长等）
class LessonPlanRequest(BaseModel):
    course_outline: str = Field(..., description="课程大纲或主题，用于生成教学内容。", examples=["第一章 Linux文件系统基础"])
    course_level: str = Field("大三", description="课程的适用年级或水平。", examples=["大学三年级"])
    expected_duration_hours: Optional[int] = Field(None, description="期望的课程总时长（小时）。", examples=[10])
    subject: Optional[str] = Field(None, description="课程所属学科。")

#返回生成的教案内容和元数据
class LessonPlanResponse(BaseModel):
    status: str = Field(..., description="操作状态。")
    lesson_plan: str = Field(..., description="生成的详细教学内容。")
    generated_at: datetime.datetime = Field(..., description="生成时间。")
    resource_id: Optional[str] = None

#教师生成考核题目的参数（题型、难度、数量等）
class AssessmentQuestionRequest(BaseModel):
    topic: str = Field(..., description="考核题目所属的主题或知识点。", examples=["Linux进程管理"])
    question_type: str = Field("选择题", description="期望生成的题目类型（如选择题、填空题、简答题、编程题）。", examples=["编程题"])
    difficulty_level: str = Field("中等", description="期望的题目难度（如简单、中等、困难）。", examples=["困难"])
    num_questions: int = Field(1, ge=1, le=10, description="期望生成的题目数量（1-10）。", examples=[3])
    programming_language: Optional[str] = Field(None, description="如果生成编程题，指定编程语言（如Python, C）。", examples=["C"])
    subject: Optional[str] = Field(None, description="考核题目所属学科。")

#返回生成的题目和参考答案
class AssessmentQuestionResponse(BaseModel):
    status: str = Field(..., description="操作状态。")
    assessment_content: str = Field(..., description="生成的考核题目及参考答案。")
    generated_at: datetime.datetime = Field(..., description="生成时间。")
    resource_id: str
    questions: List["GeneratedQuestionResponse"] = Field(default_factory=list)

#提交学生答案和参考示例，请求批改
class StudentAnswerCorrectionRequest(BaseModel):
    question: str = Field(..., description="学生回答的原始问题。", examples=["请解释Linux中的僵尸进程。"])
    student_answer: str = Field(..., description="学生的具体回答内容。", examples=["僵尸进程是已经死掉的进程。"])
    # course_id: Optional[uuid.UUID] = None  # 确保有course_id字段
    course_id: Optional[str] = None  # 确保有course_id字段
    # resource_id: Optional[uuid.UUID] = None
    resource_id: Optional[str] = None
    student_id: int
    reference_answer: Optional[str] = None

#返回批改反馈和批改时间
class CorrectionFeedbackResponse(BaseModel):
    status: str = Field(..., description="操作状态。")
    feedback: str = Field(..., description="对学生答案的批改反馈。")
    corrected_at: datetime.datetime = Field(..., description="批改时间。")

# 学生侧模型--------------------

#学生提问的请求参数（问题内容）
class StudentQuestionRequest(BaseModel):
    question: str = Field(..., description="学生提出的问题。", examples=["如何使用gdb调试C语言程序？"])

#返回 LLM 生成的答案和原始问题
class StudentQuestionResponse(BaseModel):
    status: str = Field(..., description="操作状态。")
    question: str = Field(..., description="学生提出的原始问题。")
    answer: str = Field(..., description="LLM 生成的回答。")

#学生请求生成练习题的参数（主题、数量等）
class PracticeQuestionRequest(BaseModel):
    student_id: int = Field(..., description="学生ID，用于检索其历史练习数据（当前未实现个性化）。")
    topic_focus: Optional[str] = Field(None, description="（可选）指定练习题目要侧重的知识点。", examples=["进程间通信"])
    num_questions: int = Field(1, ge=1, le=5, description="期望生成的练习题目数量（1-5）。", examples=[2])

    question_type: Optional[Literal["选择题", "填空题", "简答题", "编程题", "混合"]] = "混合"

#返回生成的练习题和答案
class PracticeQuestionResponse(BaseModel):
    status: str = Field(..., description="操作状态。")
    practice_questions: str = Field(..., description="生成的练习题目和答案。")
    generated_at: datetime.datetime = Field(..., description="生成时间。")
    resource_id: str
    questions: List["GeneratedQuestionResponse"] = Field(default_factory=list)

# 管理侧模型-----------------

#管理员创建用户的请求（用户名、密码、角色）
class UserCreateRequest(BaseModel):
    username: str = Field(..., description="新用户的用户名。", examples=["new_teacher"])
    password: str = Field(..., description="新用户的密码。", examples=["secure_pass"])
    role: str = Field(..., description="用户角色（admin, teacher, student）。", examples=["teacher"])

#返回用户创建结果和分配的 ID
class UserCreateResponse(BaseModel):
    status: str
    message: str
    user_id: Optional[int] = None

#返回用户列表信息（不含密码）
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

#描述教学资源元数据（ID、标题、类型、创建者等）
class ResourceMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="资源的唯一ID。")
    title: str = Field(..., description="资源的标题。")
    resource_type: str = Field(..., description="资源类型（如 lesson_plan, assessment）。")
    created_by_user_id: int = Field(..., description="创建者的用户ID。")
    created_at: datetime.datetime = Field(..., description="创建时间。")
    file_path: str = Field(..., description="资源在文件系统中的路径（实际不直接暴露给前端）。")
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="额外元数据。")
    subject: Optional[str] = Field(None, description="资源所属学科。")

#返回仪表盘统计数据（用户数、活跃度、正确率等）
class DashboardMetrics(BaseModel):
    total_teachers: int = Field(..., description="教师总数。")
    total_students: int = Field(..., description="学生总数。")
    total_courses: int = Field(..., description="课程总数。")
    avg_prep_time_hours: Optional[float] = Field(None, description="平均备课耗时（小时）。")
    avg_correction_time_minutes: Optional[float] = Field(None, description="平均批改耗时（分钟）。")
    avg_student_accuracy: Optional[float] = Field(None, description="学生平均正确率。")
    # top_common_errors: List[str] = Field(default_factory=list, description="高频错误知识点列表。")
    top_common_errors: List[str] = Field(..., description="高频错误知识点列表。")

    active_teachers_today: int = Field(0, description="当日活跃教师数。")
    active_students_today: int = Field(0, description="当日活跃学生数。")
    active_teachers_week: int = Field(0, description="本周活跃教师数。")
    active_students_week: int = Field(0, description="本周活跃学生数。")
    # course_optimization_suggestions: List[str] = Field(default_factory=list, description="课程优化方向建议。")
    course_optimization_suggestions: List[str] = Field(..., description="课程优化方向建议。")

#请求导出资源的参数（资源 ID 列表、格式）
class ResourceExportRequest(BaseModel):
    resource_ids: List[str] = Field(..., description="要导出的资源ID列表。")
    export_format: str = Field("markdown", description="导出格式，例如 'markdown', 'pdf'。", examples=["markdown"])

#返回导出结果和文件下载链接（模拟）
class ResourceExportResponse(BaseModel):
    status: str = Field(..., description="操作状态。")
    message: str = Field(..., description="导出结果消息。")
    exported_file_url: Optional[str] = Field(None, description="导出文件下载URL（模拟）。")

# 前端获取资源详细内容的模型
class ResourceContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True) # 同样需要从 SQLAlchemy ORM 对象转换

    id: str = Field(..., description="资源的唯一ID。")
    title: str = Field(..., description="资源的标题。")
    resource_type: str = Field(..., description="资源类型（如 lesson_plan, assessment）。")
    created_by_user_id: int = Field(..., description="创建者的用户ID。")
    created_at: datetime.datetime = Field(..., description="创建时间。")
    file_path: Optional[str] = Field(None, description="资源在文件系统中的路径。")
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="额外JSON格式元数据。")

    content: Optional[str] = None  # <-- 新增此字段
    subject: Optional[str] = None  # 确保与Resource模型匹配

#课程管理-------------------

#创建课程的请求参数（标题、描述）
class CourseCreateRequest(BaseModel):
    title: str = Field(..., max_length=255, description="课程标题")
    description: Optional[str] = Field(None, max_length=1000, description="课程描述")
    # 如果课程与特定教师关联，可以添加 teacher_id
    # teacher_id: Optional[str] = None # 或 Field(..., description="负责该课程的教师ID")

#返回课程基本信息（ID、标题、创建时间等）
class CourseResponse(BaseModel):
    id: str # 确保ID类型与数据库模型一致，如果是UUID，则为str
    title: str
    description: Optional[str] = None
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True) # 启用 Pydantic 从 ORM 模型直接读取


# 班级与试卷-------------------

class ClassCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class ClassJoinRequest(BaseModel):
    class_code: str = Field(..., min_length=4, max_length=32)


class ClassMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: int
    student_name: str
    joined_at: datetime.datetime
    status: str


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    class_code: str
    teacher_id: int
    teacher_name: Optional[str] = None
    status: str = "active"
    created_at: datetime.datetime
    updated_at: datetime.datetime
    member_count: int = 0


class ClassDetailResponse(ClassResponse):
    members: List[ClassMemberResponse] = Field(default_factory=list)


class PaperQuestionInput(BaseModel):
    id: Optional[str] = None
    question_type: str
    question_content: str
    reference_answer: Optional[str] = None
    score: float = 10.0
    difficulty_level: Optional[str] = None
    sort_order: int = 1
    metadata_json: Optional[Dict[str, Any]] = None


class PaperSectionInput(BaseModel):
    id: Optional[str] = None
    section_title: str
    source_module_name: Optional[str] = None
    sort_order: int = 1
    questions: List[PaperQuestionInput] = Field(default_factory=list)


class PaperFromLessonPlanRequest(BaseModel):
    source_resource_id: str
    title: Optional[str] = None
    question_type: str = Field("混合")
    difficulty_level: str = Field("中等")
    questions_per_section: int = Field(2, ge=1, le=10)
    max_sections: int = Field(4, ge=1, le=12)


class PaperUpdateRequest(BaseModel):
    title: str
    status: Optional[str] = None
    sections: List[PaperSectionInput] = Field(default_factory=list)


class PaperPublicationRequest(BaseModel):
    class_id: str
    deadline: Optional[datetime.datetime] = None


class PaperQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    question_type: str
    question_content: str
    reference_answer: Optional[str] = None
    score: float
    difficulty_level: Optional[str] = None
    sort_order: int
    metadata_json: Optional[Dict[str, Any]] = None


class PaperSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    section_title: str
    source_module_name: Optional[str] = None
    sort_order: int
    questions: List[PaperQuestionResponse] = Field(default_factory=list)


class PaperResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    source_resource_id: Optional[str] = None
    created_by_teacher_id: int
    class_id: Optional[str] = None
    status: str
    total_score: float
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    sections: List[PaperSectionResponse] = Field(default_factory=list)
    publication_count: int = 0


class PaperPublicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    paper_id: str
    class_id: str
    class_name: Optional[str] = None
    published_by: int
    published_at: datetime.datetime
    deadline: Optional[datetime.datetime] = None
    status: str


class StudentPaperListItem(BaseModel):
    id: str
    publication_id: str
    title: str
    class_name: str
    teacher_name: str
    published_at: datetime.datetime
    deadline: Optional[datetime.datetime] = None
    status: str
    total_score: float


class StudentPaperDetailResponse(BaseModel):
    publication_id: str
    paper: PaperResponse
    class_name: str
    teacher_name: str
    published_at: datetime.datetime
    deadline: Optional[datetime.datetime] = None


class PaperSubmissionAnswerInput(BaseModel):
    question_id: str
    student_answer: str


class PaperSubmissionRequest(BaseModel):
    answers: List[PaperSubmissionAnswerInput] = Field(..., min_length=1)


class PaperSubmissionAnswerResponse(BaseModel):
    id: str
    question_id: str
    question_content: str
    question_type: str
    reference_answer: Optional[str] = None
    student_answer: str
    auto_feedback: Optional[str] = None
    score: float
    max_score: float
    is_correct: Optional[bool] = None
    error_tags_json: Optional[Dict[str, Any]] = None
    corrected_at: Optional[datetime.datetime] = None


class PaperSubmissionResponse(BaseModel):
    id: str
    paper_id: str
    publication_id: str
    student_id: int
    student_name: Optional[str] = None
    submitted_at: datetime.datetime
    status: str
    total_score: float
    max_score: float
    correctness_percentage: Optional[float] = None
    error_analysis_json: Optional[Dict[str, Any]] = None
    answers: List[PaperSubmissionAnswerResponse] = Field(default_factory=list)


class TeacherPaperSubmissionSummary(BaseModel):
    id: str
    student_id: int
    student_name: str
    submitted_at: datetime.datetime
    total_score: float
    max_score: float
    correctness_percentage: Optional[float] = None
    status: str


class GeneratedQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    resource_id: str
    question_type: Literal["选择题", "填空题", "简答题", "编程题"]
    question_content: str
    options: List[str] = Field(default_factory=list)
    reference_answer: Optional[str] = None
    score: float
    difficulty_level: Optional[str] = None
    sort_order: int
    metadata_json: Optional[Dict[str, Any]] = None


class GeneratedQuestionSetResponse(BaseModel):
    id: str
    title: str
    resource_type: Literal["assessment", "practice"]
    created_by_user_id: int
    created_at: datetime.datetime
    subject: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    content: Optional[str] = None
    questions: List[GeneratedQuestionResponse] = Field(default_factory=list)


class LessonPlanDetailResponse(BaseModel):
    id: str
    title: str
    created_by_user_id: int
    created_at: datetime.datetime
    metadata_json: Optional[Dict[str, Any]] = None
    subject: Optional[str] = None
    content: str


class LessonPlanUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)


class LessonPlanReviseRequest(BaseModel):
    revision_instruction: str = Field(..., min_length=1)
    save_as_new: bool = False
    title: Optional[str] = Field(None, max_length=500)


class AppendGeneratedQuestionsRequest(BaseModel):
    resource_id: str
    section_title: Optional[str] = None


class PracticeSubmissionAnswerInput(BaseModel):
    question_id: str
    student_answer: str


class PracticeSubmissionRequest(BaseModel):
    answers: List[PracticeSubmissionAnswerInput] = Field(..., min_length=1)


class PracticeSubmissionAnswerResponse(BaseModel):
    question_id: str
    question_content: str
    question_type: str
    reference_answer: Optional[str] = None
    student_answer: str
    auto_feedback: Optional[str] = None
    score: float
    max_score: float
    is_correct: Optional[bool] = None
    error_tags_json: Optional[Dict[str, Any]] = None


class PracticeSubmissionResponse(BaseModel):
    resource_id: str
    total_score: float
    max_score: float
    correctness_percentage: Optional[float] = None
    answers: List[PracticeSubmissionAnswerResponse] = Field(default_factory=list)
