"""
WaveSpeed AI数字人API集成
"""
import httpx
import asyncio
from typing import Dict, Optional, Tuple
from app.config import settings
from app.integrations.base import DigitalHumanClientBase


class WaveSpeedClient(DigitalHumanClientBase):
    """WaveSpeed AI数字人API客户端"""

    @classmethod
    def get_provider_name(cls) -> str:
        return "wavespeed"

    @classmethod
    def get_category(cls) -> str:
        return "digital_human"

    @classmethod
    def get_required_fields(cls) -> list:
        return ["api_key", "base_url"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.get_config_value("api_key") or settings.WAVESPEED_API_KEY
        self.base_url = self.get_config_value("base_url") or settings.WAVESPEED_API_BASE_URL
        self.default_resolution = self.get_config_value("default_resolution") or settings.WAVESPEED_DEFAULT_RESOLUTION
        self.timeout = self.get_config_value("timeout") or settings.WAVESPEED_TIMEOUT

    async def validate_config(self) -> Tuple[bool, Optional[str]]:
        """Validate the configuration"""
        is_valid, error = self.validate_required_fields()
        if not is_valid:
            return is_valid, error
        return True, None

    async def generate_video(
        self,
        avatar_image_url: str,
        audio_url: str,
        **kwargs
    ) -> str:
        """
        Generate a digital human video

        Args:
            avatar_image_url: URL of the avatar image
            audio_url: URL of the audio file

        Returns:
            URL of the generated video
        """
        task_id = await self.create_video_task(
            audio_url=audio_url,
            image_url=avatar_image_url,
            prompt=kwargs.get("prompt", ""),
            resolution=kwargs.get("resolution"),
            seed=kwargs.get("seed", -1)
        )
        return await self.wait_for_completion(task_id)

    async def create_video_task(
        self,
        audio_url: str,
        image_url: str,
        prompt: str = "",
        resolution: str = None,
        seed: int = -1
    ) -> str:
        """
        创建数字人视频生成任务

        Args:
            audio_url: 音频URL
            image_url: 形象图片URL
            prompt: 正向提示词
            resolution: 视频分辨率 (480p/720p)
            seed: 随机种子

        Returns:
            任务ID

        Raises:
            Exception: 创建任务失败
        """
        resolution = resolution or self.default_resolution

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "audio": audio_url,
                "image": image_url,
                "prompt": prompt,
                "resolution": resolution,
                "seed": seed
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = await client.post(
                f"{self.base_url}/wavespeed-ai/infinitetalk",
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()

            if result.get("code") != 200:
                raise Exception(f"WaveSpeed API错误: {result}")

            return result["data"]["id"]

    async def get_task_result(self, task_id: str) -> Dict:
        """
        获取视频生成任务结果

        Args:
            task_id: 任务ID

        Returns:
            任务结果字典 {"status": "...", "video_url": "...", "error": "..."}

        Raises:
            Exception: 获取结果失败
        """
        async with httpx.AsyncClient(timeout=60) as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            try:
                response = await client.get(
                    f"{self.base_url}/predictions/{task_id}/result",
                    headers=headers
                )
                response.raise_for_status()

                result = response.json()

                if result.get("code") != 200:
                    raise Exception(f"WaveSpeed API错误: {result}")

                data = result["data"]

                return {
                    "status": data.get("status"),  # created, processing, completed, failed
                    "video_url": data.get("outputs", [])[0] if data.get("outputs") else None,
                    "error": data.get("error")
                }
            except httpx.ReadTimeout:
                # 返回 processing 状态，让调用方继续轮询
                return {"status": "processing", "video_url": None, "error": None}
            except httpx.HTTPStatusError as e:
                raise Exception(f"HTTP错误: {e.response.status_code} - {e.response.text[:200]}")
            except Exception as e:
                raise Exception(f"获取任务结果失败: {str(e) or type(e).__name__}")

    async def wait_for_completion(
        self,
        task_id: str,
        max_wait_seconds: int = 600
    ) -> str:
        """
        等待视频生成完成

        Args:
            task_id: 任务ID
            max_wait_seconds: 最大等待时间

        Returns:
            视频URL

        Raises:
            Exception: 生成失败或超时
        """
        poll_count = 0
        max_polls = max_wait_seconds // 5

        for i in range(max_polls):
            poll_count = i + 1
            try:
                result = await self.get_task_result(task_id)

                if result["status"] == "completed":
                    if not result["video_url"]:
                        raise Exception("视频生成完成但未返回URL")
                    return result["video_url"]
                elif result["status"] == "failed":
                    error_msg = result.get("error") or "未知错误"
                    raise Exception(f"视频生成失败: {error_msg}")
                # status is processing, continue polling

            except Exception as e:
                # 如果是我们自己抛出的异常，直接传递
                if "视频生成" in str(e) or "WaveSpeed" in str(e):
                    raise
                # 其他异常（如网络超时），记录但继续轮询
                self.logger.warning(f"WaveSpeed 轮询异常 (第{poll_count}次): {e}")

            await asyncio.sleep(5)

        raise TimeoutError(f"视频生成超时 (已轮询 {poll_count} 次，共 {max_wait_seconds} 秒)")
