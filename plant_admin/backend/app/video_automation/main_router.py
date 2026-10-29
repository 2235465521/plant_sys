# -*- coding: utf-8 -*-
"""FASTAPI 路由器模块，提供视频自动生成的 API 接口。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

from app.auth_utils import get_current_user
from app.config import get_settings
from app.models import PlantAdminUser
from app.video_automation.db_reader import get_plant_data_for_video
from app.video_automation.image_downloader import ensure_enough_plant_images
from app.video_automation.frame_renderer import get_6_slide_images
from app.video_automation.video_compiler import compile_plant_video

from app.video_automation.typography import TypographyStyle

router = APIRouter(prefix="/video-automation", tags=["video-automation"])

class VideoStyleConfig(BaseModel):
    transition_style: list[str] | str = ["book_flip"]
    text_effect: str = "fade_in"
    sticker_effect: str = "none"
    voice_over: str = "none"
    bgm_type: str = "default"
    typography: Optional[TypographyStyle] = None


@router.post("/generate")
def generate_video(
    plant_id: int,
    current_user: Annotated[PlantAdminUser, Depends(get_current_user)],
    style: VideoStyleConfig = None
):
    if style is None:
        style = VideoStyleConfig()
    """
    根据植物 ID 生成 20 秒短视频：
    - 读取植物信息
    - 图片不足 6 张时，自动通过网络搜图补充或视角变体补齐
    - 渲染 6 张古风 Slide 帧
    - 压制高兼容性 MP4 视频
    """
    print(f"RECEIVED STYLE: {style.model_dump()}")
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
    success, msg = compile_plant_video(slides, output_path, plant_data=plant_data, style=style)
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


# ==============================================================================
# 异步语义多功能视频生成 (Task Queue & Endpoints)
# ==============================================================================
import uuid
import threading
import time
from typing import Dict

video_tasks: Dict[str, dict] = {}
tasks_lock = threading.Lock()


class SemanticGenerateRequest(BaseModel):
    prompt: str
    style_preset: str = "ancient"
    model_mode: str = "flash"  # "flash" | "pro"
    typography: Optional[TypographyStyle] = None


def _update_task(task_id: str, **kwargs):
    with tasks_lock:
        if task_id in video_tasks:
            video_tasks[task_id].update(kwargs)


def _async_semantic_video_worker(
    task_id: str,
    prompt: str,
    style_preset: str,
    model_mode: str = "flash",
    typography: Optional[TypographyStyle] = None
):
    """后台工作线程：执行语义解析 -> 候选植物检索 -> 视频渲染合成"""
    try:
        model_title = "DeepSeek-Reasoner (Pro)" if model_mode == "pro" else "DeepSeek-Flash"
        _update_task(task_id, status="processing", progress_percentage=5, current_step=f"正在通过 [{model_title}] 进行自然语言意图解析...")
        
        from app.semantic_search import search_plants_for_video
        from app.video_automation.video_compiler import compile_plant_video, compile_collection_video

        search_result = search_plants_for_video(prompt, model_mode=model_mode)
        mode = search_result.get("mode", "single")
        topic_title = search_result.get("topic_title") or prompt[:10]
        plants = search_result.get("plants") or []

        if not plants:
            _update_task(
                task_id,
                status="failed",
                progress_percentage=100,
                current_step="未匹配到植物",
                message="数据库中未匹配到相关植物，请尝试修改提示词（如换成产地、功效或月份描述）。"
            )
            return

        plant_names = [p.get("vernacular_name") or "未命名植物" for p in plants]
        _update_task(
            task_id,
            progress_percentage=15,
            current_step=f"【{model_title}】识别为【{'单植物' if mode == 'single' and len(plants) == 1 else '专题合集'}】，成功精选 {len(plants)} 种植物: {', '.join(plant_names[:5])}{'...' if len(plants) > 5 else ''}",
            matched_plants=plant_names
        )

        settings = get_settings()
        base_dir = Path(__file__).resolve().parent.parent.parent
        media_dir = base_dir / settings.plant_media_subdir
        video_dir = media_dir / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)

        output_filename = f"semantic_{task_id[:8]}.mp4"
        output_path = str((video_dir / output_filename).resolve())
        style_config = VideoStyleConfig(transition_style="book_flip" if style_preset == "ancient" else "crossfade")

        # 区分单植物 vs 多植物合集
        if mode == "single" and len(plants) == 1:
            pdata = plants[0]
            pid = pdata["id"]

            def progress_cb(pct: int, msg_str: str):
                _update_task(task_id, progress_percentage=pct, current_step=msg_str)

            if style_preset in ["modern_trivia", "trivia", "modern"]:
                from app.video_automation.trivia_compiler import compile_trivia_video
                success, msg = compile_trivia_video(
                    plant_data=pdata,
                    output_path=output_path,
                    use_pro=(model_mode == "pro"),
                    progress_callback=progress_cb,
                    typography=typography
                )
                if not success:
                    _update_task(task_id, status="failed", progress_percentage=100, current_step="趣闻视频压制失败", message=msg)
                    return
            else:
                _update_task(task_id, progress_percentage=25, current_step=f"开始为单植物 [{pdata.get('vernacular_name')}] 渲染 6 帧画卷...")
                
                # 补齐图片至 6 张
                try:
                    paths = ensure_enough_plant_images(
                        plant_id=pid,
                        vernacular_name=pdata.get("vernacular_name") or "",
                        scientific_name=pdata.get("scientific_name") or "",
                        existing_server_paths=pdata.get("image_server_paths") or [],
                        target_count=6
                    )
                    pdata["image_server_paths"] = paths
                except Exception as e:
                    print(f"[Warning] 搜图补充异常: {e}")

                slides = get_6_slide_images(pdata)
                _update_task(task_id, progress_percentage=60, current_step="正在压制 20s 单植物高清短视频...")
                
                success, msg = compile_plant_video(slides, output_path, plant_data=pdata, style=style_config)
                if not success:
                    _update_task(task_id, status="failed", progress_percentage=100, current_step="压制失败", message=msg)
                    return
        else:
            def progress_cb(pct: int, msg_str: str):
                _update_task(task_id, progress_percentage=pct, current_step=msg_str)

            success, msg = compile_collection_video(
                topic_title=topic_title,
                plants_data_list=plants,
                output_path=output_path,
                style=style_config,
                progress_callback=progress_cb
            )
            if not success:
                _update_task(task_id, status="failed", progress_percentage=100, current_step="合集压制失败", message=msg)
                return

        video_url = f"/api/media/plants/videos/{output_filename}"
        _update_task(
            task_id,
            status="completed",
            progress_percentage=100,
            current_step="生成成功！",
            message=f"【{topic_title}】视频已由 [{model_title}] 为您打造完成！涵盖 {len(plants)} 种精选植物。",
            result_video_url=video_url
        )

    except Exception as e:
        print(f"[Task Error] {task_id}: {e}")
        _update_task(task_id, status="failed", progress_percentage=100, current_step="异常失败", message=str(e))


@router.post("/semantic-generate")
def start_semantic_video_generation(
    req: SemanticGenerateRequest,
    current_user: Annotated[PlantAdminUser, Depends(get_current_user)]
):
    """
    提交自然语言 Prompt 生成单植物或多植物合集视频（支持 model_mode: "flash" | "pro"）。
    """
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="提示词不能为空")

    task_id = str(uuid.uuid4())
    now = time.time()
    
    with tasks_lock:
        video_tasks[task_id] = {
            "task_id": task_id,
            "status": "queued",
            "progress_percentage": 0,
            "current_step": "任务已排队等待处理...",
            "message": "",
            "result_video_url": None,
            "matched_plants": [],
            "created_at": now
        }

    t = threading.Thread(
        target=_async_semantic_video_worker,
        args=(task_id, req.prompt.strip(), req.style_preset, req.model_mode, req.typography),
        daemon=True
    )
    t.start()

    return {
        "success": True,
        "task_id": task_id,
        "message": f"视频生成任务已提交 ({req.model_mode.upper()} 模式)，后台处理中..."
    }



@router.get("/task-status/{task_id}")
def get_semantic_video_task_status(
    task_id: str,
    current_user: Annotated[PlantAdminUser, Depends(get_current_user)]
):
    """
    轮询轮询获取异步视频生成任务的状态与进度。
    """
    with tasks_lock:
        task = video_tasks.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="未找到该视频生成任务")

    return task

