# -*- coding: utf-8 -*-
"""视频编译核心模块。将 Pillow 渲染的多张 Slide 图片，加转场动效、配音配乐，编译成手机高兼容性的 MP4。"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Generator, Any
from PIL import Image, ImageDraw
import imageio_ffmpeg
import math

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
    ease: float,
    transition_style: str = "random"
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
    
    effect_map = {
        "page_flip": 0,
        "fly_in_right": 1,
        "zoom": 2,
        "fly_up": 3,
        "vertical_flip": 4,
        "crossfade": 5,
        "book_flip": 6
    }
    
    if isinstance(transition_style, list):
        if len(transition_style) > 0:
            current_style = transition_style[trans_idx % len(transition_style)]
        else:
            current_style = "random"
    else:
        current_style = transition_style
        
    if current_style in effect_map:
        effect = effect_map[current_style]
    else:
        effect = trans_idx % 7
    
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

    elif effect == 5:
        # 6. 渐变融入 (Smooth Cross-fade)
        p1 = apply_photo_opacity(curr_p, 1.0 - ease)
        frame.paste(p1, curr_pos, p1)
        p2 = apply_photo_opacity(next_p, ease)
        frame.paste(p2, next_pos, p2)

    else:
        # 7. 卷页效果 (Page Curl) - 带有卷曲背部和阴影的对角线翻页
        # 底图是 next_p
        frame.paste(next_p, next_pos)
        
        cw, ch = curr_p.size
        # 将进度转换为对角线位置 (从右下角 cw+ch 退到 0)
        c = (cw + ch) * (1.0 - ease)
        
        # 绘制 curr_p 的可见区域蒙版
        mask = Image.new("L", (cw, ch), 0)
        draw_mask = ImageDraw.Draw(mask)
        
        pts = [(0, 0)]
        if c > cw:
            pts.extend([(cw, 0), (cw, c - cw)])
        else:
            pts.append((c, 0))
            
        if c > ch:
            pts.extend([(c - ch, ch), (0, ch)])
        else:
            pts.append((0, c))
            
        draw_mask.polygon(pts, fill=255)
        # 将当前页面内容通过蒙版贴上去
        frame.paste(curr_p, curr_pos, mask)
        
        # 绘制卷曲的背面和阴影
        if ease > 0 and ease < 1:
            draw = ImageDraw.Draw(frame, "RGBA")
            P1 = (cw, c - cw) if c > cw else (c, 0)
            P2 = (c - ch, ch) if c > ch else (0, c)
            P3 = (c - ch, c - cw) # 折叠过来的右下角坐标
            
            # 映射到画面绝对坐标
            cx, cy = curr_pos
            P1 = (P1[0] + cx, P1[1] + cy)
            P2 = (P2[0] + cx, P2[1] + cy)
            P3 = (P3[0] + cx, P3[1] + cy)
            
            # 投影 (稍微向右下偏移)
            shadow_offset = 15
            draw.polygon([P1, P2, (P3[0] + shadow_offset, P3[1] + shadow_offset)], fill=(0, 0, 0, 50))
            
            # 卷起的纸张背面
            draw.polygon([P1, P2, P3], fill=(245, 245, 245, 255))
            
            # 折叠线的高光/阴影
            draw.line([P1, P2], fill=(200, 200, 200, 180), width=2)


def draw_stickers(frame: Image.Image, frame_idx: int, effect: str):
    if effect == "petals":
        draw = ImageDraw.Draw(frame)
        for i in range(15):
            # 伪随机下落轨迹
            x = (i * 137 + frame_idx * (2 + i % 3)) % V_WIDTH
            y = ((i * 211 + frame_idx * (3 + i % 4)) % (V_HEIGHT + 100)) - 50
            size = 10 + (i % 8)
            draw.ellipse((x, y, x + size, y + size), fill=(255, 180, 200, 150))
    elif effect == "vintage_border":
        draw = ImageDraw.Draw(frame, "RGBA")
        bw = 20
        # 画一个简单的深色半透明内边框
        draw.rectangle([0, 0, V_WIDTH, bw], fill=(50, 30, 20, 100))
        draw.rectangle([0, V_HEIGHT-bw, V_WIDTH, V_HEIGHT], fill=(50, 30, 20, 100))
        draw.rectangle([0, 0, bw, V_HEIGHT], fill=(50, 30, 20, 100))
        draw.rectangle([V_WIDTH-bw, 0, V_WIDTH, V_HEIGHT], fill=(50, 30, 20, 100))
    elif effect == "light_leaks":
        draw = ImageDraw.Draw(frame, "RGBA")
        x = int(math.sin(frame_idx * 0.05) * 200) - 100
        y = int(math.cos(frame_idx * 0.03) * 200) - 100
        draw.ellipse((x, y, x + 600, y + 600), fill=(255, 150, 50, 40))
        draw.ellipse((V_WIDTH - 500 - x, V_HEIGHT - 500 - y, V_WIDTH + 100 - x, V_HEIGHT + 100 - y), fill=(255, 200, 100, 30))
    elif effect == "falling_leaves":
        draw = ImageDraw.Draw(frame, "RGBA")
        for i in range(12):
            x = (i * 187 + frame_idx * (3 + i % 5)) % V_WIDTH
            y = ((i * 311 + frame_idx * (4 + i % 6)) % (V_HEIGHT + 100)) - 50
            size_x = 15 + (i % 10)
            size_y = 8 + (i % 5)
            draw.ellipse((x, y, x + size_x, y + size_y), fill=(200, 120, 40, 180))
    elif effect == "ink_splatter":
        draw = ImageDraw.Draw(frame, "RGBA")
        for i in range(8):
            x = (i * 347) % V_WIDTH
            y = (i * 193) % V_HEIGHT
            r = 20 + (i % 30)
            pulse = math.sin(frame_idx * 0.05 + i) * 5
            draw.ellipse((x, y, x + r + pulse, y + r + pulse), fill=(20, 20, 20, 60))

def generate_video_frames(slides: list[SlideData], style: Any, fps: int = 30) -> Generator[Image.Image, None, None]:
    """
    生成短视频全部 30fps 帧:
    - 背景: 统一向左侧滑 (Slide Left)
    - 文字: 淡入淡出 (Cross-fade) 或 向上浮现 (Slide Up)
    - 中间图片: 翻页、飞入、融入融出、翻折等多样过度动效
    """
    num_slides = len(slides)
    frames_per_slide = 105   # 每张幻灯片静止帧数（配合 23s 总时长）
    transition_frames = 30   # 转场帧数：30帧=1秒，翻页更慢更优雅
    bg_paper = load_paper_background()
    
    
    global_frame_idx = 0
    for i in range(num_slides):
        curr_slide = slides[i]
        next_slide = slides[(i + 1) % num_slides]
        
        # 1. 静态展示帧
        static_count = frames_per_slide - transition_frames
        for _ in range(static_count):
            frame = curr_slide.full_slide.copy()
            if style.sticker_effect != "none":
                draw_stickers(frame, global_frame_idx, style.sticker_effect)
            yield frame
            global_frame_idx += 1
            
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
            
            # (2) 文字与标题：淡入淡出 (Cross-fade) 或向上平移 (Slide Up)
            curr_t = apply_photo_opacity(curr_slide.text_canvas, 1.0 - ease_alpha)
            next_t = apply_photo_opacity(next_slide.text_canvas, ease_alpha)
            if style.text_effect == "slide_up":
                frame.paste(curr_t, (0, int(-50 * ease_alpha)), curr_t)
                frame.paste(next_t, (0, int(50 * (1.0 - ease_alpha))), next_t)
            elif style.text_effect == "slide_down":
                frame.paste(curr_t, (0, int(50 * ease_alpha)), curr_t)
                frame.paste(next_t, (0, int(-50 * (1.0 - ease_alpha))), next_t)
            elif style.text_effect == "slide_left":
                frame.paste(curr_t, (int(-80 * ease_alpha), 0), curr_t)
                frame.paste(next_t, (int(80 * (1.0 - ease_alpha)), 0), next_t)
            elif style.text_effect == "zoom_in":
                # Scale up next text slightly
                curr_scale = 1.0 + 0.1 * ease_alpha
                curr_z, dx1, dy1 = apply_photo_scale(curr_t, curr_scale, curr_scale)
                frame.paste(curr_z, (dx1, dy1), curr_z)
                next_scale = 0.9 + 0.1 * ease_alpha
                next_z, dx2, dy2 = apply_photo_scale(next_t, next_scale, next_scale)
                frame.paste(next_z, (dx2, dy2), next_z)
            elif style.text_effect == "pop_in":
                # Fake pop in by crossfading but faster
                frame.paste(curr_t, (0, 0), curr_t)
                frame.paste(next_t, (0, 0), next_t)
            else:
                frame.paste(curr_t, (0, 0), curr_t)
                frame.paste(next_t, (0, 0), next_t)
            
            # (3) 中间植物图片：执行多维过度动画
            draw_photo_transition(frame, i, curr_slide, next_slide, ease_alpha, style.transition_style)
            
            if style.sticker_effect != "none":
                draw_stickers(frame, global_frame_idx, style.sticker_effect)
                
            yield frame
            global_frame_idx += 1


def compile_plant_video(slides: list[SlideData], output_path: str, plant_data: Any = None, style: Any = None) -> tuple[bool, str]:
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
        "-i", "-", # 0:v
    ]
    
    use_bgm = (getattr(style, "bgm_type", "default") != "none") if style else True
    input_idx = 1
    bgm_idx = -1
    tts_idx = -1
    
    if use_bgm and bgm_path and os.path.exists(bgm_path):
        cmd.extend(["-stream_loop", "-1", "-i", bgm_path])
        bgm_idx = input_idx
        input_idx += 1
        
    tts_path = None
    if style and getattr(style, "voice_over", "none") != "none" and plant_data:
        import edge_tts
        import asyncio
        import tempfile
        import threading
        from app.video_automation.text_summarizer import summarize_plant_for_tts
        
        voice = "zh-CN-XiaoxiaoNeural" if style.voice_over == "female" else "zh-CN-YunxiNeural"
        
        # Step 1: AI 总结植物信息，生成 TTS 朗读词
        print("[TTS] 调用 DeepSeek 生成朗读文案...")
        tts_text = summarize_plant_for_tts(plant_data)
        print(f"[TTS] 朗读文案: {tts_text[:80]}...")
        
        tts_path = os.path.join(tempfile.gettempdir(), f"tts_{plant_data.get('id', 0)}.mp3")
        
        # Step 2: 用独立线程运行 edge_tts（避免与 FastAPI 的事件循环冲突）
        tts_error = [None]
        def run_tts_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                async def gen_tts():
                    communicate = edge_tts.Communicate(tts_text, voice)
                    await communicate.save(tts_path)
                loop.run_until_complete(gen_tts())
                loop.close()
            except Exception as e:
                tts_error[0] = e
        
        t = threading.Thread(target=run_tts_in_thread)
        t.start()
        t.join(timeout=30)
        
        if tts_error[0]:
            print(f"[TTS] 生成失败: {tts_error[0]}")
            tts_path = None
        elif os.path.exists(tts_path):
            print(f"[TTS] 生成成功: {tts_path}")
            cmd.extend(["-i", tts_path])
            tts_idx = input_idx
            input_idx += 1
        else:
            print("[TTS] 文件不存在，跳过")
            tts_path = None

    # TTS 朗读在 16s 开始淡出（持续 1.5s），约 17.5s 完全消失
    # BGM 背景乐在 21s 开始淡出（持续 2s），视频结束前优雅收尾
    if bgm_idx != -1 and tts_idx != -1:
        cmd.extend([
            "-filter_complex",
            f"[{bgm_idx}:a]volume=0.2,afade=t=out:st=21.0:d=2.0[bgm];"
            f"[{tts_idx}:a]volume=1.3,afade=t=out:st=16.0:d=1.5[tts];"
            f"[bgm][tts]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "0:v", "-map", "[aout]"
        ])
    elif bgm_idx != -1:
        cmd.extend([
            "-filter_complex", f"[{bgm_idx}:a]afade=t=out:st=21.0:d=2.0[aout]",
            "-map", "0:v", "-map", "[aout]"
        ])
    elif tts_idx != -1:
        cmd.extend([
            "-filter_complex", f"[{tts_idx}:a]volume=1.3,afade=t=out:st=16.0:d=1.5[aout]",
            "-map", "0:v", "-map", "[aout]"
        ])
    else:
        cmd.extend([
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-map", "0:v", "-map", f"{input_idx}:a"
        ])

        
    cmd.extend([
        "-t", "23.0",                 # 总时长延长至 23 秒
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
        
        for img in generate_video_frames(slides, style, fps=30):
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
