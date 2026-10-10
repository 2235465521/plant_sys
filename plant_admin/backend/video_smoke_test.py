#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
video_smoke_test.py — Phase 1 feedback loop for /diagnosing-bugs
用法: cd backend && python video_smoke_test.py
成功 => 打印 GREEN: ... 并 exit(0)
失败 => 打印 RED: ...   并 exit(1)

测试覆盖的症状 (与用户报告的 Bug 对齐):
  1. generate_video_frames 可被 compile_collection_video 调用
  2. 合集模式至少能构建 slides 并完整跑完 generate_video_frames 生成器
  3. compile_plant_video 能接受最小化 6 张 SlideData 完成压制
"""
import sys
import os
import tempfile
from pathlib import Path

# 让 Python 能 import app.*
sys.path.insert(0, str(Path(__file__).resolve().parent))

# ── 辅助函数 ─────────────────────────────────────────────────────────────────
def green(msg: str):
    print(f"GREEN: {msg}")

def red(msg: str):
    print(f"RED:   {msg}", file=sys.stderr)

def assert_true(cond: bool, msg: str):
    if not cond:
        red(msg)
        sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: 模块可以被正确导入，generate_video_frames 存在且可调用
# ─────────────────────────────────────────────────────────────────────────────
try:
    from app.video_automation.video_compiler import (
        generate_video_frames,
        compile_plant_video,
        compile_collection_video,
    )
    green("T1: video_compiler 导入成功，三个核心函数均存在")
except ImportError as e:
    red(f"T1 FAIL — 导入失败: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: 构造最小化 SlideData 列表，验证 generate_video_frames 生成器不崩溃
# ─────────────────────────────────────────────────────────────────────────────
try:
    from PIL import Image
    from app.video_automation.frame_renderer import SlideData, V_WIDTH, V_HEIGHT

    def make_dummy_slide() -> SlideData:
        full = Image.new("RGB", (V_WIDTH, V_HEIGHT), color=(200, 180, 160))
        text = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
        photo = Image.new("RGBA", (400, 400), (100, 150, 100, 200))
        return SlideData(full_slide=full, text_canvas=text, photo_canvas=photo, photo_pos=(340, 760))

    slides_6 = [make_dummy_slide() for _ in range(6)]

    frame_count = 0
    for frame in generate_video_frames(slides_6):
        assert_true(
            frame.size == (V_WIDTH, V_HEIGHT),
            f"T2 FAIL — 帧尺寸异常: {frame.size}"
        )
        frame_count += 1

    # 6 slides × 120 帧/slide = 720 帧
    assert_true(frame_count == 720, f"T2 FAIL — 期望 720 帧，实际 {frame_count} 帧")
    green(f"T2: generate_video_frames 生成 {frame_count} 帧，全部尺寸正确")

except Exception as e:
    red(f"T2 FAIL — {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: compile_plant_video 端到端压制 (需要 ffmpeg)
# ─────────────────────────────────────────────────────────────────────────────
try:
    from app.video_automation.main_router import VideoStyleConfig

    style = VideoStyleConfig(transition_style="book_flip", bgm_type="none")
    out_path = str(Path(tempfile.gettempdir()) / "smoke_single.mp4")

    ok, msg = compile_plant_video(slides_6, out_path, plant_data=None, style=style)
    assert_true(ok, f"T3 FAIL — compile_plant_video 返回失败: {msg}")
    assert_true(os.path.exists(out_path), "T3 FAIL — 输出文件不存在")
    size_kb = os.path.getsize(out_path) // 1024
    assert_true(size_kb > 10, f"T3 FAIL — 输出文件太小 ({size_kb} KB)，可能是空文件")
    green(f"T3: compile_plant_video 成功，输出 {size_kb} KB => {out_path}")

except Exception as e:
    red(f"T3 FAIL — {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# TEST 4: compile_collection_video 端到端合集压制 (3 种虚假植物)
# ─────────────────────────────────────────────────────────────────────────────
try:
    # 模拟 get_condensed_slide_images 返回 3 张 SlideData
    # 通过 monkeypatching frame_renderer 避免真实 DB 调用
    import app.video_automation.frame_renderer as fr

    def _mock_render_title(title, subtitle):
        return make_dummy_slide()

    def _mock_render_outro(subtitle):
        return make_dummy_slide()

    def _mock_condensed(pdata, badge):
        return [make_dummy_slide(), make_dummy_slide(), make_dummy_slide()]

    def _mock_ensure_images(plant_id, vernacular_name, scientific_name, existing_server_paths, target_count):
        return existing_server_paths

    # patch
    import app.video_automation.frame_renderer as _fr_mod
    import app.video_automation.image_downloader as _dl_mod

    orig_title   = getattr(_fr_mod, "render_title_curtain_frame", None)
    orig_outro   = getattr(_fr_mod, "render_outro_curtain_frame", None)
    orig_cond    = getattr(_fr_mod, "get_condensed_slide_images", None)
    orig_ensure  = _dl_mod.ensure_enough_plant_images

    _fr_mod.render_title_curtain_frame  = _mock_render_title
    _fr_mod.render_outro_curtain_frame  = _mock_render_outro
    _fr_mod.get_condensed_slide_images  = _mock_condensed
    _dl_mod.ensure_enough_plant_images  = _mock_ensure_images

    fake_plants = [
        {"id": 1, "vernacular_name": "黄精", "scientific_name": "Polygonatum sibiricum", "image_server_paths": []},
        {"id": 2, "vernacular_name": "白前", "scientific_name": "Cynanchum stauntonii", "image_server_paths": []},
        {"id": 3, "vernacular_name": "明党参", "scientific_name": "Changium smyrnioides", "image_server_paths": []},
    ]

    out_path_col = str(Path(tempfile.gettempdir()) / "smoke_collection.mp4")
    progress_log: list[str] = []

    def on_progress(pct: int, msg: str):
        progress_log.append(f"{pct}% {msg}")

    ok2, msg2 = compile_collection_video(
        topic_title="十大中药植物",
        plants_data_list=fake_plants,
        output_path=out_path_col,
        style=style,
        progress_callback=on_progress,
    )

    # 还原 patch
    _fr_mod.render_title_curtain_frame  = orig_title
    _fr_mod.render_outro_curtain_frame  = orig_outro
    _fr_mod.get_condensed_slide_images  = orig_cond
    _dl_mod.ensure_enough_plant_images  = orig_ensure

    assert_true(ok2, f"T4 FAIL — compile_collection_video 返回失败: {msg2}")
    assert_true(os.path.exists(out_path_col), "T4 FAIL — 合集输出文件不存在")
    size_kb2 = os.path.getsize(out_path_col) // 1024
    assert_true(size_kb2 > 10, f"T4 FAIL — 合集文件太小 ({size_kb2} KB)")
    green(f"T4: compile_collection_video 成功，进度回调 {len(progress_log)} 次，输出 {size_kb2} KB => {out_path_col}")
    for entry in progress_log[-5:]:
        print(f"     进度日志: {entry}")

except Exception as e:
    red(f"T4 FAIL — {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
print("\n========================================")
print("ALL GREEN — 视频模块全部 4 项冒烟测试通过")
print("========================================")
sys.exit(0)
