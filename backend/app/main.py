import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.database import Base, engine
from app.websocket.chat import router as websocket_router


logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Secure Chat API", version="1.0.0")


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    error_codes = {
        401: ("UNAUTHORIZED", "请先登录或重新登录"),
        403: ("FORBIDDEN", "无权访问该资源"),
        404: ("NOT_FOUND", "请求的资源不存在"),
        409: ("USERNAME_EXISTS", "用户名已被注册"),
    }
    code, message = error_codes.get(exc.status_code, ("INTERNAL_ERROR", "请求处理失败"))
    if isinstance(exc.detail, str):
        if exc.detail == "INVALID_PASSWORD":
            code = "UNAUTHORIZED"
            message = "用户名或密码错误"
        elif exc.detail in {"USERNAME_EXISTS", "UNAUTHORIZED", "FORBIDDEN", "NOT_FOUND"}:
            code = exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": code, "message": message}},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {"code": "VALIDATION_ERROR", "message": "请求参数格式错误"},
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logging.getLogger(__name__).exception("Unhandled request error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": "服务暂时不可用"},
        },
    )


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(websocket_router)
