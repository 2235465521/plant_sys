# -*- coding: utf-8 -*-
"""管理背景音乐资源的载入与默认静音轨生成。"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import imageio_ffmpeg


def get_default_bgm_path() -> str:
    """返回默认背景音乐的物理路径。"""
    base_dir = Path(__file__).resolve().parent.parent.parent
    bgm_dir = base_dir / "data" / "video_assets" / "bgm"
    bgm_dir.mkdir(parents=True, exist_ok=True)
    
    # 查找目录下是否有任意 mp3
    mp3_files = list(bgm_dir.glob("*.mp3"))
    if mp3_files:
        return str(mp3_files[0].resolve())
    
    # 如果没有 mp3，则返回预设的路径，后续在合成时如果没有物理文件会触发生成静音轨
    return str((bgm_dir / "default_bgm.mp3").resolve())


def generate_silent_audio(output_path: str, duration: float = 20.0) -> bool:
    """调用 imageio-ffmpeg 静态二进制，生成指定长度的静音音轨。"""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(duration),
        "-c:a", "aac",
        output_path
    ]
    try:
        # 隐藏命令行窗口（Windows 兼容）
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            timeout=15
        )
        return result.returncode == 0
    except Exception:
        return False
