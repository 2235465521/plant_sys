# -*- coding: utf-8 -*-
"""
trivia_compiler.py - 草本趣闻短视频编译引擎 (Modern Trivia Video Compiler)
负责将 trivia_renderer 渲染的 5 张 SlideData 与 Edge-TTS 配音解说、轻柔 BGM、3D 卷轴翻页转场进行音画同步压制。
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Generator, Optional
from PIL import Image

import edge_tts
import imageio_ffmpeg

from app.video_automation.bgm_manager import get_default_bgm_path
from app.video_automation.frame_renderer import SlideData, V_WIDTH, V_HEIGHT
from app.video_automation.trivia_renderer import render_trivia_slides, load_trivia_bg
from app.video_automation.trivia_script import TriviaScript, generate_trivia_script

VOICE_DEFAULT = "zh-CN-YunxiNeural"   # 阳光活泼中青年科普男声（最契合短视频）
VOICE_RATE = "+30%"                   # +30% 紧凑快节奏短视频语速
FPS = 30
TRANSITION_FRAMES = 15                # 0.5 秒快节奏平滑转场 (4 * 15 = 60 帧)
TARGET_TOTAL_SECONDS = 20.0           # 严格控制全片总时长在 20 秒 (600 帧)


def get_audio_duration_seconds(audio_path: str) -> float:
    """通过 imageio-ffmpeg 探测音频时长（秒）"""
    if not os.path.exists(audio_path):
        return 0.0
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        p = subprocess.run(
            [exe, "-i", audio_path],
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=10,
        )
        for line in p.stderr.splitlines():
            if "Duration:" in line:
                part = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = part.split(":")
                return float(h) * 3600 + float(m) * 60 + float(s)
    except Exception:
        pass
    return 3.0


async def _synthesize_voice_async(text: str, voice: str, out_path: str, rate: str = VOICE_RATE) -> bool:
    """调用 edge-tts 异步合成单段解说音频（支持倍速控制与重试）"""
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(out_path)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
                return True
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(1.0)
            else:
                print(f"[TriviaTTS] 语音合成失败 ({text[:15]}...): {e}")
    return False


def generate_narration_chunks(
    script: TriviaScript,
    temp_dir: str,
    voice: str = VOICE_DEFAULT
) -> list[tuple[str, float]]:
    """
    为 5 幕生成对应的语音朗读词并获取各自的时长（图文分离：读精炼口语，全片严格控制在 20 秒）：
    Slide 1: 封面介绍 (~2.0s)
    Slide 2: 形态特征 (~3.2s)
    Slide 3: 植物趣闻 (~3.2s)
    Slide 4: 适生范围 (~3.2s)
    Slide 5: 美图收尾 (~2.0s)
    """
    import re
    morph_spoken = script.morphology_spoken or script.morphology_text
    trivia_spoken = script.trivia_spoken or script.trivia_text
    habitat_spoken = script.habitat_spoken or script.habitat_text

    clean_morph = re.sub(r"^(形态特征|特征)[:：\s]*", "", morph_spoken).strip()
    clean_trivia = re.sub(r"^(植物趣闻|趣闻)[:：\s]*", "", trivia_spoken).strip()
    clean_habitat = re.sub(r"^(适生范围|生境分布|生境)[:：\s]*", "", habitat_spoken).strip()

    # 口语朗读句子精简防护（若未设置 spoken，则截取前段自然标点从容控时）
    def _clamp_spoken(s: str, max_chars: int = 22) -> str:
        s = s.strip()
        if len(s) <= max_chars:
            return s.rstrip("。，, ") + "。"
        clauses = [c.strip() for c in re.split(r"[。；，,、]", s) if c.strip()]
        res = ""
        for c in clauses:
            if len(res) + len(c) <= max_chars:
                res += ("，" if res else "") + c
            else:
                break
        if not res and clauses:
            res = clauses[0][:max_chars]
        return res.rstrip("。，, ") + "。"

    clean_morph = _clamp_spoken(clean_morph, max_chars=16)
    clean_trivia = _clamp_spoken(clean_trivia, max_chars=16)
    clean_habitat = _clamp_spoken(clean_habitat, max_chars=16)

    texts = [
        f"每日认识一种植物，{script.plant_name}。",
        clean_morph,
        clean_trivia,
        clean_habitat,
        "带你认识身边草木中药。",
    ]

    results: list[tuple[str, float]] = []
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        for i, txt in enumerate(texts):
            chunk_p = os.path.join(temp_dir, f"narr_{i+1}.mp3")
            ok = loop.run_until_complete(_synthesize_voice_async(txt, voice, chunk_p, rate=VOICE_RATE))
            if ok:
                dur = get_audio_duration_seconds(chunk_p)
                results.append((chunk_p, max(1.8, dur)))
            else:
                # 离线降级为静音固定时长
                results.append(("", 3.0))
    finally:
        loop.close()

    return results


def compute_slide_static_frames(
    durations: list[float],
    fps: int = FPS,
    target_total_seconds: float = TARGET_TOTAL_SECONDS,
    transition_frames: int = TRANSITION_FRAMES
) -> list[int]:
    """
    精确计算各 Slide 的静态停留帧数，使得总片长严格对齐 20 秒：
    1. 目标总帧数 TARGET_TOTAL_FRAMES = int(target_total_seconds * fps) = 600
    2. 转场总帧数 = (N - 1) * transition_frames = 4 * 15 = 60
    3. 静态帧总预算 = 600 - 60 = 540 帧 (18.0 秒)
    4. 各幕保底停留帧 = int(durations[i] * fps) + 3 (确保人声朗读完毕再翻页)
    5. 剩余预算按各幕时长比例分配，并在最后一幕补齐余数，确保总帧数精准达到 600 帧
    """
    num_slides = len(durations)
    if num_slides == 0:
        return []

    target_total_frames = int(target_total_seconds * fps)
    total_trans_frames = (num_slides - 1) * transition_frames
    static_budget = max(num_slides * 20, target_total_frames - total_trans_frames)

    min_frames = [max(24, int(d * fps) + 3) for d in durations]
    sum_min = sum(min_frames)

    if sum_min <= static_budget:
        remaining = static_budget - sum_min
        total_dur = sum(durations) if sum(durations) > 0 else 1.0
        allocated = []
        distributed = 0
        for i in range(num_slides - 1):
            extra = int(remaining * (durations[i] / total_dur))
            allocated.append(min_frames[i] + extra)
            distributed += extra
        allocated.append(min_frames[-1] + (remaining - distributed))
        return allocated
    else:
        # 语音略微超出预算时，保留保底帧数避免截断人声
        return min_frames


def apply_photo_scale(photo: Image.Image, scale_w: float, scale_h: float) -> tuple[Image.Image, int, int]:
    """按比例缩放 RGBA 图片，返回缩放后的图与居中偏移量"""
    w, h = photo.size
    new_w = max(1, int(w * scale_w))
    new_h = max(1, int(h * scale_h))
    resized = photo.resize((new_w, new_h), Image.Resampling.LANCZOS)
    dx = (w - new_w) // 2
    dy = (h - new_h) // 2
    return resized, dx, dy


def apply_photo_opacity(photo: Image.Image, opacity: float) -> Image.Image:
    """调整 RGBA 图片的透明度 (0.0 ~ 1.0)"""
    if opacity >= 0.99:
        return photo
    if opacity <= 0.01:
        return Image.new("RGBA", photo.size, (0, 0, 0, 0))
    r, g, b, a = photo.split()
    a = a.point(lambda p: int(p * max(0.0, min(1.0, opacity))))
    return Image.merge("RGBA", (r, g, b, a))


def draw_photo_transition(
    frame: Image.Image,
    curr_slide: SlideData,
    next_slide: SlideData,
    ease: float
):
    """
    丝滑卡片高级转场 (Smooth Cross-Fade & Scale Transition)：
    - 通栏 1080x900 大图与 1080x1920 全屏摄影保持左右满幅 (无边缘内缩黑边缝隙)，执行纯净无暇 Alpha 交叉淡入淡出 (Cross-Fade)
    - 首屏白瓷药材盘小卡片平滑淡出
    - 绝无黑块、生硬折叠与畸变，完美融合光斑背景
    """
    alpha_out = max(0.0, 1.0 - ease)
    alpha_in = min(1.0, ease)

    # 1. 前一张图
    if curr_slide.photo_canvas.size[0] >= 1080:
        curr_faded = apply_photo_opacity(curr_slide.photo_canvas, alpha_out)
        frame.paste(curr_faded, curr_slide.photo_pos, curr_faded)
    else:
        scale_out = 1.0 - ease * 0.06
        curr_scaled, dx1, dy1 = apply_photo_scale(curr_slide.photo_canvas, scale_out, scale_out)
        curr_faded = apply_photo_opacity(curr_scaled, alpha_out)
        frame.paste(curr_faded, (curr_slide.photo_pos[0] + dx1, curr_slide.photo_pos[1] + dy1), curr_faded)

    # 2. 后一张图
    if next_slide.photo_canvas.size[0] >= 1080:
        next_faded = apply_photo_opacity(next_slide.photo_canvas, alpha_in)
        frame.paste(next_faded, next_slide.photo_pos, next_faded)
    else:
        scale_in = 0.94 + ease * 0.06
        next_scaled, dx2, dy2 = apply_photo_scale(next_slide.photo_canvas, scale_in, scale_in)
        next_faded = apply_photo_opacity(next_scaled, alpha_in)
        frame.paste(next_faded, (next_slide.photo_pos[0] + dx2, next_slide.photo_pos[1] + dy2), next_faded)


def generate_trivia_frames(
    slides: list[SlideData],
    static_frames: list[int],
    fps: int = FPS,
    output_size: Optional[tuple[int, int]] = None
) -> Generator[Image.Image, None, None]:
    """
    生成草本趣闻风的全部连续帧：
    - 精确按 static_frames[i] 停留
    - 转场：文字 Cross-Fade，中间卡片 Smooth Scale & Cross-Fade
    """
    num_slides = len(slides)
    bg = load_trivia_bg()

    def _out(img: Image.Image) -> Image.Image:
        if output_size is not None and output_size != img.size:
            return img.resize(output_size, Image.Resampling.BILINEAR)
        return img

    for i in range(num_slides):
        curr_slide = slides[i]
        next_slide = slides[(i + 1) % num_slides]
        n_frames = static_frames[i] if i < len(static_frames) else 90

        # 本幕停留
        for _ in range(n_frames):
            yield _out(curr_slide.full_slide)

        # 最后一幕直接结束，不进行后续翻页
        if i == num_slides - 1:
            break

        # 快节奏平滑转场帧 (TRANSITION_FRAMES = 15 帧)
        for k in range(TRANSITION_FRAMES):
            ease = (k + 1) / float(TRANSITION_FRAMES + 1)
            frame = bg.copy()

            # 文字淡入淡出
            curr_t = apply_photo_opacity(curr_slide.text_canvas, 1.0 - ease)
            next_t = apply_photo_opacity(next_slide.text_canvas, ease)
            frame.paste(curr_t, (0, 0), curr_t)
            frame.paste(next_t, (0, 0), next_t)

            draw_photo_transition(frame, curr_slide, next_slide, ease)
            yield _out(frame.convert("RGB"))


def build_final_audio(
    chunks: list[tuple[str, float]],
    static_frames: list[int],
    output_audio_path: str,
    bgm_path: str,
    fps: int = FPS
) -> bool:
    """
    使用 FFmpeg 滤镜链拼接各幕语音，并与 BGM（22%音量）进行混流：
    - 按各幕 static_frames 与 TRANSITION_FRAMES 精确计算人声起点
    - 人声音量 100%，背景音乐柔和，结尾 1.0s 平滑淡出
    - 输出音频时长与视频总帧数严格对齐
    """
    exe = imageio_ffmpeg.get_ffmpeg_exe()

    # 计算总帧数与总秒数
    num_slides = len(static_frames)
    total_frames = sum(static_frames) + (num_slides - 1) * TRANSITION_FRAMES
    total_sec = total_frames / float(fps)
    fade_start = max(0.0, total_sec - 1.0)

    # 1. 检查是否存在有效配音文件
    valid_chunks = [p for p, _ in chunks if p and os.path.exists(p)]
    if not valid_chunks:
        # 无语音，仅使用 BGM
        if os.path.exists(bgm_path):
            cmd = [
                exe, "-y",
                "-i", bgm_path,
                "-filter_complex", f"[0:a]aloop=loop=-1:size=2e+09,atrim=0:{total_sec:.2f},volume=0.22,afade=t=out:st={fade_start:.2f}:d=1.0[aout]",
                "-map", "[aout]",
                "-ac", "2", "-ar", "44100",
                output_audio_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=25)
            return os.path.exists(output_audio_path)
        return False

    # 2. 精确计算每幕人声起点 frame_start 与 adelay (毫秒)
    filter_inputs = []
    filter_delays = []
    curr_frame = 0

    cmd = [exe, "-y"]
    input_idx = 0

    for i, (chunk_p, _) in enumerate(chunks):
        if chunk_p and os.path.exists(chunk_p):
            cmd.extend(["-i", chunk_p])
            delay_ms = int((curr_frame / float(fps)) * 1000)
            filter_delays.append(f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}[a{input_idx}]")
            filter_inputs.append(f"[a{input_idx}]")
            input_idx += 1

        # 下一幕人声起点 = 当前帧 + 本幕停留帧 + 转场帧
        curr_frame += static_frames[i] + TRANSITION_FRAMES

    # 加上 BGM 输入
    has_bgm = os.path.exists(bgm_path)
    if has_bgm:
        cmd.extend(["-i", bgm_path])
        bgm_idx = input_idx

    # 构造 filter_complex
    filter_parts = []
    filter_parts.extend(filter_delays)

    # 混合全部人声
    amix_voice = "".join(filter_inputs) + f"amix=inputs={len(filter_inputs)}:normalize=0[vocal]"
    filter_parts.append(amix_voice)

    if has_bgm:
        # BGM 循环并降低音量至 22%，裁切至总时长并柔和淡出
        filter_parts.append(f"[{bgm_idx}:a]aloop=loop=-1:size=2e+09,volume=0.22,atrim=0:{total_sec:.2f}[bgm_soft]")
        filter_parts.append(f"[vocal][bgm_soft]amix=inputs=2:duration=longest:dropout_transition=0,atrim=0:{total_sec:.2f},afade=t=out:st={fade_start:.2f}:d=1.0[aout]")
        map_out = "[aout]"
    else:
        filter_parts.append(f"[vocal]apad=pad_dur={total_sec:.2f},atrim=0:{total_sec:.2f},afade=t=out:st={fade_start:.2f}:d=1.0[aout]")
        map_out = "[aout]"

    filter_complex_str = "; ".join(filter_parts)
    cmd.extend([
        "-filter_complex", filter_complex_str,
        "-map", map_out,
        "-ac", "2",
        "-ar", "44100",
        output_audio_path
    ])

    try:
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=25)
        return p.returncode == 0 and os.path.exists(output_audio_path)
    except Exception as e:
        print(f"[TriviaCompiler] 音频混流异常: {e}")
        return False


def compile_trivia_video(
    plant_data: dict[str, Any],
    output_path: str,
    use_pro: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    output_size: Optional[tuple[int, int]] = None
) -> tuple[bool, str]:
    """
    端到端编译草本趣闻短视频：
    1. 提炼 4 幕爆款脚本 (DeepSeek / 规则降级)
    2. 渲染 5 张 SlideData 画卡
    3. 合成 Edge-TTS 解说音频并计算帧停留时长
    4. 混流人声与 BGM
    5. FFmpeg 管道逐帧压制 H.264 MP4
    """
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = output_dir / "temp_trivia"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        if progress_callback:
            progress_callback(10, "正在提炼《草本趣闻》短视频脚本...")
        script = generate_trivia_script(plant_data, use_pro=use_pro)

        if progress_callback:
            progress_callback(25, "正在合成 Edge-TTS 阳光科普男声配音...")
        chunks = generate_narration_chunks(script, str(temp_dir))
        durations = [dur for _, dur in chunks]
        static_frames = compute_slide_static_frames(durations, fps=FPS, target_total_seconds=TARGET_TOTAL_SECONDS)

        if progress_callback:
            progress_callback(40, "正在渲染 1080P 白瓷药材盘与祥云卡片图层...")
        slides = render_trivia_slides(plant_data, script)

        if progress_callback:
            progress_callback(55, "正在混流人声与轻柔古风背景音乐...")
        mixed_audio_p = str(temp_dir / "mixed_audio.wav")
        bgm_p = get_default_bgm_path()
        has_audio = build_final_audio(chunks, static_frames, mixed_audio_p, bgm_p, fps=FPS)

        if progress_callback:
            progress_callback(70, "正在执行 3D 卷轴翻页与 H.264 视频压制...")

        w, h = output_size if output_size else (V_WIDTH, V_HEIGHT)
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        cmd = [
            ffmpeg_exe,
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{w}x{h}",
            "-pix_fmt", "rgb24",
            "-r", str(FPS),
            "-i", "-",
        ]

        if has_audio and os.path.exists(mixed_audio_p):
            cmd.extend([
                "-i", mixed_audio_p,
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest"
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            output_path
        ])

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

        frame_gen = generate_trivia_frames(slides, static_frames, fps=FPS, output_size=(w, h))
        for f in frame_gen:
            proc.stdin.write(f.tobytes())

        proc.stdin.close()
        stdout_data, stderr_data = proc.communicate(timeout=120)

        if proc.returncode == 0 and os.path.exists(output_path):
            if progress_callback:
                progress_callback(100, "《草本趣闻风》短视频压制完成！")
            return True, output_path
        else:
            err = stderr_data.decode("utf-8", errors="ignore") if stderr_data else "未知错误"
            return False, f"FFmpeg 压制失败: {err[-300:]}"

    except Exception as e:
        return False, f"编译异常: {e}"
    finally:
        # 清理临时目录
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
