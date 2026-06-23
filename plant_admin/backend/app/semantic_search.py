import os
import urllib.request
import json
from fastapi import HTTPException

def fetch_search_intent(query: str) -> dict:
    prompt = f"""你是一个专业的中草药与植物学检索专家。用户输入了一个植物搜索查询词："{query}"。
请帮我分析该查询词所表达的语义，并提取为供数据库筛选的 JSON 参数。支持提取以下维度的筛选条件：
1. harvest_months: 数组。如果用户寻找特定季节或月份的植物（如"夏天" -> [6,7,8]；"秋天" -> [9,10,11]；"春天" -> [3,4,5]；"冬天" -> [12,1,2]；或者明确提到某个月如"五月" -> [5]），请将匹配的所有月份数字存入该数组，否则返回空数组 []。
2. food_therapy_months: 数组。如果寻找特定季节或月份的食疗植物，处理逻辑同上。
3. habitats: 字符串数组。如果提到特定生境或生存场景（从 "森林", "草原", "湿地", "荒漠", "海洋" 中选择，或者提到其他特殊生境如 "高山雪线", "农田", "山坡荒地" ），请列出匹配的分类名称，否则返回空数组 []。
4. rankings: 字符串数组。如果提到排行榜相关的荣誉特征（如 "最甜"、"最苦"、"珍稀濒危"、"花期长"等），匹配分类可以是: "sweetest", "bitterest", "rarity", "growth_cycle" 之一，否则返回空数组 []。
5. regions: 字符串数组。如果是寻找特定产区、省份或道地组合（如 "浙江", "河南", "四川", "广药", "浙八味" 等），请列出匹配的名称，否则返回空数组 []。
6. keywords: 字符串数组。提取 1-3 个可用于模糊匹配植物名称、描述或药用性状的关键检索词（如搜索"消暑治感冒的药材"，关键词可以是 ["消暑", "感冒", "治感冒"]），如果查询词只有植物名称本身，可以直接提取为植物名称。若无可提取，请返回空数组 []。

请严格以下方的 JSON 格式返回，不要有任何 Markdown 代码块外的文字，也不要包含任何多余信息：
{{
    "harvest_months": [],
    "food_therapy_months": [],
    "habitats": [],
    "rankings": [],
    "regions": [],
    "keywords": []
}}"""

    api_key = "sk-2a32fdc69e89434eafe99a88999380a2"
    payload = {
        "model": "deepseek-v4-flash",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that outputs only JSON objects."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }

    try:
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            resp_bytes = response.read()
            resp_data = json.loads(resp_bytes.decode("utf-8"))
            content_str = resp_data["choices"][0]["message"]["content"]
            result = json.loads(content_str)
            return result
    except Exception as e:
        print(f"LLM 意图解析失败: {e}")
        return {
            "harvest_months": [],
            "food_therapy_months": [],
            "habitats": [],
            "rankings": [],
            "regions": [],
            "keywords": [query]
        }

def query_semantic_similarity(query: str, allowed_ids: list[int] = None) -> list[tuple[int, float]]:
    """
    计算查询词与已有植物的语义相似度，并返回按相似度降序排列的 (plant_id, score) 列表。
    如果指定了 allowed_ids，则只计算并返回这些 ID 的相似度。
    """
    intent = fetch_search_intent(query)
    
    harvest_months = intent.get("harvest_months") or []
    food_therapy_months = intent.get("food_therapy_months") or []
    habitats = intent.get("habitats") or []
    rankings = intent.get("rankings") or []
    regions = intent.get("regions") or []
    keywords = intent.get("keywords") or []
    
    from app.database import connect_mysql
    conn = connect_mysql()
    try:
        # 1. 从关联子表中匹配 plant_ids
        habitat_pids = []
        if habitats:
            ph = ",".join(["%s"] * len(habitats))
            with conn.cursor() as cur:
                cur.execute(f"SELECT plant_id FROM plant_habitats WHERE habitat_type IN ({ph})", list(habitats))
                habitat_pids = [r["plant_id"] for r in cur.fetchall() or []]
                
        ranking_pids = []
        if rankings:
            ph = ",".join(["%s"] * len(rankings))
            with conn.cursor() as cur:
                cur.execute(f"SELECT plant_id FROM plant_rankings WHERE ranking_type IN ({ph})", list(rankings))
                ranking_pids = [r["plant_id"] for r in cur.fetchall() or []]
                
        region_pids = []
        if regions:
            conds = []
            reg_params = []
            for r in regions:
                conds.append("region_name LIKE %s OR combo_name LIKE %s")
                reg_params.extend([f"%{r}%", f"%{r}%"])
            sql_where = " OR ".join(conds)
            with conn.cursor() as cur:
                cur.execute(f"SELECT plant_id FROM plant_regions WHERE {sql_where}", reg_params)
                region_pids = [r["plant_id"] for r in cur.fetchall() or []]
                
        # 2. 构造主表候选集查询 WHERE 子句
        conds = []
        sql_params = []
        
        for kw in keywords:
            kw_like = f"%{kw}%"
            conds.append("(vernacular_name LIKE %s OR alternative_names_zh LIKE %s OR morphology_text LIKE %s OR medicinal_shape LIKE %s)")
            sql_params.extend([kw_like, kw_like, kw_like, kw_like])
            
        for m in harvest_months:
            conds.append("FIND_IN_SET(%s, harvest_months) > 0")
            sql_params.append(str(m))
            
        for m in food_therapy_months:
            conds.append("FIND_IN_SET(%s, food_therapy_months) > 0")
            sql_params.append(str(m))
            
        all_related_pids = set(habitat_pids + ranking_pids + region_pids)
        if all_related_pids:
            ph = ",".join(["%s"] * len(all_related_pids))
            conds.append(f"id IN ({ph})")
            sql_params.extend(list(all_related_pids))
            
        if not conds:
            kw_like = f"%{query}%"
            conds.append("(vernacular_name LIKE %s OR alternative_names_zh LIKE %s OR morphology_text LIKE %s OR medicinal_shape LIKE %s)")
            sql_params.extend([kw_like, kw_like, kw_like, kw_like])
            
        where_clause = " OR ".join(conds)
        
        # 3. 查询候选记录并进行打分
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT id, vernacular_name, alternative_names_zh, morphology_text, medicinal_shape, harvest_months, food_therapy_months "
                f"FROM plant_classification_import WHERE {where_clause}",
                sql_params
            )
            rows = cur.fetchall() or []
            
        scores = []
        for row in rows:
            pid = row["id"]
            score = 0.0
            
            for kw in keywords:
                kw_lower = kw.lower()
                vname = (row.get("vernacular_name") or "").lower()
                altname = (row.get("alternative_names_zh") or "").lower()
                morph = (row.get("morphology_text") or "").lower()
                med = (row.get("medicinal_shape") or "").lower()
                
                if kw_lower in vname:
                    score += 10.0
                if kw_lower in altname:
                    score += 5.0
                if kw_lower in morph:
                    score += 2.0
                if kw_lower in med:
                    score += 2.0
                    
            h_months = [m.strip() for m in (row.get("harvest_months") or "").split(",") if m.strip()]
            f_months = [m.strip() for m in (row.get("food_therapy_months") or "").split(",") if m.strip()]
            for m in harvest_months:
                if str(m) in h_months:
                    score += 3.0
            for m in food_therapy_months:
                if str(m) in f_months:
                    score += 3.0
                    
            if pid in habitat_pids:
                score += 4.0
            if pid in ranking_pids:
                score += 5.0
            if pid in region_pids:
                score += 4.0
                
            scores.append((pid, score))
            
        scores.sort(key=lambda x: x[1], reverse=True)
        
        if allowed_ids is not None:
            allowed_set = set(allowed_ids)
            scores = [x for x in scores if x[0] in allowed_set]
            
        return scores
        
    finally:
        conn.close()
