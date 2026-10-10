# -*- coding: utf-8 -*-
"""视频编译核心模块。将 Pillow 渲染的多张 Slide 图片，加转场动效、配音配乐，编译成手机高兼容性的 MP4。"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Generator, Any
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
    curr_slide: SlideData,
    next_slide: SlideData,
    ease: float
):
    """
    为中间植物图片渲染 3D 书本翻页转场动效。
    """
    curr_p = curr_slide.photo_canvas
    curr_pos = curr_slide.photo_pos
    next_p = next_slide.photo_canvas
    next_pos = next_slide.photo_pos
    
    # 使用 Smooth Cubic S-Curve 三次缓动曲线，让物理翻页带有自然重力惯性
    if ease < 0.5:
        s_ease = 4.0 * ease * ease * ease
    else:
        f = 2.0 * ease - 2.0
        s_ease = 0.5 * f * f * f + 1.0
    
    # 1. 自然 3D 书本卷轴翻页 (3D Book/Page Flip)
    if s_ease < 0.5:
        progress = s_ease * 2.0
        scale_x = max(0.005, (1.0 - progress) ** 1.2)
        p_img, dx, dy = apply_photo_scale(curr_p, scale_x, 1.0)
        # 左侧书脊轴固定，右侧向左翻折
        frame.paste(p_img, (curr_pos[0], curr_pos[1]), p_img)
        
        # 添加翻页暗面影效果
        if progress > 0.1:
            shadow = Image.new("RGBA", p_img.size, (0, 0, 0, int(120 * progress)))
            frame.paste(shadow, (curr_pos[0], curr_pos[1]), p_img)
    else:
        progress = (s_ease - 0.5) * 2.0
        scale_x = max(0.005, progress ** 1.2)
        p_img, dx, dy = apply_photo_scale(next_p, scale_x, 1.0)
        # 新一页从书脊轴展开
        frame.paste(p_img, (next_pos[0], next_pos[1]), p_img)
        
        # 亮面高光展平
        if progress < 0.9:
            highlight = Image.new("RGBA", p_img.size, (255, 255, 255, int(90 * (1.0 - progress))))
            frame.paste(highlight, (next_pos[0], next_pos[1]), p_img)


def generate_video_frames(
    slides: list[SlideData],
    style: Any = None,
    fps: int = 30,
    output_size: tuple[int, int] | None = None,
) -> Generator[Image.Image, None, None]:
    """
    生成短视频全部 30fps 帧:
    - 背景: 静态纸张古风背景
    - 文字: 淡入淡出 (Cross-fade)
    - 中间图片: 3D 书本翻页 (Book Flip) 转场
    - output_size: 可选，指定输出分辨率 (w, h)；默认与渲染分辨率相同。
      合集模式传入 (720, 1280) 可将管道数据量降低 75%%，大幅加速压制。
    """
    num_slides = len(slides)
    frames_per_slide = 120   # 每张幻灯片静止+转场帧数
    transition_frames = 48   # 转场帧数 48 帧 = 1.6 秒

    bg_paper = load_paper_background()

    def _out(frame: Image.Image) -> Image.Image:
        """按需缩放输出帧 (BILINEAR: 合集降分辨率速度比 LANCZOS 快 5-8x，质量已够用)"""
        if output_size is not None:
            return frame.resize(output_size, Image.Resampling.BILINEAR)
        return frame

    for i in range(num_slides):
        curr_slide = slides[i]
        next_slide = slides[(i + 1) % num_slides]

        # 1. 静态展示帧
        static_count = frames_per_slide - transition_frames
        for _ in range(static_count):
            yield _out(curr_slide.full_slide.copy())

        # 2. 混合过渡转场帧
        for k in range(transition_frames):
            ease = (k + 1) / float(transition_frames + 1)
            frame = bg_paper.copy()

            curr_t = apply_photo_opacity(curr_slide.text_canvas, 1.0 - ease)
            next_t = apply_photo_opacity(next_slide.text_canvas, ease)
            frame.paste(curr_t, (0, 0), curr_t)
            frame.paste(next_t, (0, 0), next_t)

            draw_photo_transition(frame, curr_slide, next_slide, ease)
            yield _out(frame)


def compile_plant_video(slides: list[SlideData], output_path: str, plant_data: Any = None, style: Any = None) -> tuple[bool, str]:
    """
    调用 imageio-ffmpeg 提供的静态 FFmpeg 压制单植物视频。
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
        "-i", "-", # 0:v
    ]
    
    input_idx = 1
    bgm_idx = -1
    
    if bgm_path and os.path.exists(bgm_path):
        cmd.extend(["-stream_loop", "-1", "-i", bgm_path])
        bgm_idx = input_idx
        input_idx += 1

    if bgm_idx != -1:
        cmd.extend([
            "-filter_complex", f"[{bgm_idx}:a]afade=t=out:st=21.0:d=2.0[aout]",
            "-map", "0:v", "-map", "[aout]"
        ])
    else:
        cmd.extend([
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-map", "0:v", "-map", f"{input_idx}:a"
        ])

    cmd.extend([
        "-t", "23.0",                 # 总时长 23 秒
        "-c:v", "libx264",            # H.264 视频编码
        "-pix_fmt", "yuv420p",        # 极高的移动端兼容性
        "-crf", "20",                 # 画质指数（单植物保持高画质）
        "-preset", "fast",            # fast: 比 medium 快 40%，画质损失极小
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
        
        for img in generate_video_frames(slides):
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


def compile_collection_video(
    topic_title: str,
    plants_data_list: list[dict],
    output_path: str,
    style: Any = None,
    progress_callback: Any = None
) -> tuple[bool, str]:
    """
    编译多植物专题合集短视频。
    """
    from app.video_automation.frame_renderer import (
        render_title_curtain_frame,
        render_outro_curtain_frame,
        get_condensed_slide_images
    )
    from app.video_automation.image_downloader import ensure_enough_plant_images

    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    total_plants = len(plants_data_list)
    if progress_callback:
        progress_callback(15, f"准备合成专题 [{topic_title}]，匹配到 {total_plants} 种植物...")

    all_slides: list[SlideData] = []
    
    # 1. 片头幕
    title_slide = render_title_curtain_frame(topic_title, f"中国植物库 · {total_plants}种精选植物专题")
    all_slides.append(title_slide)

    # 2. 依次构建每个植物的章节 Slide
    for idx, pdata in enumerate(plants_data_list):
        pid = pdata.get("id")
        vname = pdata.get("vernacular_name") or f"植物{pid}"
        if progress_callback:
            pct = 20 + int((idx / total_plants) * 50)
            progress_callback(pct, f"正在处理第 {idx+1}/{total_plants} 种植物 [{vname}]...")

        try:
            paths = ensure_enough_plant_images(
                plant_id=pid,
                vernacular_name=vname,
                scientific_name=pdata.get("scientific_name") or "",
                existing_server_paths=pdata.get("image_server_paths") or [],
                target_count=3
            )
            pdata["image_server_paths"] = paths
        except Exception as e:
            print(f"[Warning] 植物 {vname} 图片补充异常: {e}")

        badge_str = f"{idx+1:02d}/{total_plants:02d}"
        plant_slides = get_condensed_slide_images(pdata, badge_str)
        all_slides.extend(plant_slides)

    # 3. 片尾幕
    outro_slide = render_outro_curtain_frame(f"中国植物库 · {topic_title} 专题合成")
    all_slides.append(outro_slide)

    if progress_callback:
        progress_callback(75, f"全部 {len(all_slides)} 帧画面已渲染完成，开始进行音视频压制...")

    # 合集视频降至 720×1280：管道原始数据量减少 75%，压制速度提升 4-5x
    COLLECTION_W, COLLECTION_H = 720, 1280

    fps = 30
    total_frames = len(all_slides) * 120
    total_seconds = total_frames / float(fps)

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    bgm_path = get_default_bgm_path()

    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{COLLECTION_W}x{COLLECTION_H}",  # 720×1280，比原始 1080×1920 数据量少 75%
        "-r", str(fps),
        "-i", "-", # 0:v
    ]

    input_idx = 1
    bgm_idx = -1

    if bgm_path and os.path.exists(bgm_path):
        cmd.extend(["-stream_loop", "-1", "-i", bgm_path])
        bgm_idx = input_idx
        input_idx += 1

    fade_out_start = max(1.0, total_seconds - 2.5)
    if bgm_idx != -1:
        cmd.extend([
            "-filter_complex",
            f"[{bgm_idx}:a]volume=0.25,afade=t=out:st={fade_out_start:.1f}:d=2.0[aout]",
            "-map", "0:v", "-map", "[aout]"
        ])
    else:
        cmd.extend([
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-map", "0:v", "-map", f"{input_idx}:a"
        ])

    cmd.extend([
        "-t", f"{total_seconds:.2f}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "23",                 # 合集可略降画质换速度
        "-preset", "ultrafast",       # ultrafast: 编码 CPU 时间减少 80%
        "-c:a", "aac",
        "-b:a", "128k",
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

        global_frame_idx = 0
        for img in generate_video_frames(all_slides, output_size=(COLLECTION_W, COLLECTION_H)):
            proc.stdin.write(img.tobytes())
            global_frame_idx += 1
            if progress_callback and (global_frame_idx % 300 == 0):  # 更频繁更新进度（每 10s）
                pct = 75 + int((global_frame_idx / total_frames) * 20)
                progress_callback(pct, f"视频压制进度 [{global_frame_idx}/{total_frames}] 帧段...")

        proc.stdin.close()
        stdout_data, stderr_data = proc.communicate()

        if proc.returncode == 0:
            if progress_callback:
                progress_callback(100, "视频压制与拼接已全部完成！")
            return True, "合集视频合成成功"
        else:
            err_msg = stderr_data.decode("utf-8", errors="replace")
            return False, f"FFmpeg 压制报错: {err_msg}"

    except Exception as e:
        return False, f"合成过程发生异常: {str(e)}"
