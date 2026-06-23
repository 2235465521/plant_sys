import pymysql
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.database import get_db
from app.auth_utils import get_current_user, require_admin
from app.models import PlantAdminUser
from app.schemas import (
    PlantConfusionGroupCreate,
    PlantConfusionGroupOut,
    PlantConfusionGroupUpdate,
    PlantOut
)

router = APIRouter(prefix="/features", tags=["features"])


def _get_plant_by_id(plant_id: int, conn: pymysql.connections.Connection) -> Optional[PlantOut]:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM plant_classification_import WHERE id = %s", (plant_id,))
        p = cur.fetchone()
    if not p:
        return None
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM plant_aliases WHERE plant_id = %s", (plant_id,))
        aliases = cur.fetchall() or []
        cur.execute("SELECT habitat_type FROM plant_habitats WHERE plant_id = %s", (plant_id,))
        habitats = [r["habitat_type"] for r in cur.fetchall() or []]
        cur.execute("SELECT * FROM plant_rankings WHERE plant_id = %s", (plant_id,))
        rankings = cur.fetchall() or []
        cur.execute("SELECT * FROM plant_regions WHERE plant_id = %s", (plant_id,))
        regions = cur.fetchall() or []
    
    from app.routers.plants import plant_row_to_out
    return plant_row_to_out(p, aliases=aliases, habitats=habitats, rankings=rankings, regions=regions)


# ==========================================
# 3. Habitats (场景分类)
# ==========================================

@router.get("/habitats/summary")
def get_habitats_summary(conn: pymysql.connections.Connection = Depends(get_db), _ = Depends(get_current_user)):
    # Standard 5 categories: 海洋, 湿地, 森林, 草原, 荒漠
    categories = ["海洋", "湿地", "森林", "草原", "荒漠"]
    counts = {cat: 0 for cat in categories}
    
    with conn.cursor() as cur:
        cur.execute("SELECT habitat_type, COUNT(*) as cnt FROM plant_habitats GROUP BY habitat_type")
        rows = cur.fetchall() or []
        for r in rows:
            htype = r["habitat_type"]
            counts[htype] = r["cnt"]
            
    # Include other types if they exist, but at least standard ones
    return [{"habitat_type": k, "count": v} for k, v in counts.items()]


@router.get("/habitats")
def list_habitat_plants(
    habitat_type: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    conn: pymysql.connections.Connection = Depends(get_db),
    _ = Depends(get_current_user),
):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) as total FROM plant_habitats h "
            "JOIN plant_classification_import p ON h.plant_id = p.id "
            "WHERE h.habitat_type = %s",
            (habitat_type,)
        )
        total = cur.fetchone()["total"]
        
        cur.execute(
            "SELECT h.plant_id FROM plant_habitats h "
            "JOIN plant_classification_import p ON h.plant_id = p.id "
            "WHERE h.habitat_type = %s "
            "LIMIT %s OFFSET %s",
            (habitat_type, page_size, (page - 1) * page_size)
        )
        plant_ids = [r["plant_id"] for r in cur.fetchall() or []]
        
    items = []
    for pid in plant_ids:
        p_out = _get_plant_by_id(pid, conn)
        if p_out:
            items.append(p_out)
            
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ==========================================
# 4. Rankings (特色排行榜)
# ==========================================

@router.get("/rankings/summary")
def get_rankings_summary(conn: pymysql.connections.Connection = Depends(get_db), _ = Depends(get_current_user)):
    with conn.cursor() as cur:
        cur.execute("SELECT ranking_type, COUNT(*) as cnt FROM plant_rankings GROUP BY ranking_type")
        rows = cur.fetchall() or []
    return [{"ranking_type": r["ranking_type"], "count": r["cnt"]} for r in rows]


@router.get("/rankings")
def list_ranking_plants(
    ranking_type: str,
    conn: pymysql.connections.Connection = Depends(get_db),
    _ = Depends(get_current_user),
):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT r.plant_id, r.ranking_value, r.description FROM plant_rankings r "
            "JOIN plant_classification_import p ON r.plant_id = p.id "
            "WHERE r.ranking_type = %s "
            "ORDER BY r.id ASC",
            (ranking_type,)
        )
        rows = cur.fetchall() or []
        
    items = []
    for r in rows:
        p_out = _get_plant_by_id(r["plant_id"], conn)
        if p_out:
            items.append({
                "plant": p_out,
                "ranking_value": r["ranking_value"],
                "description": r["description"]
            })
    return items


# ==========================================
# 5. Regional Daodi (道地药材)
# ==========================================

@router.get("/regions/summary")
def get_regions_summary(conn: pymysql.connections.Connection = Depends(get_db), _ = Depends(get_current_user)):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT region_name, combo_name, COUNT(*) as cnt "
            "FROM plant_regions GROUP BY region_name, combo_name"
        )
        rows = cur.fetchall() or []
    return [{"region_name": r["region_name"], "combo_name": r["combo_name"], "count": r["cnt"]} for r in rows]


