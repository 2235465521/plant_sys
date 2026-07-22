# -*- coding: utf-8 -*-
"""视频编译核心模块。将 Pillow 渲染的多张 Slide 图片，加转场动效、配音配乐，编译成手机高兼容性的 MP4。"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Generator
from PIL import Image
import imageio_ffmpeg

from app.video_automation.bgm_manager import get_default_bgm_path
from app.video_automation.frame_renderer import SlideData, V_WIDTH, V_HEIGHT, load_paper_background


def apply_photo_opacity(photo: Image.Image, opacity: float) -> Image.Image:
    """按比例调整 RGBA 图片的透明度 (0.0 ~ 1.0)"""
    if opacity >= 0.99:
        return photo
    if opacity <= 0.01:
        return Image.new("RGBA", photo.size, (0, 0, 0, 0))
    r, g, b, a = photo.split()
    a = a.point(lambda p: int(p * max(0.0, min(1.0, opacity))))
    return Image.merge("RGBA", (r, g, b, a))


def apply_photo_scale(photo: Image.Image, scale_w: float, scale_h: float) -> tuple[Image.Image, int, int]:
    """按比例缩放 RGBA 图片，返回缩放后的图与 (dx, dy) 居中偏移量"""
    w, h = photo.size
    new_w = max(1, int(w * scale_w))
    new_h = max(1, int(h * scale_h))
    resized = photo.resize((new_w, new_h), Image.Resampling.LANCZOS)
    dx = (w - new_w) // 2
    dy = (h - new_h) // 2
    return resized, dx, dy


def draw_photo_transition(
    frame: Image.Image,
    trans_idx: int,
    curr_slide: SlideData,
    next_slide: SlideData,
    ease: float
):
    """
    为中间植物图片渲染丰富多元的过度动画：
    0: 3D 横向翻页 (Page Flip)
    1: 右侧飞入 (Fly in from Right)
    2: 缩放融入融出 (Zoom & Cross-fade)
    3: 下方弹跳飞入 (Fly up from Bottom)
    4: 3D 纵向翻折 (Vertical Flip)
    5: 渐变融入 (Smooth Cross-fade)
    """
    curr_p = curr_slide.photo_canvas
    curr_pos = curr_slide.photo_pos
    next_p = next_slide.photo_canvas
    next_pos = next_slide.photo_pos
    
    effect = trans_idx % 6
    
    if effect == 0:
        # 1. 3D 横向翻页 (Page Flip)
        if ease < 0.5:
            progress = ease * 2.0
            scale_x = max(0.01, 1.0 - progress)
            p_img, dx, dy = apply_photo_scale(curr_p, scale_x, 1.0)
            frame.paste(p_img, (curr_pos[0] + dx, curr_pos[1] + dy), p_img)
        else:
            progress = (ease - 0.5) * 2.0
            scale_x = max(0.01, progress)
            p_img, dx, dy = apply_photo_scale(next_p, scale_x, 1.0)
            frame.paste(p_img, (next_pos[0] + dx, next_pos[1] + dy), p_img)

    elif effect == 1:
        # 2. 从右侧飞入 (Fly in from Right)
        if ease < 0.5:
            op = 1.0 - ease * 2.0
            p_img = apply_photo_opacity(curr_p, op)
            frame.paste(p_img, (curr_pos[0] - int(120 * ease), curr_pos[1]), p_img)
        else:
            fly_progress = (1.0 - ease) * 2.0
            offset_x = int(V_WIDTH * fly_progress)
            frame.paste(next_p, (next_pos[0] + offset_x, next_pos[1]), next_p)

    elif effect == 2:
        # 3. 缩放融入融出 (Zoom & Cross-Fade)
        curr_op = 1.0 - ease
        curr_scale = 1.0 + 0.15 * ease
        p1, dx1, dy1 = apply_photo_scale(apply_photo_opacity(curr_p, curr_op), curr_scale, curr_scale)
        frame.paste(p1, (curr_pos[0] + dx1, curr_pos[1] + dy1), p1)
        
        next_op = ease
        next_scale = 0.8 + 0.2 * ease
        p2, dx2, dy2 = apply_photo_scale(apply_photo_opacity(next_p, next_op), next_scale, next_scale)
        frame.paste(p2, (next_pos[0] + dx2, next_pos[1] + dy2), p2)

    elif effect == 3:
        # 4. 从下方飞入 (Fly up from Bottom)
        if ease < 0.5:
            offset_y = int(V_HEIGHT * (ease * 2.0))
            frame.paste(curr_p, (curr_pos[0], curr_pos[1] - offset_y), curr_p)
        else:
            fly_y = int(V_HEIGHT * (1.0 - (ease - 0.5) * 2.0))
            frame.paste(next_p, (next_pos[0], next_pos[1] + fly_y), next_p)

    elif effect == 4:
        # 5. 3D 纵向翻折 (Vertical Flip)
        if ease < 0.5:
            progress = ease * 2.0
            scale_y = max(0.01, 1.0 - progress)
            p_img, dx, dy = apply_photo_scale(curr_p, 1.0, scale_y)
            frame.paste(p_img, (curr_pos[0] + dx, curr_pos[1] + dy), p_img)
        else:
            progress = (ease - 0.5) * 2.0
            scale_y = max(0.01, progress)
            p_img, dx, dy = apply_photo_scale(next_p, 1.0, scale_y)
            frame.paste(p_img, (next_pos[0] + dx, next_pos[1] + dy), p_img)

    else:
        # 6. 渐变融入 (Smooth Cross-fade)
        p1 = apply_photo_opacity(curr_p, 1.0 - ease)
        frame.paste(p1, curr_pos, p1)
        p2 = apply_photo_opacity(next_p, ease)
        frame.paste(p2, next_pos, p2)


def generate_video_frames(slides: list[SlideData], fps: int = 30) -> Generator[Image.Image, None, None]:
    """
    生成短视频全部 30fps 帧:
    - 背景: 统一向左侧滑 (Slide Left)
    - 文字: 淡入淡出 (Cross-fade)
    - 中间图片: 翻页、飞入、融入融出、翻折等多样过度动效
    """
    num_slides = len(slides)
    frames_per_slide = 100
    transition_frames = 15
    bg_paper = load_paper_background()
    
    for i in range(num_slides):
        curr_slide = slides[i]
        next_slide = slides[(i + 1) % num_slides]
        
        # 1. 静态展示帧
        static_count = frames_per_slide - transition_frames
        for _ in range(static_count):
            yield curr_slide.full_slide
            
        # 2. 混合过渡转场帧
        for k in range(transition_frames):
            alpha = (k + 1) / float(transition_frames + 1)
            t = alpha * 2
            if t < 1:
                ease_alpha = 0.5 * t * t
            else:
                ease_alpha = -0.5 * ((t - 1) * (t - 3) - 1)
                
            bg_offset = int(V_WIDTH * ease_alpha)
            
            # (1) 背景纸底图：统一向左侧滑
            frame = Image.new("RGB", (V_WIDTH, V_HEIGHT))
            frame.paste(bg_paper, (-bg_offset, 0))
            frame.paste(bg_paper, (V_WIDTH - bg_offset, 0))
            
            # (2) 文字与标题：淡入淡出 (Cross-fade)
            curr_t = apply_photo_opacity(curr_slide.text_canvas, 1.0 - ease_alpha)
            next_t = apply_photo_opacity(next_slide.text_canvas, ease_alpha)
            frame.paste(curr_t, (0, 0), curr_t)
            frame.paste(next_t, (0, 0), next_t)
            
            # (3) 中间植物图片：执行多维过度动画 (翻页、飞入、融入、翻折等)
            draw_photo_transition(frame, i, curr_slide, next_slide, ease_alpha)
            
            yield frame


def compile_plant_video(slides: list[SlideData], output_path: str) -> tuple[bool, str]:
    """
    调用 imageio-ffmpeg 提供的静态 FFmpeg 压制视频。
    - 压制格式：H.264 (libx264), yuv420p 像素格式，AAC 音频。
    - 自动加入背景音乐并淡出。
    """
    if len(slides) < 6:
        return False, f"Slide 数量不足（预期 6 个，实际只有 {len(slides)} 个）"
        
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    bgm_path = get_default_bgm_path()
    
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{V_WIDTH}x{V_HEIGHT}",
        "-r", "30",
        "-i", "-", # 视频流从管道输入
    ]
    
    if bgm_path and os.path.exists(bgm_path):
        cmd.extend([
            "-stream_loop", "-1",
            "-i", bgm_path
        ])
        audio_filter = "afade=t=out:st=18.5:d=1.5"
        cmd.extend([
            "-filter_complex", f"[1:a]{audio_filter}[aout]",
            "-map", "0:v",
            "-map", "[aout]"
        ])
    else:
        cmd.extend([
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo"
        ])
        cmd.extend([
            "-map", "0:v",
            "-map", "1:a"
        ])
        
    cmd.extend([
        "-t", "20.0",                 # 总时长限制在 20 秒
        "-c:v", "libx264",            # H.264 视频编码
        "-pix_fmt", "yuv420p",        # 极高的移动端兼容性
        "-crf", "20",                 # 画质指数
        "-preset", "medium",          # 压缩预设速度
        "-c:a", "aac",                # AAC 音频编码
        "-b:a", "128k",               # 音频比特率
        output_path
    ])
    
    try:
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo
        )
        
        for img in generate_video_frames(slides, fps=30):
            proc.stdin.write(img.tobytes())
            
        proc.stdin.close()
        stdout_data, stderr_data = proc.communicate()
        
        if proc.returncode == 0:
            return True, "视频合成成功"
        else:
            err_msg = stderr_data.decode("utf-8", errors="replace")
            return False, f"FFmpeg 报错: {err_msg}"
            
    except Exception as e:
        return False, f"合成过程发生异常: {str(e)}"
