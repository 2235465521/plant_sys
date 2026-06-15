import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_mysql
from app.plant_image_fetch import resolve_remote_image_url, download_image_bytes

def main():
    print("正在连接 MySQL 数据库...")
    conn = connect_mysql()
    try:
        with conn.cursor() as cur:
            print("正在扫描包含网络图片链接的植物记录...")
            cur.execute(
                "SELECT id, vernacular_name, image_url, image_server_paths "
                "FROM plant_classification_import "
                "WHERE image_url IS NOT NULL AND TRIM(image_url) <> ''"
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    total = len(rows)
    print(f"共扫描到 {total} 条包含网络图片链接的植物记录。")
    if total == 0:
        return

    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        "data", 
        "plant_images"
    )
    os.makedirs(data_dir, exist_ok=True)

    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, r in enumerate(rows):
        plant_id = int(r["id"])
        name = r.get("vernacular_name") or "未命名"
        img_url_raw = r["image_url"].strip()

        plant_dir = os.path.join(data_dir, str(plant_id))
        
        # 如果本地对应的图片目录已存在且有文件，说明图片在，直接跳过
        if os.path.exists(plant_dir) and os.listdir(plant_dir):
            skip_count += 1
            continue

        print(f"[{i+1}/{total}] 正在为 ID {plant_id} ({name}) 自动重新下载图片...")
        try:
            # 解析网络图片链接为直链
            img_url, reason = resolve_remote_image_url(img_url_raw)
            if not img_url:
                print(f"  [跳过] 无法解析网络链接: {reason}")
                fail_count += 1
                continue

            img_bytes = download_image_bytes(img_url)

            # 判断文件后缀名
            ext = ".jpg"
            if ".png" in img_url.lower():
                ext = ".png"
            elif ".webp" in img_url.lower():
                ext = ".webp"

            filename = f"i_{plant_id}_recovered{ext}"
            os.makedirs(plant_dir, exist_ok=True)
            filepath = os.path.join(plant_dir, filename)

            # 写入本地文件
            with open(filepath, "wb") as f:
                f.write(img_bytes)

            local_path = f"/api/media/plants/{plant_id}/{filename}"

            # 更新数据库路径
            conn = connect_mysql()
            try:
                with conn.cursor() as cur:
                    paths_str = json.dumps([local_path], ensure_ascii=False)
                    cur.execute(
                        "UPDATE plant_classification_import SET image_server_paths = %s WHERE id = %s",
                        (paths_str, plant_id)
                    )
                conn.commit()
            finally:
                conn.close()

            print(f"  [成功] 已恢复并保存到: {local_path}")
            success_count += 1

        except Exception as e:
            print(f"  [失败] 恢复出错: {str(e)}")
            fail_count += 1

    print(f"\n恢复任务结束！成功重新下载: {success_count}，无需恢复(已存在): {skip_count}，失败/跳过: {fail_count}")

if __name__ == "__main__":
    main()