@router.get("/regions")
def list_region_plants(
    region_name: Optional[str] = None,
    combo_name: Optional[str] = None,
    conn: pymysql.connections.Connection = Depends(get_db),
    _ = Depends(get_current_user),
):
    if not region_name and not combo_name:
        return []
        
    sql = "SELECT r.plant_id FROM plant_regions r JOIN plant_classification_import p ON r.plant_id = p.id WHERE "
    params = []
    if region_name and combo_name:
        sql += "r.region_name = %s AND r.combo_name = %s"
        params = [region_name, combo_name]
    elif region_name:
        sql += "r.region_name = %s"
        params = [region_name]
    else:
        sql += "r.combo_name = %s"
        params = [combo_name]
        
    with conn.cursor() as cur:
        cur.execute(sql, params)
        plant_ids = [r["plant_id"] for r in cur.fetchall() or []]
        
    items = []
    for pid in plant_ids:
        p_out = _get_plant_by_id(pid, conn)
        if p_out:
            items.append(p_out)
    return items


# ==========================================
# 6. Confusion Groups (易混淆专题)
# ==========================================

def get_confusion_group_detail(group_id: int, conn: pymysql.connections.Connection) -> PlantConfusionGroupOut:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM plant_confusion_groups WHERE id = %s", (group_id,))
        g = cur.fetchone()
    if not g:
        raise HTTPException(404, "分组不存在")
        
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM plant_confusion_items WHERE group_id = %s", (group_id,))
        items = cur.fetchall() or []
        
    resolved_items = []
    for item in items:
        p_out = _get_plant_by_id(item["plant_id"], conn)
        resolved_items.append({
            "id": item["id"],
            "group_id": item["group_id"],
            "plant_id": item["plant_id"],
            "distinguish_point": item["distinguish_point"],
            "plant": p_out
        })
        
    return PlantConfusionGroupOut(
        id=g["id"],
        group_name=g["group_name"],
        description=g["description"],
        items=resolved_items
    )


@router.get("/confusion-groups", response_model=list[PlantConfusionGroupOut])
def list_confusion_groups(
    conn: pymysql.connections.Connection = Depends(get_db),
    _ = Depends(get_current_user),
):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM plant_confusion_groups ORDER BY id DESC")
        groups = cur.fetchall() or []
    out = []
    for g in groups:
        out.append(get_confusion_group_detail(g["id"], conn))
    return out


@router.get("/confusion-groups/{id}", response_model=PlantConfusionGroupOut)
def get_confusion_group(
    id: int,
    conn: pymysql.connections.Connection = Depends(get_db),
    _ = Depends(get_current_user),
):
    return get_confusion_group_detail(id, conn)


@router.post("/confusion-groups", response_model=PlantConfusionGroupOut)
def create_confusion_group(
    body: PlantConfusionGroupCreate,
    conn: pymysql.connections.Connection = Depends(get_db),
    _ = Depends(require_admin),
):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO plant_confusion_groups (group_name, description) VALUES (%s, %s)",
            (body.group_name, body.description)
        )
        group_id = conn.insert_id()
        
        for item in body.items:
            cur.execute(
                "INSERT INTO plant_confusion_items (group_id, plant_id, distinguish_point) VALUES (%s, %s, %s)",
                (group_id, item.plant_id, item.distinguish_point)
            )
    conn.commit()
    return get_confusion_group_detail(group_id, conn)


@router.put("/confusion-groups/{id}", response_model=PlantConfusionGroupOut)
def update_confusion_group(
    id: int,
    body: PlantConfusionGroupUpdate,
    conn: pymysql.connections.Connection = Depends(get_db),
    _ = Depends(require_admin),
):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM plant_confusion_groups WHERE id = %s", (id,))
        if not cur.fetchone():
            raise HTTPException(404, "分组不存在")
            
        updates = []
        params = []
        if body.group_name is not None:
            updates.append("group_name = %s")
            params.append(body.group_name)
        if body.description is not None:
            updates.append("description = %s")
            params.append(body.description)
        if updates:
            params.append(id)
            cur.execute(f"UPDATE plant_confusion_groups SET {','.join(updates)} WHERE id = %s", params)
            
        if body.items is not None:
            cur.execute("DELETE FROM plant_confusion_items WHERE group_id = %s", (id,))
            for item in body.items:
                cur.execute(
                    "INSERT INTO plant_confusion_items (group_id, plant_id, distinguish_point) VALUES (%s, %s, %s)",
                    (id, item.plant_id, item.distinguish_point)
                )
    conn.commit()
    return get_confusion_group_detail(id, conn)


@router.delete("/confusion-groups/{id}")
def delete_confusion_group(
    id: int,
    conn: pymysql.connections.Connection = Depends(get_db),
    _ = Depends(require_admin),
):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM plant_confusion_groups WHERE id = %s", (id,))
        if not cur.fetchone():
            raise HTTPException(404, "分组不存在")
        cur.execute("DELETE FROM plant_confusion_items WHERE group_id = %s", (id,))
        cur.execute("DELETE FROM plant_confusion_groups WHERE id = %s", (id,))
    conn.commit()
    return {"status": "ok"}
