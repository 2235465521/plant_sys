import pymysql
from fastapi import APIRouter, Depends, HTTPException

from app.auth_utils import create_access_token, get_current_user, hash_password, verify_password
from app.config import get_settings
from app.database import get_db
from app.models import PlantAdminUser
from app.schemas import LoginRequest, RegisterRequest, RegisterStatus, TokenResponse, UserBrief

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/register-status", response_model=RegisterStatus)
def register_status():
    s = get_settings()
    return RegisterStatus(enabled=s.register_enabled, allow_admin=s.register_allow_admin)


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, conn: pymysql.connections.Connection = Depends(get_db)):
    s = get_settings()
    if not s.register_enabled:
        raise HTTPException(403, "注册功能已关闭")
    if body.role == "admin" and not s.register_allow_admin:
        raise HTTPException(403, "当前不允许自助注册管理员，请选择普通用户或由管理员建号")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM plant_admin_users WHERE username = %s",
            (body.username,),
        )
        if cur.fetchone():
            raise HTTPException(409, "该用户名已被占用")
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO plant_admin_users (username, password_hash, role) VALUES (%s, %s, %s)",
            (body.username, hash_password(body.password), body.role),
        )
        new_id = cur.lastrowid
    conn.commit()
    token = create_access_token(new_id, body.username, body.role)
    return TokenResponse(access_token=token, role=body.role, username=body.username)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, conn: pymysql.connections.Connection = Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, username, password_hash, role, is_active FROM plant_admin_users WHERE username = %s",
            (body.username,),
        )
        row = cur.fetchone()
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")
    if not row["is_active"]:
        raise HTTPException(403, "账号已停用")
    token = create_access_token(int(row["id"]), row["username"], str(row["role"]))
    return TokenResponse(
        access_token=token,
        role=row["role"],
        username=row["username"],
    )


@router.get("/me", response_model=UserBrief)
def me(user: PlantAdminUser = Depends(get_current_user)):
    return UserBrief(id=user.id, username=user.username, role=user.role)


@router.get("/users", response_model=list[UserBrief])
def list_users(conn: pymysql.connections.Connection = Depends(get_db), current_user: PlantAdminUser = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(403, "仅管理员可查看用户列表")
    with conn.cursor() as cur:
        cur.execute("SELECT id, username, role FROM plant_admin_users WHERE is_active = 1 ORDER BY id DESC")
        rows = cur.fetchall()
    return [UserBrief(**r) for r in rows]


from app.schemas import UserRoleUpdate

@router.put("/users/{user_id}/role")
def update_user_role(user_id: int, body: UserRoleUpdate, conn: pymysql.connections.Connection = Depends(get_db), current_user: PlantAdminUser = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(403, "仅管理员可修改用户权限")
    if user_id == current_user.id:
        raise HTTPException(400, "不能修改自己的权限")
    with conn.cursor() as cur:
        cur.execute("UPDATE plant_admin_users SET role = %s WHERE id = %s", (body.role, user_id))
    conn.commit()
    return {"status": "ok"}
