from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Mapped, mapped_column
from sqlalchemy import Column, Integer, func, JSON, ForeignKey, Float, String, Text, DateTime
from src.backend.config import settings
from typing import List, Optional

# 基类
Base = declarative_base()

# 用户模型
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50)) # "admin", "teacher", "student"
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关系 (Relationships)
    resources_created: Mapped[List["Resource"]] = relationship(
        "Resource", back_populates="creator", foreign_keys="[Resource.created_by_user_id]"
    )
    lesson_plan_time_logs: Mapped[List["LessonPlanTimeLog"]] = relationship(
        "LessonPlanTimeLog", back_populates="user", foreign_keys="[LessonPlanTimeLog.user_id]"
    )
    correction_time_logs: Mapped[List["CorrectionTimeLog"]] = relationship(
        "CorrectionTimeLog", back_populates="user", foreign_keys="[CorrectionTimeLog.user_id]"
    )
    student_performances: Mapped[List["StudentPerformance"]] = relationship(
        "StudentPerformance", back_populates="student", foreign_keys="[StudentPerformance.student_id]"
    )
    activity_logs: Mapped[List["UserActivityLog"]] = relationship(
        "UserActivityLog", back_populates="user", foreign_keys="[UserActivityLog.user_id]"
    )
    courses_created: Mapped[List["Course"]] = relationship(
        "Course", back_populates="creator", foreign_keys="[Course.created_by_user_id]"
    )


# 资源模型 (例如备课内容、题目等)
class Resource(Base):
    __tablename__ = "resources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500))
    resource_type: Mapped[str] = mapped_column(String(100)) # e.g., "lesson_plan", "assessment", "practice"
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id")) # 外键，指向User.id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True) # 实际文件存储路径
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # 存储额外JSON格式元数据
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # 新增字段：资源所属学科


    # 关系
    creator: Mapped["User"] = relationship(
        "User", back_populates="resources_created", foreign_keys="[Resource.created_by_user_id]"
    )
    lesson_plan_time_logs: Mapped[List["LessonPlanTimeLog"]] = relationship(
        "LessonPlanTimeLog", back_populates="resource", foreign_keys="[LessonPlanTimeLog.resource_id]"
    )
    correction_time_logs: Mapped[List["CorrectionTimeLog"]] = relationship(
        "CorrectionTimeLog", back_populates="resource", foreign_keys="[CorrectionTimeLog.resource_id]"
    )
    student_performances: Mapped[List["StudentPerformance"]] = relationship(
        "StudentPerformance", back_populates="resource", foreign_keys="[StudentPerformance.resource_id]"
    )
    activity_logs: Mapped[List["UserActivityLog"]] = relationship(
        "UserActivityLog", back_populates="related_resource", foreign_keys="[UserActivityLog.related_resource_id]"
    )


# 备课时间日志
class LessonPlanTimeLog(Base):
    __tablename__ = "lesson_plan_time_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    resource_id: Mapped[Optional[str]] = mapped_column(ForeignKey("resources.id"), nullable=True) # 关联的备课资源ID
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关系
    user: Mapped["User"] = relationship(
        "User", back_populates="lesson_plan_time_logs", foreign_keys="[LessonPlanTimeLog.user_id]"
    )
    resource: Mapped[Optional["Resource"]] = relationship(
        "Resource", back_populates="lesson_plan_time_logs", foreign_keys="[LessonPlanTimeLog.resource_id]"
    )


# 批改时间日志
class CorrectionTimeLog(Base):
    __tablename__ = "correction_time_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    resource_id: Mapped[Optional[str]] = mapped_column(ForeignKey("resources.id"), nullable=True) # 关联的被批改的资源ID (如练习或作业)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关系
    user: Mapped["User"] = relationship(
        "User", back_populates="correction_time_logs", foreign_keys="[CorrectionTimeLog.user_id]"
    )
    resource: Mapped[Optional["Resource"]] = relationship(
        "Resource", back_populates="correction_time_logs", foreign_keys="[CorrectionTimeLog.resource_id]"
    )


# 课程模型
class Course(Base):
    __tablename__ = "courses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id")) # 关联创建者
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # 关系
    creator: Mapped["User"] = relationship(
        "User", back_populates="courses_created", foreign_keys="[Course.created_by_user_id]"
    )
    student_performances: Mapped[List["StudentPerformance"]] = relationship(
        "StudentPerformance", back_populates="course", foreign_keys="[StudentPerformance.course_id]"
    )
    activity_logs: Mapped[List["UserActivityLog"]] = relationship(
        "UserActivityLog", back_populates="related_course", foreign_keys="[UserActivityLog.related_course_id]"
    )


# 学生学习表现模型
class StudentPerformance(Base):
    __tablename__ = "student_performance"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    course_id: Mapped[Optional[str]] = mapped_column(ForeignKey("courses.id"), nullable=True) # 关联课程
    resource_id: Mapped[Optional[str]] = mapped_column(ForeignKey("resources.id"), nullable=True) # 关联的具体练习/考核资源
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # 得分
    total_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # 总分，用于计算正确率
    correctness_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # 正确率
    error_analysis_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # 存储JSON格式的错误点分析
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    assessment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True,
                                                           comment="本次评估的类型，例如：选择题、编程题、期末测试等")
    # 关系
    student: Mapped["User"] = relationship(
        "User", back_populates="student_performances", foreign_keys="[StudentPerformance.student_id]"
    )
    course: Mapped[Optional["Course"]] = relationship(
        "Course", back_populates="student_performances", foreign_keys="[StudentPerformance.course_id]"
    )
    resource: Mapped[Optional["Resource"]] = relationship(
        "Resource", back_populates="student_performances", foreign_keys="[StudentPerformance.resource_id]"
    )


# 用户活动日志
class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    activity_type: Mapped[str] = mapped_column(String(255), index=True) # 例如: "login", "generate_lesson_plan", "ask_question"
    related_resource_id: Mapped[Optional[str]] = mapped_column(ForeignKey("resources.id"), nullable=True)
    related_course_id: Mapped[Optional[str]] = mapped_column(ForeignKey("courses.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # 活动的额外详细信息

    # 关系
    user: Mapped["User"] = relationship(
        "User", back_populates="activity_logs", foreign_keys="[UserActivityLog.user_id]"
    )
    related_resource: Mapped[Optional["Resource"]] = relationship(
        "Resource", back_populates="activity_logs", foreign_keys="[UserActivityLog.related_resource_id]"
    )
    related_course: Mapped[Optional["Course"]] = relationship(
        "Course", back_populates="activity_logs", foreign_keys="[UserActivityLog.related_course_id]"
    )


# 创建异步引擎
engine = create_async_engine(settings.DATABASE_URL, echo=True) # echo=True 会打印SQL语句

# 创建异步会话
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False # 避免在commit后立即卸载对象
)

# 数据库初始化函数
async def init_db():
    async with engine.begin() as conn:
        # 假设你已经手动创建了数据库 'educational_platform_db'
        await conn.run_sync(Base.metadata.create_all)
    print("数据库初始化完成，表结构已检查/创建。")


# 依赖注入函数，获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session