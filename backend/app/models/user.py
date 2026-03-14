"""
用户相关数据模型
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Integer, DECIMAL, BIGINT, Date
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.database import Base
from app.core.constants import UserTier, OAuthProvider


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 基本信息
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(255), unique=True)
    password_hash = Column(String(255))  # OAuth用户可为空
    avatar_url = Column(String(500))

    # 订阅信息 - 直接使用 String，让 PostgreSQL 验证 enum
    tier = Column(String(20), nullable=False, default="free")
    tier_expires_at = Column(DateTime(timezone=True))

    # 状态
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True))

    # 关系
    oauth_accounts = relationship("UserOAuthAccount", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    usage_records = relationship("UserUsage", back_populates="user", cascade="all, delete-orphan")
    api_configs = relationship("UserApiConfig", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, tier={self.tier})>"


class UserOAuthAccount(Base):
    """OAuth账户关联表"""
    __tablename__ = "user_oauth_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # OAuth信息 - 直接使用 String，让 PostgreSQL 验证 enum
    provider = Column(String(20), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    provider_username = Column(String(255))
    provider_email = Column(String(255))
    provider_avatar_url = Column(String(500))

    # Token信息 (可选存储)
    access_token = Column(String)
    refresh_token = Column(String)
    token_expires_at = Column(DateTime(timezone=True))

    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="oauth_accounts")

    def __repr__(self):
        return f"<UserOAuthAccount(id={self.id}, provider={self.provider}, provider_user_id={self.provider_user_id})>"


class UserSession(Base):
    """用户会话表"""
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Token信息
    token_hash = Column(String(64), nullable=False, unique=True)

    # 设备信息
    device_info = Column(String)  # JSON格式存储

    # 状态
    is_valid = Column(Boolean, nullable=False, default=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))

    # 关系
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, is_valid={self.is_valid})>"


class UserUsage(Base):
    """用户用量表"""
    __tablename__ = "user_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 计费周期
    billing_cycle_start = Column(Date, nullable=False)
    billing_cycle_end = Column(Date, nullable=False)

    # 用量统计
    videos_generated = Column(Integer, nullable=False, default=0)
    minutes_used = Column(DECIMAL(10, 2), nullable=False, default=0)
    storage_used_bytes = Column(BIGINT, nullable=False, default=0)
    api_calls = Column(Integer, nullable=False, default=0)

    # 限额 (从订阅计划同步)
    minutes_limit = Column(DECIMAL(10, 2), nullable=False)
    storage_limit_bytes = Column(BIGINT, nullable=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="usage_records")

    def __repr__(self):
        return f"<UserUsage(id={self.id}, user_id={self.user_id}, minutes_used={self.minutes_used})>"
