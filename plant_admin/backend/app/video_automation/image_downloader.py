# -*- coding: utf-8 -*-
"""图片自动补充模块。当植物数据库图片不足 6 张时，使用现有植物图片的特写裁剪变体补齐，确保100%准确。"""
from __future__ import annotations

import os
from pathlib import Path
from PIL import Image

V_WIDTH = 1080
V_HEIGHT = 1920


def ensure_enough_plant_images(
    plant_id: int,
    vernacular_name: str,
    scientific_name: str,
    existing_server_paths: list[str],
    target_count: int = 6
) -> list[str]:
    """
    检查并补足植物图片到 target_count (默认 6 张):
    1. 保留现有的本地有效图片。
    2. 若不足 6 张，自动使用现有植物图片的特写裁剪变体（Ken Burns 风格缩放截取）轮流补齐。
    安全上限与去重校验，彻底防止死循环卡死。
    """
    base_dir = Path(__file__).resolve().parent.parent.parent
    media_dir = base_dir / "data" / "plant_images" / str(plant_id)
    media_dir.mkdir(parents=True, exist_ok=True)
    
    # 清理旧有的误下载文件
    for old_f in media_dir.glob("auto_plant_*.jpg"):
        try:
            old_f.unlink()
        except Exception:
            pass
    for old_f in media_dir.glob("auto_supplement_*.jpg"):
        try:
            old_f.unlink()
        except Exception:
            pass

    raw_paths = list(existing_server_paths or [])
    
    # 过滤出物理文件确实存在的图片路径
    valid_local_paths = []
    for sp in raw_paths:
        prefix = "/api/media/plants/"
        if sp.startswith(prefix):
            sub_path = sp[len(prefix):]
            abs_p = base_dir / "data" / "plant_images" / sub_path
            if abs_p.exists() and sp not in valid_local_paths:
                valid_local_paths.append(sp)
                
    final_server_paths = list(valid_local_paths)
    
    # 若有效图片数已经达到或超过 6 张，直接返回
    if len(final_server_paths) >= target_count:
        return final_server_paths
        
    # 如果本地完全没有可用物理图片文件，直接返回
    if not final_server_paths:
        return final_server_paths

    original_paths = list(final_server_paths)
    var_idx = 1
    max_attempts = 20  # 防死循环硬上限
    
    while len(final_server_paths) < target_count and var_idx <= max_attempts:
        base_sp = original_paths[(var_idx - 1) % len(original_paths)]
        prefix = "/api/media/plants/"
        sub_p = base_sp[len(prefix):]
        src_abs = base_dir / "data" / "plant_images" / sub_p
        
        if src_abs.exists():
            try:
                var_path = media_dir / f"crop_variant_{var_idx}.jpg"
                
                # 如果变体文件尚未生成，则进行剪裁生成
                if not var_path.exists():
                    with Image.open(src_abs) as orig:
                        w, h = orig.size
                        mod = var_idx % 4
                        if mod == 1:
                            crop_box = (0, 0, int(w * 0.85), int(h * 0.85))
                        elif mod == 2:
                            crop_box = (int(w * 0.15), int(h * 0.15), w, h)
                        elif mod == 3:
                            crop_box = (int(w * 0.1), int(h * 0.1), int(w * 0.9), int(h * 0.9))
                        else:
                            crop_box = (int(w * 0.05), 0, int(w * 0.95), h)
                            
                        cropped = orig.crop(crop_box)
                        cropped.save(var_path, quality=92)
                
                rel_sub = var_path.relative_to(base_dir / "data" / "plant_images").as_posix()
                server_path = f"/api/media/plants/{rel_sub}"
                if server_path not in final_server_paths:
                    final_server_paths.append(server_path)
            except Exception:
                pass
        var_idx += 1
                
    return final_server_paths
