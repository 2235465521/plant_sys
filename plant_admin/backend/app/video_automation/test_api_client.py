# -*- coding: utf-8 -*-
"""API 测试客户端：模拟登录并请求生成视频。"""
from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error

API_BASE = "http://127.0.0.1:8000/api"


def run_api_test():
    # Windows 命令行 UTF-8 支持
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # 1. 登录获取 token
    login_url = f"{API_BASE}/auth/login"
    login_data = {
        "username": "test_admin",
        "password": "test_pwd123"
    }
    
    print(f"1. 正在登录获取 JWT Token... (URL: {login_url})")
    req = urllib.request.Request(
        login_url,
        data=json.dumps(login_data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            resp_body = json.loads(res.read().decode("utf-8"))
            token = resp_body.get("access_token")
            if not token:
                print("登录失败：未返回 access_token")
                return
            print("登录成功！已获取 JWT Token.")
    except urllib.error.URLError as e:
        print(f"网络连接错误，请确认 FastAPI 后端服务已启动 (在 8000 端口): {e}")
        return
    except Exception as e:
        print(f"登录异常: {e}")
        return
        
    # 2. 请求生成视频
    generate_url = f"{API_BASE}/video-automation/generate?plant_id=3"
    print(f"\n2. 正在请求生成视频 API... (URL: {generate_url})")
    
    # POST 请求，即使没有 body 也必须是 POST 方法
    req_gen = urllib.request.Request(
        generate_url,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    
    try:
        with urllib.request.urlopen(req_gen, timeout=60) as res_gen:
            resp_gen = json.loads(res_gen.read().decode("utf-8"))
            print("\n[SUCCESS] API 返回成功！响应结果如下：")
            print(json.dumps(resp_gen, indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print(f"API 接口返回错误 (HTTP {e.code}): {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"请求异常: {e}")


if __name__ == "__main__":
    run_api_test()
