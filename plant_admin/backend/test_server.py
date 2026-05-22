"""最小测试服务——用来排查 uvicorn 在本机是否能正常响应 HTTP 请求"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}
