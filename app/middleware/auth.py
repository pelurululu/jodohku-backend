"""
JODOHKU.MY — Authentication Middleware
JWT verification and user injection for route dependencies
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User, AccountStatus
from app.models.admin import AdminUser

settings = get_settings()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and verify JWT from Authorization header.
    Returns the authenticated User object.
    """
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        if not user_id or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token tidak sah.",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token telah tamat atau tidak sah.",
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pengguna tidak ditemui.",
        )
    
    if user.status == AccountStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akaun anda telah digantung.",
        )
    
    if user.status == AccountStatus.DELETED:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Akaun telah dipadamkan.",
        )
    
    return user


async def get_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """Verify admin JWT and return AdminUser."""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        admin_id = payload.get("sub")
        if not admin_id or payload.get("type") != "admin":
            raise HTTPException(status_code=403, detail="Akses ditolak.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token tidak sah.")
    
    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin = result.scalar_one_or_none()
    
    if not admin or not admin.is_active:
        raise HTTPException(status_code=403, detail="Akses ditolak.")
    
    return admin


async def get_ws_user(token: str, db: AsyncSession):
    """Authenticate WebSocket connections."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except JWTError:
        return None


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Optional auth — returns None if no valid token."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    
    try:
        token = auth.replace("Bearer ", "")
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except (JWTError, Exception):
        return None
