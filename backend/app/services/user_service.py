"""
用户业务逻辑
"""
from datetime import date, datetime
from sqlalchemy.orm import Session
from typing import Dict

from app.models.user import User, UserUsage
from app.core.constants import UserTier, SUBSCRIPTION_PLANS


class UserService:
    """用户服务"""

    def __init__(self, db: Session):
        self.db = db

    async def get_user_usage(self, user_id: str) -> Dict:
        """
        获取用户用量统计

        Args:
            user_id: 用户ID

        Returns:
            用量统计字典
        """
        # 获取当前计费周期的用量记录
        today = date.today()
        cycle_start = today.replace(day=1)

        # 计算下个月第一天
        if cycle_start.month < 12:
            cycle_end = cycle_start.replace(month=cycle_start.month + 1, day=1)
        else:
            cycle_end = cycle_start.replace(year=cycle_start.year + 1, month=1, day=1)

        usage = self.db.query(UserUsage).filter(
            UserUsage.user_id == user_id,
            UserUsage.billing_cycle_start == cycle_start
        ).first()

        # 如果没有记录，获取用户订阅计划并创建默认记录
        if not usage:
            user = self.db.query(User).filter(User.id == user_id).first()
            plan_config = SUBSCRIPTION_PLANS.get(user.tier, SUBSCRIPTION_PLANS[UserTier.FREE])

            usage = UserUsage(
                user_id=user_id,
                billing_cycle_start=cycle_start,
                billing_cycle_end=cycle_end,
                minutes_limit=plan_config["minutes_per_month"],
                storage_limit_bytes=plan_config["storage_mb"] * 1024 * 1024
            )
            self.db.add(usage)
            self.db.commit()
            self.db.refresh(usage)

        # 计算剩余额度
        minutes_remaining = max(0, float(usage.minutes_limit - usage.minutes_used))
        storage_remaining = max(0, usage.storage_limit_bytes - usage.storage_used_bytes)

        return {
            "user_id": str(user_id),
            "billing_cycle": {
                "start": usage.billing_cycle_start.isoformat(),
                "end": usage.billing_cycle_end.isoformat()
            },
            "videos_generated": usage.videos_generated,
            "minutes": {
                "used": float(usage.minutes_used),
                "limit": float(usage.minutes_limit),
                "remaining": minutes_remaining
            },
            "storage": {
                "used_bytes": usage.storage_used_bytes,
                "limit_bytes": usage.storage_limit_bytes,
                "remaining_bytes": storage_remaining,
                "used_mb": round(usage.storage_used_bytes / 1024 / 1024, 2),
                "limit_mb": round(usage.storage_limit_bytes / 1024 / 1024, 2)
            }
        }

    async def update_user(self, user_id: str, data: Dict) -> Dict:
        """
        更新用户信息

        Args:
            user_id: 用户ID
            data: 更新数据

        Returns:
            更新后的用户信息
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")

        if "username" in data and data["username"]:
            # 检查用户名是否已存在
            existing = self.db.query(User).filter(
                User.username == data["username"],
                User.id != user_id
            ).first()
            if existing:
                raise ValueError("用户名已被使用")
            user.username = data["username"]

        if "avatar_url" in data:
            user.avatar_url = data["avatar_url"]

        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)

        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "tier": user.tier.value
        }
