"""
项目相关数据模型
"""
from sqlalchemy import Column, String, Text, Integer, DECIMAL, BigInteger, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from app.database import Base
from app.core.constants import ProjectStatus, VideoResolution


class Project(Base):
    """项目表 (视频生成任务)"""
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 基本信息
    title = Column(String(200), nullable=False)

    # 状态 - 直接使用 String，让 PostgreSQL 验证 enum
    status = Column(String(30), nullable=False, default="pending")
    progress = Column(Integer, nullable=False, default=0)
    current_step = Column(String(100))

    # 关联资产
    avatar_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False)
    voice_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False)
    script_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"))

    # 脚本内容 (如果不使用资产库脚本)
    script_content = Column(Text)

    # 生成配置
    config = Column(JSONB, nullable=False, default={})

    # 生成结果
    video_url = Column(String(500))
    audio_url = Column(String(500))
    thumbnail_url = Column(String(500))
    duration_seconds = Column(DECIMAL(10, 2))
    resolution = Column(String(10))
    file_size_bytes = Column(BigInteger)

    # 第三方API任务ID
    tts_task_id = Column(String(100))
    video_task_id = Column(String(100))

    # 错误信息
    error_message = Column(Text)
    error_code = Column(String(50))
    retry_count = Column(Integer, nullable=False, default=0)

    # 费用统计
    credits_used = Column(DECIMAL(10, 4), nullable=False, default=0)

    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # 关系
    logs = relationship("ProjectLog", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, title={self.title}, status={self.status}, progress={self.progress})>"


class ProjectLog(Base):
    """项目日志表 (记录生成过程)"""
    __tablename__ = "project_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # 日志信息
    level = Column(String(20), nullable=False, default="info")  # info, warning, error, debug
    step = Column(String(100))
    message = Column(Text, nullable=False)
    details = Column(JSONB)

    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # 关系
    project = relationship("Project", back_populates="logs")

    def __repr__(self):
        return f"<ProjectLog(id={self.id}, project_id={self.project_id}, level={self.level}, step={self.step})>"
