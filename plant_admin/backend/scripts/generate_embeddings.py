import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
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
                "SELECT id, vernacular_name, alternative_names_zh, scientific_name, synonyms, "
                "family, genus, morphology_text, medicinal_shape, habitat, distribution_china, distribution_abroad "
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
    local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "models", "paraphrase-multilingual-MiniLM-L12-v2")
    if os.path.exists(local_path):
        model_name = local_path
        print(f"检测到本地已存在模型，正在从本地路径 '{model_name}' 加载...")
    else:
        print(f"正在从 HuggingFace 镜像站加载模型 '{model_name}'...")
        print("（首次运行会自动从镜像站缓存下载该模型，约为 110MB，请保持网络畅通）")
    model = SentenceTransformer(model_name)

    print("正在组装检索描述文本...")
    texts = []
    ids = []
    for r in rows:
        ids.append(int(r["id"]))
        parts = [
            f"中文名：{r['vernacular_name']}" if r["vernacular_name"] else "",
            f"别名：{r['alternative_names_zh']}" if r["alternative_names_zh"] else "",
            f"学名：{r['scientific_name']}" if r["scientific_name"] else "",
            f"异名：{r['synonyms']}" if r["synonyms"] else "",
            f"科：{r['family']}" if r["family"] else "",
            f"属：{r['genus']}" if r["genus"] else "",
            f"形态描述：{r['morphology_text']}" if r["morphology_text"] else "",
            f"药材性状：{r['medicinal_shape']}" if r["medicinal_shape"] else "",
            f"生境：{r['habitat']}" if r["habitat"] else "",
            f"国内分布：{r['distribution_china']}" if r["distribution_china"] else "",
            f"国外分布：{r['distribution_abroad']}" if r["distribution_abroad"] else "",
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
