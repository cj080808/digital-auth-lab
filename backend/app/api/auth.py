from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, UserResponse, success
from app.security import (
    ACCESS_TOKEN_MINUTES,
    COOKIE_NAME,
    COOKIE_SECURE,
    create_access_token,
    hash_password,
    verify_password,
)


router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or payload.username,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="USERNAME_EXISTS") from None
    db.refresh(user)
    return success(UserResponse.model_validate(user, from_attributes=True))


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="INVALID_PASSWORD")

    response.set_cookie(
        key=COOKIE_NAME,
        value=create_access_token(user.id),
        max_age=ACCESS_TOKEN_MINUTES * 60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return success({"user": UserResponse.model_validate(user, from_attributes=True)})


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    data = {
        "id": user.id,
        "username": user.username,
        "displayName": user.display_name,
        "role": user.role,
        "certificateStatus": "notConfigured",
    }
    return success(data)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )
    return success({})
