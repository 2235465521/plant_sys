from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import bcrypt
import pymysql
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings
from app.database import get_db
from app.models import PlantAdminUser

bearer = HTTPBearer(auto_error=False)
settings = get_settings()


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int, username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def _row_to_user(row: dict) -> PlantAdminUser:
    return PlantAdminUser(
        id=int(row["id"]),
        username=row["username"],
        password_hash=row["password_hash"],
        role=str(row["role"]),
        is_active=bool(row["is_active"]),
    )


def get_current_user(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer)],
    conn: pymysql.connections.Connection = Depends(get_db),
) -> PlantAdminUser:
    if creds is None or not creds.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录或 token 无效")
    try:
        data = decode_token(creds.credentials)
        uid = int(data["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token 无效或已过期")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, username, password_hash, role, is_active FROM plant_admin_users WHERE id = %s",
            (uid,),
        )
        row = cur.fetchone()
    if row is None or not row.get("is_active"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在或已停用")
    return _row_to_user(row)


def require_admin(user: Annotated[PlantAdminUser, Depends(get_current_user)]) -> PlantAdminUser:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")
    return user
