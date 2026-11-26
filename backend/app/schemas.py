import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class RegisterRequest(ApiModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=80)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", value):
            raise ValueError("用户名只能包含字母、数字和下划线")
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("密码必须至少包含一个字母和一个数字")
        return value


class LoginRequest(ApiModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.lower()


class UserResponse(ApiModel):
    id: int
    username: str
    display_name: str
    role: str


class CurrentUserResponse(UserResponse):
    certificate_status: str = "notConfigured"


class MessageResponse(ApiModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    created_at: datetime
    signature_status: str = "unverified"

    @field_validator("created_at")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class MessagePage(ApiModel):
    items: list[MessageResponse]
    page: int
    page_size: int
    total: int


class ApiError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ApiError


def success(data: Any) -> dict[str, Any]:
    if isinstance(data, BaseModel):
        data = data.model_dump(by_alias=True, mode="json")
    elif isinstance(data, list):
        data = [
            item.model_dump(by_alias=True, mode="json") if isinstance(item, BaseModel) else item
            for item in data
        ]
    return {"success": True, "data": data}
