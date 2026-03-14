"""
Celery配置
"""
from celery import Celery
from app.config import settings

# 注册所有集成客户端（在 Celery worker 启动时执行）
from app.integrations.client_factory import register_all_clients
register_all_clients()

celery_app = Celery(
    "tiktokgen",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.video_generation"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.CELERY_TASK_TIMEOUT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIMEOUT,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50
)
