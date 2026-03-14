"""
User API Configuration Model

Stores user-specific API configurations for third-party services.
Supports both user-level and system-level configurations.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.database import Base


class UserApiConfig(Base):
    """
    User API Configuration Table

    Stores API configurations for various third-party services.
    Configurations can be user-specific or system-level defaults.
    """
    __tablename__ = "user_api_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User association (nullable for system-level configs)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Category: ai_image, cloud_storage, digital_human, tts, llm
    category = Column(String(30), nullable=False, index=True)

    # Provider: openai, aliyun_oss, wavespeed, etc.
    provider = Column(String(50), nullable=False)

    # Encrypted configuration data (JSON string encrypted with Fernet)
    config_data = Column(Text, nullable=False)

    # User-friendly display name
    display_name = Column(String(100), nullable=True)

    # Status flags
    is_active = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False)  # Default for this category
    is_system = Column(Boolean, nullable=False, default=False)   # System-level config from .env

    # Validation status
    is_validated = Column(Boolean, nullable=False, default=False)
    last_validated_at = Column(DateTime(timezone=True), nullable=True)
    validation_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationship to user
    user = relationship("User", back_populates="api_configs")

    # Unique constraint: one config per user per category per provider
    # System configs (user_id=NULL) also follow this constraint
    __table_args__ = (
        UniqueConstraint(
            'user_id', 'category', 'provider',
            name='uq_user_category_provider'
        ),
        # Index for efficient queries
        # Index('ix_user_api_configs_user_category', 'user_id', 'category'),  # Covered by individual indexes
    )

    def __repr__(self):
        return f"<UserApiConfig(id={self.id}, user_id={self.user_id}, category={self.category}, provider={self.provider})>"

    def to_dict(self):
        """Convert to dictionary (without sensitive data)"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "category": self.category,
            "provider": self.provider,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "is_system": self.is_system,
            "is_validated": self.is_validated,
            "last_validated_at": self.last_validated_at.isoformat() if self.last_validated_at else None,
            "validation_error": self.validation_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
