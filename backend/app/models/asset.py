"""
资产相关数据模型
"""
from sqlalchemy import Column, String, Text, Boolean, Integer, BigInteger, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from app.database import Base
from app.core.constants import AssetType, AssetSource, AssetStatus


class Asset(Base):
    """资产表 (形象/音色/脚本)"""
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))  # NULL表示系统资产

    # 基本信息 - 直接使用 String，让 PostgreSQL 验证 enum
    type = Column(String(20), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text)

    # 来源与状态
    source = Column(String(20), nullable=False, default="upload")
    status = Column(String(20), nullable=False, default="ready")
    is_system = Column(Boolean, nullable=False, default=False)
    is_public = Column(Boolean, nullable=False, default=False)

    # 文件信息
    file_url = Column(String(500))  # 主文件URL (形象图片/音频文件)
    file_size_bytes = Column(BigInteger)
    file_mime_type = Column(String(100))
    preview_url = Column(String(500))  # 预览URL (音色预览音频)
    thumbnail_url = Column(String(500))  # 缩略图URL

    # 内容 (脚本类型使用)
    content = Column(Text)

    # 元数据 (JSON格式，不同类型存储不同信息)
    meta_data = Column("metadata", JSONB, nullable=False, default={})

    # AI生成相关
    generation_task_id = Column(String(100))
    generation_prompt = Column(Text)
    generation_error = Column(Text)

    # 统计
    use_count = Column(Integer, nullable=False, default=0)

    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    tags = relationship("AssetTag", back_populates="asset", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Asset(id={self.id}, type={self.type}, title={self.title}, is_system={self.is_system})>"


class AssetTag(Base):
    """资产标签表 (多对多关系)"""
    __tablename__ = "asset_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String(50), nullable=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # 关系
    asset = relationship("Asset", back_populates="tags")

    def __repr__(self):
        return f"<AssetTag(id={self.id}, asset_id={self.asset_id}, tag={self.tag})>"
