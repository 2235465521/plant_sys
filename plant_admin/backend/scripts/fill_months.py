#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
植物最佳采收与食疗入药月份描述自动补全脚本 (DeepSeek API 批量处理)
"""

import os
import sys
import re
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

# 尝试引入 pymysql，如果没有则提示安装
try:
    import pymysql
except ImportError:
    print("错误: 未找到 pymysql 库，请先安装: pip install pymysql")
    sys.exit(1)

# API 密钥与端点配置
API_KEY = "sk-2a32fdc69e89434eafe99a88999380a2"
API_URL = "https://api.deepseek.com/v1/chat/completions"

# 加载 .env 配置文件
def load_env():
    # 查找 backend 目录下的 .env
    script_dir = Path(__file__).resolve().parent
    env_path = script_dir.parent / '.env'
    if not env_path.exists():
        # 尝试在当前目录或父目录查找
        env_path = Path('backend/.env')
        if not env_path.exists():
            env_path = Path('.env')
            
    if env_path.exists():
        print(f"正在加载配置文件: {env_path.resolve()}")
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()
    else:
        print("未找到 .env 配置文件，将使用默认连接参数")

def get_db_connection():
    db_url = os.getenv("DATABASE_URL", "")
    if db_url:
        match = re.search(r"mysql\+pymysql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/([^?]+)", db_url)
        if match:
            user, password, host, port, dbname = match.groups()
            port = int(port) if port else 3306
            # 移除 dbname 后可能存在的 query params
            dbname = dbname.split('?')[0]
            try:
                return pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=dbname,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor
                )
            except Exception as e:
                print(f"通过 DATABASE_URL 连接失败: {e}")
                
    # 默认备份连接
    print("尝试使用默认本地连接 (root:lsj223546@127.0.0.1:3306/plant_db)")
    return pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="lsj223546",
        database="plant_db",
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def fetch_ai_enrichment(name, sci_name, morph, med, hab):
    prompt = f"""你是一个专业的中草药与植物学专家。
根据以下提供的植物信息：
- 中文名称: {name}
- 拉丁名: {sci_name}
- 形态描述: {morph}
- 现有药用性状: {med}
- 生境: {hab}

请帮我深入分析该植物，并生成结构化数据：
1. 最佳采收月份：请列出最适合采收的月份数字，多个月份用逗号分隔，如 "5,6" 或仅一个数字如 "8"。如果没有明确文献，请根据其开花/结果期或通用药用部位（根、茎、叶、花、果）规律进行推断。
2. 最佳采收详细说明：请给出一段详细的中文说明，解释为什么选择这些月份（如开花期、植株成熟度、有效成分含量等），并附带采收和炮制建议（如阴干、烘干等），字数在 100-250 字左右。
3. 适合食疗入药月份：请列出适合作为食疗或药膳入药的月份数字，多个月份用逗号分隔，如 "6,7"。通常与最佳采收月接近或略晚，或为适宜物候调理的季节。
4. 食疗入药详细说明：请给出一段详细的说明，指出食疗或入药的注意事项、鲜品/干品的使用安全风险（如有无毒性、需如何处理如干燥煎煮）、经典古籍记载（如没有特定古籍，可指出同属药材通用逻辑）及服用建议，字数在 150-300 字左右。
5. 药用性状/药用形状说明：如果该植物现有的药用性状描述不完整或无记录，请结合其植物志与药材典籍，推断生成详细的药用形状、性味归经、功效主治说明，字数在 150-300 字左右。
6. 生境场景分类：从 "森林", "草原", "湿地", "荒漠", "海洋" 中选择最适合它的一个或多个分类，如果有其他特殊生境（如 "高山雪线", "农田", "山坡荒地" ），也可以直接生成新分类名称并加入列表中。以字符串数组返回。
7. 特色排行榜推荐：如果该植物具备某些极端或奇特特征（极甜、极苦、国家级珍稀濒危、或生长花期极其漫长/特殊），请为其推荐排行榜分类（ranking_type 必须是: "sweetest"、"bitterest"、"rarity"、"growth_cycle" 之一），并填写指标数值（如 "9.5分", "一级保护"）和详细理由。若均不符合，请返回空数组 []。
8. 道地药材产区关联：若该植物属于某省份的著名道地药材或经典药材名（如 浙江的“浙八味”、河南的“四大怀药”、四川的“川药”、广东的“广药”、吉林的“关药”、云南的“云药”等），请对应生成 region_name (省份) 和 combo_name (经典组合名)。如果不属于上述经典组合，但其在该省份为著名道地特产，可以只填写 region_name 并将 combo_name 设为 null。若均不符合，请返回空数组 []。
9. 分类别名及由来：推荐 1 到 3 个该植物在医药、文学或民间的别称，提供别称类型（必须是："药典标准名", "古书古名", "民间通用俗称", "各地方言名", "药房处方名", "市场商品名", "易混淆错用名" 之一），并详细解释该别名的由来背景或出处（origin_desc）。若无推荐，请返回空数组 []。

