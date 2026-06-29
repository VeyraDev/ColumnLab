from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repo import UserRepository
from app.schemas.common import LoginResponse, UserOut


class AuthService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def register(self, username: str, email: str, password: str) -> LoginResponse:
        if self.repo.get_by_username(username):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
        if self.repo.get_by_email(email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被注册")
        user = self.repo.create(username, email, hash_password(password))
        token = create_access_token(str(user.id))
        return LoginResponse(
            access_token=token,
            user_id=user.id,
            username=user.username,
        )

    def login(self, username: str, password: str) -> LoginResponse:
        user = self.repo.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码不正确")
        token = create_access_token(str(user.id))
        return LoginResponse(
            access_token=token,
            user_id=user.id,
            username=user.username,
        )

    def get_profile(self, user_id: int) -> UserOut:
        user = self.repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        return UserOut.model_validate(user)
