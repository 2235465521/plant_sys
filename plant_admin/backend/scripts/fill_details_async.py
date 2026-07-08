#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
植物生长环境与入药部位自动补全脚本 (DeepSeek API 高并发异步协程版)
"""

import os
import sys
import re
import asyncio
import argparse
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import pymysql
except ImportError:
    print("错误: 未找到 pymysql 库，请先安装: pip install pymysql")
    sys.exit(1)

try:
    import httpx
except ImportError:
    print("错误: 未找到 httpx 库，请先安装: pip install httpx")
    sys.exit(1)

# API 密钥与端点配置
API_KEY = "sk-2a32fdc69e89434eafe99a88999380a2"
API_URL = "https://api.deepseek.com/v1/chat/completions"

# 加载 .env 配置文件
def load_env():
    script_dir = Path(__file__).resolve().parent
    env_path = script_dir.parent / '.env'
    if not env_path.exists():
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

# AI 数据请求协程
async def fetch_ai_enrichment_async(
    client: httpx.AsyncClient,
    name: str,
    sci_name: str,
    morph: str,
    med: str,
    harvest: str,
    food: str,
    hab: str,
    semaphore: asyncio.Semaphore
) -> Optional[Dict[str, Any]]:
    prompt = f"""你是一个专业的中草药与植物学专家。
请分析以下植物的特征信息，提取并规范其【生长环境】（habitat）与【入药部位】（medicinal_part）。
植物信息如下：
- 中文名称: {name}
- 拉丁名: {sci_name}
- 形态描述: {morph}
- 药用性状/形状: {med}
- 采收说明: {harvest}
- 食疗说明: {food}
- 现有生境记录: {hab}

任务要求：
1. 生长环境 (habitat)：结合其形态描述、分布地区以及已有的生境记录（若有），生成一段规范、简洁的生长环境描述（如“生于海拔1000-2500米的山坡、林下、灌丛中或草地”）。字数在 50 字以内，力求准确规范。若已有生境记录已足够规范，可直接沿用或微调。
2. 入药部位 (medicinal_part)：结合其药用性状、采收说明与食疗说明，提炼出该植物最常用的中草药入药部位。要求字数极少、简洁明了（如“全草”、“根”、“根茎”、“叶”、“花”、“果实”、“种子”、“皮”、“皮部”、“藤茎”等，若有多个部位入药，用逗号隔开，如“叶，果实”）。通常不要超过 10 个字。如果完全无法判断，请返回 null。

