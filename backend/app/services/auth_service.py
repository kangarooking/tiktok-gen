"""
认证业务逻辑
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict
import secrets

from app.models.user import User, UserOAuthAccount, UserSession
from app.core.security import create_access_token, hash_sha256, hash_password, verify_password
from app.core.constants import OAuthProvider, UserTier
from app.integrations.github_oauth import GitHubOAuthClient
from app.config import settings
from app.core.exceptions import APIException


class AuthService:
    """认证服务"""

    def __init__(self, db: Session):
        self.db = db
        self.github_client = GitHubOAuthClient()

    async def get_github_auth_url(self) -> Dict:
        """获取GitHub OAuth授权URL"""
        state = secrets.token_urlsafe(32)
        auth_url = self.github_client.get_auth_url(state)
        return {"auth_url": auth_url, "state": state}

    async def handle_github_callback(self, code: str) -> Dict:
        """
        处理GitHub OAuth回调

        Args:
            code: GitHub返回的授权码

        Returns:
            包含token和用户信息的字典
        """
        # 1. 用code换取access_token
        token_data = await self.github_client.get_access_token(code)

        # 2. 获取GitHub用户信息
        github_user = await self.github_client.get_user_info(
            token_data.get("access_token")
        )

        # 3. 查找或创建用户
        user = self._find_or_create_user(github_user, token_data)

        # 4. 生成JWT Token
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # 5. 创建会话记录
        self._create_session(user.id, access_token)

        # 6. 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        self.db.commit()

        return {
            "token": access_token,
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "tier": user.tier  # 直接使用字符串
            }
        }

    def _find_or_create_user(self, github_user: Dict, token_data: Dict) -> User:
        """
        查找或创建用户

        Args:
            github_user: GitHub用户信息
            token_data: OAuth token数据

        Returns:
            用户对象
        """
        # 先通过provider_user_id查找 - 使用字符串值
        oauth_account = self.db.query(UserOAuthAccount).filter(
            UserOAuthAccount.provider == "github",
            UserOAuthAccount.provider_user_id == str(github_user.get("id"))
        ).first()

        if oauth_account:
            # 更新OAuth信息
            oauth_account.access_token = token_data.get("access_token")
            oauth_account.token_expires_at = (
                datetime.fromtimestamp(token_data.get("expires_at"))
                if token_data.get("expires_at")
                else None
            )
            user = oauth_account.user
        else:
            # 创建新用户 - 使用字符串值
            user = User(
                username=github_user.get("login"),
                email=github_user.get("email"),
                avatar_url=github_user.get("avatar_url"),
                tier="free",
                is_active=True,
                is_verified=True  # GitHub用户已验证
            )
            self.db.add(user)
            self.db.flush()

            # 创建OAuth关联 - 使用字符串值
            oauth_account = UserOAuthAccount(
                user_id=user.id,
                provider="github",
                provider_user_id=str(github_user.get("id")),
                provider_username=github_user.get("login"),
                provider_email=github_user.get("email"),
                provider_avatar_url=github_user.get("avatar_url"),
                access_token=token_data.get("access_token")
            )
            self.db.add(oauth_account)
            self.db.commit()

        return user

    def _create_session(self, user_id: str, token: str):
        """
        创建会话记录

        Args:
            user_id: 用户ID
            token: JWT Token
        """
        session = UserSession(
            user_id=user_id,
            token_hash=hash_sha256(token),
            expires_at=datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            is_valid=True
        )
        self.db.add(session)
        self.db.commit()

    async def logout(self, user_id: str):
        """
        登出 - 标记所有会话为失效

        Args:
            user_id: 用户ID
        """
        self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_valid == True
        ).update({
            "is_valid": False,
            "revoked_at": datetime.utcnow()
        })
        self.db.commit()

    async def register(self, username: str, password: str) -> Dict:
        """
        用户注册

        Args:
            username: 用户名
            password: 密码

        Returns:
            包含token和用户信息的字典
        """
        # 检查用户名是否已存在
        existing_user = self.db.query(User).filter(
            User.username == username
        ).first()

        if existing_user:
            raise APIException(message="用户名已存在", code=400)

        # 创建新用户
        user = User(
            username=username,
            password_hash=hash_password(password),
            tier="free",
            is_active=True,
            is_verified=False
        )
        self.db.add(user)
        self.db.flush()

        # 生成JWT Token
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # 创建会话记录
        self._create_session(user.id, access_token)

        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        self.db.commit()

        return {
            "token": access_token,
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "tier": user.tier
            }
        }

    async def login(self, username: str, password: str) -> Dict:
        """
        用户登录

        Args:
            username: 用户名
            password: 密码

        Returns:
            包含token和用户信息的字典
        """
        # 查找用户
        user = self.db.query(User).filter(
            User.username == username
        ).first()

        if not user:
            raise APIException(message="用户名或密码错误", code=401)

        # 验证密码
        if not user.password_hash or not verify_password(password, user.password_hash):
            raise APIException(message="用户名或密码错误", code=401)

        # 检查用户是否被禁用
        if not user.is_active:
            raise APIException(message="账户已被禁用", code=403)

        # 生成JWT Token
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # 创建会话记录
        self._create_session(user.id, access_token)

        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        self.db.commit()

        return {
            "token": access_token,
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "tier": user.tier
            }
        }
