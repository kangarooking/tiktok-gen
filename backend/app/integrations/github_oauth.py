"""
GitHub OAuth集成
"""
import httpx
from typing import Dict, Optional
from app.config import settings


class GitHubOAuthClient:
    """GitHub OAuth客户端"""

    def __init__(self):
        self.client_id = settings.GITHUB_CLIENT_ID
        self.client_secret = settings.GITHUB_CLIENT_SECRET
        self.redirect_uri = settings.GITHUB_REDIRECT_URI

    def get_auth_url(self, state: str) -> str:
        """
        生成GitHub OAuth授权URL

        Args:
            state: 随机状态字符串，用于防CSRF

        Returns:
            授权URL
        """
        return (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&scope=user:email"
            f"&state={state}"
        )

    async def get_access_token(self, code: str) -> Dict:
        """
        用授权码换取访问令牌

        Args:
            code: GitHub返回的授权码

        Returns:
            包含access_token的字典
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> Dict:
        """
        获取GitHub用户信息

        Args:
            access_token: GitHub访问令牌

        Returns:
            用户信息字典
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
            )
            response.raise_for_status()
            user_data = response.json()

            # 获取用户邮箱（如果公开）
            if not user_data.get("email"):
                email_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json"
                    }
                )
                email_response.raise_for_status()
                emails = email_response.json()
                primary_email = next((e for e in emails if e.get("primary")), None)
                if primary_email:
                    user_data["email"] = primary_email.get("email")

            return user_data
