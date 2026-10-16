from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginIn, SignupIn, TokenResponse, UserOut
from app.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        token_type="bearer",
        user=UserOut(id=user.id, email=user.email),
    )


@router.post("/signup", response_model=TokenResponse)
def signup(body: SignupIn, db: Session = Depends(get_db)) -> TokenResponse:
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email")
    existing = db.query(User).filter(User.email == email).one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token(user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenResponse:
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return _token(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email)
