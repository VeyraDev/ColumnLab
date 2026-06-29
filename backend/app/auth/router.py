from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import LoginRequest, RegisterRequest, success

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    result = AuthService(db).register(body.username, body.email, body.password)
    return success(result.model_dump())


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    result = AuthService(db).login(body.username, body.password)
    return success(result.model_dump())


@router.get("/profile")
def profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = AuthService(db).get_profile(current_user.id)
    return success(result.model_dump())
