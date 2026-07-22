# -*- coding: utf-8 -*-
"""只读数据库访问服务，为视频生成模块提供数据支撑。"""
from __future__ import annotations

import json
from typing import Any, Optional
import pymysql

from app.database import connect_mysql


def _deserialize_paths(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        t = raw.strip()
        if not t:
            return []
        try:
            parsed = json.loads(t)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        return [str(x).strip() for x in parsed if x is not None and str(x).strip()]
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if x is not None and str(x).strip()]
    return []


def get_plant_data_for_video(plant_id: int) -> Optional[dict[str, Any]]:
    """查询视频生成所需的全部植物详情，确保只读且不影响业务代码。"""
    conn = connect_mysql()
    try:
        with conn.cursor() as cur:
            # 1. 查询基础信息
            cols = [
                "id", "division", "subclass", "taxonomic_order", "family", "genus",
                "vernacular_name", "alternative_names_zh", "scientific_name",
                "morphology_text", "medicinal_shape", "distribution_china",
                "distribution_abroad", "habitat", "medicinal_part",
                "is_medicinal_food_homologous", "image_url", "image_server_paths",
                "harvest_months_desc", "food_therapy_months_desc"
            ]
            sql = f"SELECT {', '.join(cols)} FROM plant_classification_import WHERE id = %s"
            cur.execute(sql, (plant_id,))
            row = cur.fetchone()
            if not row:
                return None
            
            # 解析图片路径
            row["image_server_paths"] = _deserialize_paths(row.get("image_server_paths"))
            
            # 2. 查询别名系统
            cur.execute(
                "SELECT alias_type, alias_name, origin_desc FROM plant_aliases WHERE plant_id = %s",
                (plant_id,)
            )
            aliases = []
            for al in cur.fetchall() or []:
                origin = f"({al['origin_desc']})" if al.get("origin_desc") else ""
                aliases.append(f"{al['alias_name']}{origin}")
            row["aliases_list"] = aliases

            # 3. 查询场景分类
            cur.execute(
                "SELECT habitat_type FROM plant_habitats WHERE plant_id = %s",
                (plant_id,)
            )
            row["habitats_list"] = [h["habitat_type"] for h in cur.fetchall() or []]

            # 4. 查询排行榜
            cur.execute(
                "SELECT ranking_type, ranking_value, description FROM plant_rankings WHERE plant_id = %s",
                (plant_id,)
            )
            rankings = []
            ranking_type_cn = {
                "sweetest": "最甜", "bitterest": "最苦", "rarity": "珍稀", "growth_cycle": "生长周期"
            }
            for r in cur.fetchall() or []:
                lbl = ranking_type_cn.get(r["ranking_type"], r["ranking_type"])
                val = f"[{lbl}] {r['description'] or ''}"
                rankings.append(val)
            row["rankings_list"] = rankings

            # 5. 查询道地药材省份
            cur.execute(
                "SELECT region_name, combo_name FROM plant_regions WHERE plant_id = %s",
                (plant_id,)
            )
            regions = []
            for reg in cur.fetchall() or []:
                combo = f"({reg['combo_name']})" if reg.get("combo_name") else ""
                regions.append(f"{reg['region_name']}{combo}")
            row["regions_list"] = regions

            return row
    finally:
        conn.close()