请严格以下方的 JSON 格式返回，不要有任何 Markdown 代码块外的文字，也不要包含任何多余信息：
{{
    "habitat": "生于海拔...",
    "medicinal_part": "全草"
}}"""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that outputs only JSON objects."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }

    async with semaphore:
        for attempt in range(3):
            try:
                resp = await client.post(API_URL, json=payload, timeout=30.0)
                if resp.status_code == 200:
                    resp_data = resp.json()
                    content_str = resp_data["choices"][0]["message"]["content"]
                    return json.loads(content_str)
                elif resp.status_code == 429:
                    # 频率限制，指数避退
                    wait_time = 2 * (attempt + 1)
                    await asyncio.sleep(wait_time)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                await asyncio.sleep(1)
                
    return None

# DB 更新队列消费者
async def db_writer_worker(queue: asyncio.Queue, shutdown_event: asyncio.Event):
    # 强制 utf-8 编码输出
    sys.stdout.reconfigure(encoding='utf-8')
    
    conn = get_db_connection()
    success_count = 0
    fail_count = 0
    try:
        while not (shutdown_event.is_set() and queue.empty()):
            try:
                # 设置超时，方便检查 shutdown_event
                item = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
                
            plant_id, habitat, medicinal_part = item
            try:
                def update_row():
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE plant_classification_import SET habitat = %s, medicinal_part = %s WHERE id = %s",
                            (habitat, medicinal_part, plant_id)
                        )
                    conn.commit()
                
                await asyncio.to_thread(update_row)
                success_count += 1
            except Exception as ex:
                fail_count += 1
                print(f"数据库更新失败 (ID: {plant_id}): {ex}", file=sys.stderr)
            finally:
                queue.task_done()
    finally:
        conn.close()
        print(f"\n[DB Writer] 退出。成功提交: {success_count} 条，失败: {fail_count} 条。")

async def main_async():
    # 命令行解析
    parser = argparse.ArgumentParser(description="AI Plant Details Enrichment Async Script")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of plants to process")
    parser.add_argument("--min-id", type=int, default=None, help="Start processing from this plant ID")
    parser.add_argument("--concurrency", type=int, default=30, help="Concurrency limit for API calls")
    args = parser.parse_args()

    # 强制 utf-8 编码输出
    sys.stdout.reconfigure(encoding='utf-8')

    load_env()
    conn = get_db_connection()
    print("连接数据库成功！")

    # 查询待处理记录 (medicinal_part 为空)
    query = """
        SELECT id, vernacular_name, scientific_name, morphology_text, medicinal_shape, habitat, harvest_months_desc, food_therapy_months_desc
        FROM plant_classification_import
        WHERE medicinal_part IS NULL OR medicinal_part = ''
    """
    if args.min_id is not None:
        query += f" AND id >= {args.min_id}"
    query += " ORDER BY id ASC"
    if args.limit is not None:
        query += f" LIMIT {args.limit}"

    with conn.cursor() as cur:
        cur.execute(query)
        plants = cur.fetchall()
    conn.close()

    total_to_process = len(plants)
    print(f"发现待补全数据标本数: {total_to_process} 条")
    if total_to_process == 0:
        print("所有标本的入药部位数据已补全，无需运行此脚本。")
        return

    # 初始化异步相关组件
    semaphore = asyncio.Semaphore(args.concurrency)
    db_queue = asyncio.Queue(maxsize=200)
    shutdown_event = asyncio.Event()

    # 启动 DB 写入消费者
    db_worker_task = asyncio.create_task(db_writer_worker(db_queue, shutdown_event))

    limits = httpx.Limits(max_keepalive_connections=args.concurrency, max_connections=args.concurrency * 2)
    # 使用 acheck_auth_tokens 或自定义 authorization 头
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    success_count = 0
    fail_count = 0
    start_time = time.time()

    async with httpx.AsyncClient(limits=limits, headers=headers) as client:
        tasks = []
        
        async def process_plant(p):
            nonlocal success_count, fail_count
            plant_id = p["id"]
            name = p.get("vernacular_name") or ""
            sci_name = p.get("scientific_name") or ""
            morph = p.get("morphology_text") or ""
            med = p.get("medicinal_shape") or ""
            harvest = p.get("harvest_months_desc") or ""
            food = p.get("food_therapy_months_desc") or ""
            hab = p.get("habitat") or ""

            try:
                res = await fetch_ai_enrichment_async(
                    client=client,
                    name=name,
                    sci_name=sci_name,
                    morph=morph,
                    med=med,
                    harvest=harvest,
                    food=food,
                    hab=hab,
                    semaphore=semaphore
                )
                if res and ("medicinal_part" in res or "habitat" in res):
                    # 获取解析出来的内容
                    ai_habitat = res.get("habitat") or hab
                    ai_med_part = res.get("medicinal_part") or ""
                    
                    # 放入 DB 写入队列
                    await db_queue.put((plant_id, ai_habitat, ai_med_part))
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1

        print(f"\n开始使用方案 A 异步协程（并发限制：{args.concurrency}）处理，按 Ctrl+C 可随时安全退出...")
        
        # 批量并发运行
        for p in plants:
            tasks.append(asyncio.create_task(process_plant(p)))

        # 进度监控任务
        async def progress_monitor():
            last_processed = 0
            while not shutdown_event.is_set():
                await asyncio.sleep(5)
                processed = success_count + fail_count
                if processed == 0:
                    continue
                elapsed = time.time() - start_time
                speed = processed / elapsed
                percent = (processed / total_to_process) * 100
                est_rem_seconds = (total_to_process - processed) / speed if speed > 0 else 0
                est_rem_min = est_rem_seconds / 60
                print(f"[进度] 已处理: {processed}/{total_to_process} ({percent:.2f}%) | "
                      f"成功: {success_count} | 失败: {fail_count} | "
                      f"速度: {speed:.1f} 条/秒 | 预计剩余时间: {est_rem_min:.1f} 分钟")
                if processed >= total_to_process:
                    break

        monitor_task = asyncio.create_task(progress_monitor())

        try:
            # 等待所有 API 请求处理任务完成
            await asyncio.gather(*tasks, return_exceptions=True)
        except KeyboardInterrupt:
            print("\n[警告] 捕获到 Ctrl+C 中断信号，正在优雅关闭中...")
        finally:
            # 标记 API 处理完毕，通知 DB worker 退出
            shutdown_event.set()
            monitor_task.cancel()
            
            # 等待队列中的写入操作完成
            print("正在等待队列中的数据库更新写入完毕...")
            await db_queue.join()
            await db_worker_task

    total_elapsed = time.time() - start_time
    print(f"\n===== 批量处理完成 =====")
    print(f"总耗时: {total_elapsed:.1f} 秒 ({total_elapsed/60:.1f} 分钟)")
    print(f"成功填充: {success_count} 条")
    print(f"处理失败: {fail_count} 条")

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n脚本已被手动中断。")
