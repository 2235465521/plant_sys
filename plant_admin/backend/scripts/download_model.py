import sys
import os

def main():
    try:
        from modelscope import snapshot_download
    except ImportError:
        print("[错误] 未检测到 modelscope 库。请在虚拟环境中运行：")
        print("pip install modelscope")
        sys.exit(1)
        
    print("正在从 ModelScope 国内源下载模型 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'...")
    model_id = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    target_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "models", "paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    try:
        snapshot_download(
            model_id=model_id,
            local_dir=target_dir
        )
        print("\n[成功] 模型已下载并成功保存至本地目录:", target_dir)
    except Exception as e:
        print(f"\n[错误] 下载失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
