from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user_repo import UserRepository

security_scheme = HTTPBearer(auto_error=False)


def _user_from_token(raw_token: str, db: Session) -> User:
    user_id = decode_access_token(raw_token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或令牌无效")
    user = UserRepository(db).get_by_id(int(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    token: str | None = Query(None, description="SSE 等无法携带 Authorization 时的令牌"),
    db: Session = Depends(get_db),
) -> User:
    raw_token: str | None = None
    if credentials is not None and credentials.credentials:
        raw_token = credentials.credentials
    elif token:
        raw_token = token
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或令牌无效")
    return _user_from_token(raw_token, db)
