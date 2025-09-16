from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, User, UserRole, RefreshToken
from pydantic_models import UserRegister, UserLogin, RefreshTokenRequest
from utils import (
    hash_password, 
    get_current_user, 
    verify_password, 
    generate_access_token, 
    generate_refresh_token, 
    refresh_access_token, 
    deactivate_refresh_token
)

router = APIRouter()

@router.post('/signup')
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    already_exists = db.query(User).filter(User.email == user_data.email).first()
    if already_exists:
        raise HTTPException(status_code=400, detail="User already registered")
    
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=UserRole.USER
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"user_name": new_user.name, "detail": "User registered successfully"}

@router.post('/admin/signup')
def register_admin(
    signup_data: UserRegister, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admin can create another admin")
    
    already_exists = db.query(User).filter(User.email == signup_data.email).first()
    if already_exists:
        raise HTTPException(status_code=400, detail="Admin already registered")
    
    new_admin = User(
        name=signup_data.name,
        email=signup_data.email,
        password_hash=hash_password(signup_data.password),
        role=UserRole.ADMIN
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return {"admin_name": new_admin.name, "detail": "Admin registered successfully"}

@router.post('/login')
def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    stored_user = db.query(User).filter(User.email == credentials.email).first()
    if not stored_user or not verify_password(credentials.password, stored_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = generate_access_token({"sub": stored_user.email})
    refresh_token, jti = generate_refresh_token({"sub": stored_user.email})

    db_refresh_token = RefreshToken(jti=jti, user_id=stored_user.id)
    db.add(db_refresh_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post('/refresh')
def issue_new_token(token: RefreshTokenRequest, db: Session = Depends(get_db)):
    new_access_token = refresh_access_token(token.refresh_token, db)
    return {"access_token": new_access_token, "token_type": "bearer"}

@router.post('/logout')
def logout_user(token: RefreshTokenRequest, db: Session = Depends(get_db)):
    deactivate_refresh_token(token.refresh_token, db)
    return {"detail": "Logged out successfully"}