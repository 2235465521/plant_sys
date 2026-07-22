# -*- coding: utf-8 -*-
"""FASTAPI 路由器模块，提供视频自动生成的 API 接口。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.auth_utils import get_current_user
from app.config import get_settings
from app.models import PlantAdminUser
from app.video_automation.db_reader import get_plant_data_for_video
from app.video_automation.image_downloader import ensure_enough_plant_images
from app.video_automation.frame_renderer import get_6_slide_images
from app.video_automation.video_compiler import compile_plant_video

router = APIRouter(prefix="/video-automation", tags=["video-automation"])


@router.post("/generate")
def generate_video(
    plant_id: int,
    current_user: Annotated[PlantAdminUser, Depends(get_current_user)]
):
    """
    根据植物 ID 生成 20 秒短视频：
    - 读取植物信息
    - 图片不足 6 张时，自动通过网络搜图补充或视角变体补齐
    - 渲染 6 张古风 Slide 帧
    - 压制高兼容性 MP4 视频
    """
    # 1. 查询只读数据
    plant_data = get_plant_data_for_video(plant_id)
    if not plant_data:
        raise HTTPException(status_code=404, detail="未找到该植物数据")
        
    # 2. 检查并补充图片至 6 张 (网络自动抓图 + 特写变体补齐)
    try:
        updated_paths = ensure_enough_plant_images(
            plant_id=plant_id,
            vernacular_name=plant_data.get("vernacular_name") or "",
            scientific_name=plant_data.get("scientific_name") or "",
            existing_server_paths=plant_data.get("image_server_paths") or [],
            target_count=6
        )
        plant_data["image_server_paths"] = updated_paths
    except Exception as e:
        print(f"[Warning] 图片自动补充异常: {e}")

    # 3. 准备输出路径
    settings = get_settings()
    base_dir = Path(__file__).resolve().parent.parent.parent
    media_dir = base_dir / settings.plant_media_subdir
    video_dir = media_dir / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    
    output_filename = f"plant_{plant_id}_video.mp4"
    output_path = str((video_dir / output_filename).resolve())
    
    # 4. 渲染幻灯片帧
    try:
        slides = get_6_slide_images(plant_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"渲染图片帧失败: {str(e)}")
        
    # 5. 压制合成视频
    success, msg = compile_plant_video(slides, output_path)
    if not success:
        raise HTTPException(status_code=500, detail=f"压制视频失败: {msg}")
        
    video_url = f"/api/media/plants/videos/{output_filename}"
    
    return {
        "success": True,
        "message": "视频生成成功！已为您应用 6 帧精美古风画卷与动画。",
        "plant_id": plant_id,
        "vernacular_name": plant_data.get("vernacular_name"),
        "video_url": video_url,
        "file_size_bytes": os.path.getsize(output_path) if os.path.exists(output_path) else 0
    }
