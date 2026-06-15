import os
import sys
import pickle

# 将项目根目录（backend）添加到 sys.path 以便导入 app 中的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_mysql

def main():
    print("正在连接 MySQL 数据库...")
    conn = connect_mysql()
    try:
        with conn.cursor() as cur:
            print("正在获取植物信息数据...")
            cur.execute(
                "SELECT id, vernacular_name, scientific_name, family, genus, morphology_text, habitat "
                "FROM plant_classification_import ORDER BY id ASC"
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    total = len(rows)
    print(f"共加载了 {total} 条植物数据。")
    if total == 0:
        print("未在数据库中找到植物记录。请确认数据表已导入。")
        return

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("\n[错误] 未检测到 sentence-transformers 库。")
        print("请在您的 Python 虚拟环境中运行以下命令安装所需依赖：")
        print("pip install sentence-transformers numpy")
        return

    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    print(f"正在加载轻量级多语言嵌入模型 '{model_name}'...")
    print("（首次运行会自动从 HuggingFace 缓存下载该模型，约为 110MB，请保持网络畅通）")
    model = SentenceTransformer(model_name)

    print("正在组装检索描述文本...")
    texts = []
    ids = []
    for r in rows:
        ids.append(int(r["id"]))
        parts = [
            r["vernacular_name"] or "",
            r["scientific_name"] or "",
            r["family"] or "",
            r["genus"] or "",
            r["morphology_text"] or "",
            r["habitat"] or "",
        ]
        text = " ".join(p.strip() for p in parts if p.strip())
        texts.append(text)

    print("正在进行向量编码计算（此步骤在 CPU 上可能耗时 1-5 分钟，支持 GPU 加速）...")
    # 开启归一化以支持直接通过点积（Dot Product）计算余弦相似度
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, "plant_embeddings.pkl")

    print(f"正在将编码数据保存到本地文件 {out_path}...")
    with open(out_path, "wb") as f:
        pickle.dump({
            "ids": ids,
            "embeddings": embeddings
        }, f)

    print("AI 检索向量数据成功生成！您可以将其随代码一同推送或在服务器上执行此脚本。")

if __name__ == "__main__":
    main()