请严格以下方的 JSON 格式返回，不要有任何 Markdown 代码块外的文字，也不要包含任何多余信息：
{{
    "harvest_months": "5,6",
    "harvest_months_desc": "最佳采收说明文本...",
    "food_therapy_months": "6,7",
    "food_therapy_months_desc": "食疗入药说明文本...",
    "medicinal_shape": "详细生成的药用形状与功效归经...",
    "habitats": ["森林", "湿地"],
    "rankings": [
        {{
            "ranking_type": "sweetest",
            "ranking_value": "9.5分",
            "description": "含有特异性甜味素，比蔗糖甜数百倍，是著名的天然甜味植物..."
        }}
    ],
    "regions": [
        {{
            "region_name": "浙江",
            "combo_name": "浙八味"
        }}
    ],
    "aliases": [
        {{
            "alias_type": "古书古名",
            "alias_name": "仙草",
            "origin_desc": "在《神农本草经》中被称为仙草，因其具有清热利湿、凉血解毒之奇效..."
        }}
    ]
}}"""

    payload = {
        "model": "deepseek-v4-flash",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that outputs only JSON objects."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        },
        method="POST"
    )
    
    # 3次重试机制
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                resp_bytes = response.read()
                resp_data = json.loads(resp_bytes.decode("utf-8"))
                content_str = resp_data["choices"][0]["message"]["content"]
                return json.loads(content_str)
        except Exception as e:
            print(f"  [重试 {attempt + 1}/3] 请求失败: {e}")
            time.sleep(2 * (attempt + 1))
            
    raise Exception("多次尝试后依然调用失败")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="AI Plant Details Enrichment Script")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of plants to process")
    parser.add_argument("--offset", type=int, default=None, help="Database offset for query")
    args = parser.parse_args()

    load_env()
    conn = get_db_connection()
    print("数据库连接成功！")
    
    # 查询尚未补全时令描述的数据
    sql_query = """
        SELECT id, vernacular_name, scientific_name, morphology_text, medicinal_shape, habitat
        FROM plant_classification_import
        WHERE harvest_months_desc IS NULL OR harvest_months_desc = ''
        ORDER BY id ASC
    """
    if args.limit is not None:
        sql_query += f" LIMIT {args.limit}"
        if args.offset is not None:
            sql_query += f" OFFSET {args.offset}"
    elif args.offset is not None:
        sql_query += f" LIMIT 18446744073709551615 OFFSET {args.offset}"
        
    with conn.cursor() as cur:
        cur.execute(sql_query)
        plants = cur.fetchall()
        
    total_to_process = len(plants)
    print(f"发现待补全数据标本数: {total_to_process} 条")
    
    if total_to_process == 0:
        print("所有标本的采收说明和食疗说明已补全，无需运行此脚本。")
        conn.close()
        return

    success_count = 0
    fail_count = 0
    
    print("\n开始执行批量 AI 数据补全，输入 Ctrl+C 可以安全随时中止脚本...\n")
    
    try:
        for idx, p in enumerate(plants):
            plant_id = p["id"]
            name = p.get("vernacular_name") or ""
            sci_name = p.get("scientific_name") or ""
            
            display_name = name if name else (sci_name if sci_name else f"ID:{plant_id}")
            print(f"[{idx + 1}/{total_to_process}] 正在处理植物: {display_name} (ID: {plant_id}) ...")
            
            try:
                ai_data = fetch_ai_enrichment(
                    name=name,
                    sci_name=sci_name,
                    morph=p.get("morphology_text") or "",
                    med=p.get("medicinal_shape") or "",
                    hab=p.get("habitat") or ""
                )
                
                # 提取出来的数据
                harvest_months = ai_data.get("harvest_months")
                harvest_months_desc = ai_data.get("harvest_months_desc")
                food_therapy_months = ai_data.get("food_therapy_months")
                food_therapy_months_desc = ai_data.get("food_therapy_months_desc")
                medicinal_shape = ai_data.get("medicinal_shape")
                
                habitats = ai_data.get("habitats") or []
                rankings = ai_data.get("rankings") or []
                regions = ai_data.get("regions") or []
                aliases = ai_data.get("aliases") or []
                
                with conn.cursor() as cur:
                    # 1. 更新主表描述与药用形状
                    sql_update = """
                        UPDATE plant_classification_import
                        SET harvest_months = %s,
                            harvest_months_desc = %s,
                            food_therapy_months = %s,
                            food_therapy_months_desc = %s,
                            medicinal_shape = %s
                        WHERE id = %s
                    """
                    cur.execute(sql_update, (
                        harvest_months,
                        harvest_months_desc,
                        food_therapy_months,
                        food_therapy_months_desc,
                        medicinal_shape,
                        plant_id
                    ))
                    
                    # 2. 清除并重新插入生境
                    cur.execute("DELETE FROM plant_habitats WHERE plant_id = %s", (plant_id,))
                    for h in habitats:
                        cur.execute("INSERT INTO plant_habitats (plant_id, habitat_type) VALUES (%s, %s)", (plant_id, h))
                        
                    # 3. 清除并重新插入榜单
                    cur.execute("DELETE FROM plant_rankings WHERE plant_id = %s", (plant_id,))
                    for r in rankings:
                        cur.execute(
                            "INSERT INTO plant_rankings (plant_id, ranking_type, ranking_value, description) "
                            "VALUES (%s, %s, %s, %s)",
                            (plant_id, r.get("ranking_type"), r.get("ranking_value"), r.get("description"))
                        )
                        
                    # 4. 清除并重新插入道地药材地
                    cur.execute("DELETE FROM plant_regions WHERE plant_id = %s", (plant_id,))
                    for reg in regions:
                        cur.execute(
                            "INSERT INTO plant_regions (plant_id, region_name, combo_name) "
                            "VALUES (%s, %s, %s)",
                            (plant_id, reg.get("region_name"), reg.get("combo_name"))
                        )
                        
                    # 5. 清除并重新插入别称
                    cur.execute("DELETE FROM plant_aliases WHERE plant_id = %s", (plant_id,))
                    for al in aliases:
                        cur.execute(
                            "INSERT INTO plant_aliases (plant_id, alias_type, alias_name, origin_desc) "
                            "VALUES (%s, %s, %s, %s)",
                            (plant_id, al.get("alias_type"), al.get("alias_name"), al.get("origin_desc"))
                        )
                        
                conn.commit()
                success_count += 1
                print(f"  成功补全! 采收月: {harvest_months}, 食疗月: {food_therapy_months}, 别名数: {len(aliases)}")
                
            except Exception as ex:
                fail_count += 1
                print(f"  处理失败 (ID: {plant_id}): {ex}")
                
            time.sleep(0.8)
            
            if (idx + 1) % 10 == 0:
                percent = ((idx + 1) / total_to_process) * 100
                print(f"\n--- 阶段统计: 已完成 {percent:.2f}% | 成功: {success_count} | 失败: {fail_count} ---\n")
                
    except KeyboardInterrupt:
        print("\n脚本已被用户手动中断。已保存当前进度。")
        
    finally:
        conn.close()
        print(f"\n批量处理结束。共成功更新 {success_count} 条，失败 {fail_count} 条。")

if __name__ == "__main__":
    main()
