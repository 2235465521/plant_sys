import os
import pickle
import numpy as np
from fastapi import HTTPException

# 全局延迟加载变量
_MODEL = None
_EMBEDDINGS_DATA = None

EMBEDDINGS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "plant_embeddings.pkl"
)

def load_resources():
    """延迟加载模型和向量数据，避免 API 启动时卡顿"""
    global _MODEL, _EMBEDDINGS_DATA
    
    if _EMBEDDINGS_DATA is None:
        if not os.path.exists(EMBEDDINGS_PATH):
            raise HTTPException(
                status_code=400,
                detail="AI 语义搜索尚未初始化。请联系管理员在后台运行 scripts/generate_embeddings.py 生成向量数据。"
            )
        try:
            with open(EMBEDDINGS_PATH, "rb") as f:
                _EMBEDDINGS_DATA = pickle.load(f)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"加载 AI 向量数据失败: {str(e)}"
            )

    if _MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            _MODEL = SentenceTransformer(model_name)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"加载 AI 语义模型失败: {str(e)}。请确保已安装 sentence-transformers 并可正常联网/缓存加载。"
            )

def query_semantic_similarity(query: str, allowed_ids: list[int] = None) -> list[tuple[int, float]]:
    """
    计算查询词与已有植物的语义相似度，并返回按相似度降序排列的 (plant_id, score) 列表。
    如果指定了 allowed_ids，则只计算并返回这些 ID 的相似度。
    """
    load_resources()
    
    all_ids = _EMBEDDINGS_DATA["ids"]
    all_embeddings = _EMBEDDINGS_DATA["embeddings"]  # Shape: (N, D)
    
    # 编码查询词，开启归一化以支持点积计算余弦相似度
    query_vector = _MODEL.encode(query, normalize_embeddings=True)  # Shape: (D,)
    
    if allowed_ids is not None:
        allowed_set = set(allowed_ids)
        # 筛选出允许的 ID 及其对应的向量索引
        indices = [i for i, pid in enumerate(all_ids) if pid in allowed_set]
        if not indices:
            return []
        
        filtered_ids = [all_ids[i] for i in indices]
        filtered_embeddings = all_embeddings[indices]
        
        # 计算相似度得分
        scores = np.dot(filtered_embeddings, query_vector)
        results = list(zip(filtered_ids, [float(s) for s in scores]))
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    else:
        scores = np.dot(all_embeddings, query_vector)
        results = list(zip(all_ids, [float(s) for s in scores]))
        results.sort(key=lambda x: x[1], reverse=True)
        return results
