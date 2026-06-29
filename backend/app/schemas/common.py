from typing import Any, Generic, TypeVar

from pydantic import BaseModel, EmailStr, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    msg: str = "ok"
    data: T | None = None


def success(data: Any = None, msg: str = "ok") -> dict[str, Any]:
    return {"code": 0, "msg": msg, "data": data}


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    user_id: int
    username: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str

    model_config = {"from_attributes": True}
