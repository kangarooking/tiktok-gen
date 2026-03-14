"""
自定义异常类
"""
from typing import Any, Optional, Dict
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse


class APIException(Exception):
    """
    基础API异常
    """
    def __init__(
        self,
        message: str,
        code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(message)


class ValidationError(APIException):
    """数据验证错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)


class NotFoundError(APIException):
    """资源未找到"""
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class UnauthorizedError(APIException):
    """未授权"""
    def __init__(self, message: str = "未授权访问"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(APIException):
    """权限不足"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class QuotaExceededError(APIException):
    """额度超限"""
    def __init__(self, message: str = "已达到使用限额"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class ConfigurationError(APIException):
    """配置错误"""
    def __init__(self, message: str = "API配置错误"):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExternalServiceError(APIException):
    """第三方服务错误"""
    def __init__(self, service: str, message: str = "第三方服务异常"):
        super().__init__(f"{service}: {message}", status.HTTP_502_BAD_GATEWAY)


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    API异常处理器
    """
    return JSONResponse(
        status_code=exc.code,
        content={
            "success": False,
            "message": exc.message,
            "data": None,
            "details": exc.details
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    HTTP异常处理器
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None
        }
    )
