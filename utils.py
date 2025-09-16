from passlib.context import CryptContext
from dotenv import load_dotenv
import os
from datetime import timedelta, datetime, timezone
from jose import jwt, JWTError
import uuid
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db, User, RefreshToken
from database import PostAnalytics

# PASSWORD HASHING

pwd_context = CryptContext(schemes=['bcrypt'])

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# JWT ACCESS/REFRESH TOKEN GENERATION

load_dotenv()

JWT_ACCESS_SECRET = os.getenv('JWT_ACCESS_SECRET')
JWT_REFRESH_SECRET = os.getenv('JWT_REFRESH_SECRET')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM')

def generate_access_token(data: dict, expiry_delta: timedelta):
    payload = data.copy()
    expiry = datetime.now(timezone.utc) + (expiry_delta or timedelta(minutes=15))
    payload.update({"exp": expiry, "type": "access"})
    return jwt.encode(payload, JWT_ACCESS_SECRET, algorithm=JWT_ALGORITHM)

def generate_refresh_token(data: dict, expiry_delta: timedelta):
    jti = str(uuid.uuid4())
    payload = data.copy()
    expiry = datetime.now(timezone.utc) + (expiry_delta or timedelta(days=7))
    payload.update({"exp": expiry, "jti": jti, "type": "refresh"})
    return jwt.encode(payload, JWT_REFRESH_SECRET, algorithm=JWT_ALGORITHM), jti

# JWT ACCESS/REFRESH FUNCTIONS

security = HTTPBearer()

def get_current_user(access_token: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):

    try:
        payload = jwt.decode(access_token.credentials, JWT_ACCESS_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="sub claim missing from token")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User data missing")
        
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Authorization failed")
    
def refresh_access_token(refresh_token_str: str, db: Session):

    try:
        payload = jwt.decode(refresh_token_str, JWT_REFRESH_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=401, detail="jti claim missing from token")
        
        stored_token = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
        if not stored_token or not stored_token.is_active:
            raise HTTPException(status_code=401, detail="Invalid or missing refresh token")
        
        email = payload.get("sub") # email from payload
        if not email:
            raise HTTPException(status_code=401, detail="sub claim missing from token")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User data missing")
        
        new_access_token = generate_access_token({"sub": user.email}) # email from db
        return new_access_token
    except JWTError:
        raise HTTPException(status_code=401, detail="Token refresh failed")
    
# LOGOUT FUNCTION (invalidates refresh token)

def deactivate_refresh_token(refresh_token_str: str, db: Session):

    try:
        payload = jwt.decode(refresh_token_str, JWT_REFRESH_SECRET, algorithms=[JWT_ALGORITHM])
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=400, detail="jti claim missing in token")

        stored_token = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
        if not stored_token or not stored_token.is_active:
            raise HTTPException(status_code=400, detail="Refresh token already invalidated")

        stored_token.is_active = False
        db.commit()
        return True
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
# ANALYTICS GENERATION FUNCTION

def create_post_analytics(post_id: str, db: Session):

    try:
        post_uuid = uuid.UUID(post_id)
        analytics = PostAnalytics(post_id=post_uuid)
        db.add(analytics)
        db.commit()
        db.refresh(analytics)
        return analytics
    except Exception as e:
        db.rollback()
        raise e
