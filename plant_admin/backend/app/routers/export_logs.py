import pymysql
from fastapi import APIRouter, Depends, Query

from app.auth_utils import get_current_user
from app.database import get_db
from app.models import PlantAdminUser
from app.schemas import ExportLogListOut, ExportLogOut

router = APIRouter(prefix="/export-logs", tags=["export-logs"])


@router.get("", response_model=ExportLogListOut)
def list_export_logs(
    conn: pymysql.connections.Connection = Depends(get_db),
    _: PlantAdminUser = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM plant_export_logs")
        total = int((cur.fetchone() or {"c": 0})["c"])
    offset = (page - 1) * page_size
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.id, e.plant_id, e.plant_name, e.user_id, e.username,
                   u.role AS user_role, e.export_format, e.created_at
            FROM plant_export_logs e
            LEFT JOIN plant_admin_users u ON u.id = e.user_id
            ORDER BY e.id DESC
            LIMIT %s OFFSET %s
            """,
            (page_size, offset),
        )
        rows = cur.fetchall()
    return ExportLogListOut(
        items=[ExportLogOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
