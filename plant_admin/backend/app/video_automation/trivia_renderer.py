# -*- coding: utf-8 -*-
"""
trivia_renderer.py - 草本趣闻短视频画面渲染模块 (Modern Trivia Style Renderer)
100% 像素级对标《老王聊草本》样片：
- 冷白天蓝光斑背景 (1080x1920)
- 顶部双侧如意祥云托底艺术标牌（暖橙金立体渐变 + 深褐描边）
- 封面白瓷花瓣药材盘容器 + 拼音光晕 + 透视星轨光环
- 高清 1000x660 圆角内容卡片
- 醒目亮黄色（#FFEE11）+ 4px深黑褐描边圆润爆款短视频字体
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from app.video_automation.frame_renderer import SlideData, V_WIDTH, V_HEIGHT, get_system_font
from app.video_automation.trivia_script import TriviaScript, generate_trivia_script

TRIVIA_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "video_assets" / "trivia"
FONTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "video_assets" / "fonts"


def load_trivia_bg() -> Image.Image:
    """加载 1080x1920 冷白天蓝光斑画布，若不存在则动态回退生成"""
    bg_p = TRIVIA_ASSETS_DIR / "trivia_bg.png"
    if bg_p.exists():
        try:
            return Image.open(str(bg_p)).convert("RGBA")
        except Exception:
            pass
    return Image.new("RGBA", (V_WIDTH, V_HEIGHT), (235, 242, 250, 255))


def get_banner_font(size: int) -> ImageFont.FreeTypeFont:
    """
    获取大标题艺术字体（华文琥珀 > 幼圆 > 仓库自带2.ttf > 微软雅黑粗体 > Linux CJK > 1.ttf）。
    确保在 Linux/Windows 生产服务器上绝不回退到默认位图字体产生豆腐块乱码！
    """
    f_2 = FONTS_DIR / "2.ttf"
    f_1 = FONTS_DIR / "1.ttf"
    candidates = [
        "C:\\Windows\\Fonts\\STHUPO.TTF",
        "C:\\Windows\\Fonts\\SIMYOU.TTF",
        str(f_2.resolve()) if f_2.exists() else "",
        "C:\\Windows\\Fonts\\msyhbd.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
        str(f_1.resolve()) if f_1.exists() else "",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return get_system_font(size, bold=True)


def get_body_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """
    获取正文爆款字体（幼圆 > 微软雅黑粗体 > 仓库自带1.ttf > 2.ttf > Linux CJK）。
    """
    f_1 = FONTS_DIR / "1.ttf"
    f_2 = FONTS_DIR / "2.ttf"
    candidates = [
        "C:\\Windows\\Fonts\\SIMYOU.TTF",
        "C:\\Windows\\Fonts\\msyhbd.ttc" if bold else "C:\\Windows\\Fonts\\msyh.ttc",
        str(f_1.resolve()) if f_1.exists() else "",
        str(f_2.resolve()) if f_2.exists() else "",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return get_system_font(size, bold=bold)


def get_latin_pinyin_font(size: int) -> ImageFont.FreeTypeFont:
    """获取带调号拼音字体（Arial / Segoe UI / 微软雅黑 / Linux DejaVu / 正文字体）"""
    candidates = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\msyh.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return get_body_font(size, bold=False)


def draw_text_with_outline(
    draw: ImageDraw.ImageDraw,
    pos: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    outline_color: tuple[int, int, int] = (45, 30, 10),
    outline_width: int = 4,
    anchor: str = "mm"
):
    """高质量描边文字渲染器"""
    x, y = pos
    if outline_width > 0:
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx * dx + dy * dy <= outline_width * outline_width:
                    draw.text((x + dx, y + dy), text, fill=outline_color, font=font, anchor=anchor)
    draw.text((x, y), text, fill=fill, font=font, anchor=anchor)


def draw_cloud_banner(
    canvas: Image.Image,
    title: str,
    y_pos: int = 180,
    font_size: int = 86
):
    """
    绘制顶部对称如意祥云抱字标牌：
    左祥云 + 暖金橙字深褐边 + 右祥云
    """
    draw = ImageDraw.Draw(canvas)
    f_title = get_banner_font(font_size)
    text_w = f_title.getlength(title)
    cx = V_WIDTH // 2

    # 加载祥云
    cloud_l_p = TRIVIA_ASSETS_DIR / "cloud_left.png"
    cloud_r_p = TRIVIA_ASSETS_DIR / "cloud_right.png"

    cloud_w, cloud_h = 110, 82
    if cloud_l_p.exists() and cloud_r_p.exists():
        try:
            cl = Image.open(str(cloud_l_p)).convert("RGBA").resize((cloud_w, cloud_h), Image.Resampling.LANCZOS)
            cr = Image.open(str(cloud_r_p)).convert("RGBA").resize((cloud_w, cloud_h), Image.Resampling.LANCZOS)

            lx = int(cx - text_w / 2 - cloud_w - 15)
            rx = int(cx + text_w / 2 + 15)
            cy = int(y_pos - cloud_h / 2)

            canvas.paste(cl, (lx, cy), cl)
            canvas.paste(cr, (rx, cy), cr)
        except Exception:
            pass

    # 文字阴影与暖橙金立体描边
    draw_text_with_outline(
        draw,
        (cx, y_pos),
        title,
        f_title,
        fill=(255, 215, 120),            # 暖金橙填色
        outline_color=(125, 65, 15),     # 深褐轮廓边
        outline_width=5,
        anchor="mm"
    )


NO_LINE_START_CHARS = set("，。、；：？！）》’”」』·")


def wrap_text_cjk(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """中文自然排版折行算法，严格遵循避头尾法则 (Kinsoku Shori)"""
    if not text:
        return []
    lines: list[str] = []
    curr = ""
    for ch in text:
        w = font.getlength(curr + ch)
        if w <= max_width:
            curr += ch
        else:
            # 避头尾：如果当前字符不可置于行首，强制挂在当前行尾
            if ch in NO_LINE_START_CHARS:
                curr += ch
                lines.append(curr)
                curr = ""
            else:
                if curr:
                    lines.append(curr)
                curr = ch
    if curr:
        lines.append(curr)
    return lines


def create_dish_card(image_path: str, size: int = 640) -> tuple[Image.Image, tuple[int, int]]:
    """
    封面白瓷药材盘卡片：
    - 智能裁切/载入图片
    - 叠加白瓷花瓣盘与深度立体投影
    """
    card = Image.new("RGBA", (size + 40, size + 40), (0, 0, 0, 0))
    pos = (V_WIDTH // 2 - (size + 40) // 2, 360)

    # 若图片存在，圆形入盘
    img = None
    if image_path and os.path.exists(image_path):
        try:
            raw = Image.open(image_path).convert("RGBA")
            rw, rh = raw.size
            scale = max(size / rw, size / rh)
            nw, nh = int(rw * scale), int(rh * scale)
            resized = raw.resize((nw, nh), Image.Resampling.LANCZOS)
            x_c = (nw - size) // 2
            y_c = (nh - size) // 2
            img = resized.crop((x_c, y_c, x_c + size, y_c + size))
        except Exception:
            img = None

    if img is None:
        img = Image.new("RGBA", (size, size), (220, 230, 240, 255))

    # 绘制外层白瓷光圈和阴影
    mask = Image.new("L", (size, size), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.ellipse((0, 0, size, size), fill=255)

    # 盘底柔和立体投影
    shadow = Image.new("RGBA", (size + 40, size + 40), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.ellipse((20, 26, size + 20, size + 26), fill=(60, 90, 130, 60))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    card.paste(shadow, (0, 0), shadow)

    # 贴入主体
    inner_dish = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner_dish.paste(img, (0, 0), mask)

    # 叠加白瓷边缘双高光
    d_draw = ImageDraw.Draw(inner_dish)
    d_draw.ellipse((0, 0, size, size), outline=(255, 255, 255, 240), width=8)
    d_draw.ellipse((4, 4, size - 4, size - 4), outline=(230, 240, 250, 180), width=4)

    card.paste(inner_dish, (20, 20), inner_dish)
    return card, pos


def create_photo_card(
    image_path: str,
    w: int = 1000,
    h: int = 660,
    corner_radius: int = 24
) -> tuple[Image.Image, tuple[int, int]]:
    """
    内容页高清 1000x660 圆角照片卡片：
    - 精致微圆角裁切
    - 2px 极细白边与下沉软阴影
    """
    pad = 30
    card_w, card_h = w + pad * 2, h + pad * 2
    pos = (V_WIDTH // 2 - card_w // 2, 280)

    canvas = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))

    img = None
    if image_path and os.path.exists(image_path):
        try:
            raw = Image.open(image_path).convert("RGBA")
            rw, rh = raw.size
            scale = max(w / rw, h / rh)
            nw, nh = int(rw * scale), int(rh * scale)
            resized = raw.resize((nw, nh), Image.Resampling.LANCZOS)
            x_c = (nw - w) // 2
            y_c = (nh - h) // 2
            img = resized.crop((x_c, y_c, x_c + w, y_c + h))
        except Exception:
            img = None

    if img is None:
        img = Image.new("RGBA", (w, h), (210, 225, 240, 255))

    # 圆角蒙版
    mask = Image.new("L", (w, h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle((0, 0, w, h), radius=corner_radius, fill=255)

    # 软阴影
    shadow = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rounded_rectangle(
        (pad, pad + 10, pad + w, pad + h + 10),
        radius=corner_radius,
        fill=(50, 75, 110, 50)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    canvas.paste(shadow, (0, 0), shadow)

    # 贴图
    photo_cropped = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    photo_cropped.paste(img, (0, 0), mask)

    # 白框描边
    p_draw = ImageDraw.Draw(photo_cropped)
    p_draw.rounded_rectangle((0, 0, w, h), radius=corner_radius, outline=(255, 255, 255, 230), width=4)

    canvas.paste(photo_cropped, (pad, pad), photo_cropped)
    return canvas, pos


def resolve_plant_images(plant_data: dict[str, Any]) -> list[str]:
    """解析并返回可用的本地植物照片物理路径"""
    paths = plant_data.get("image_server_paths") or []
    base_dir = Path(__file__).resolve().parent.parent.parent
    valid_paths: list[str] = []

    for p in paths:
        clean = str(p).strip().replace("\\", "/")
        if os.path.exists(clean):
            valid_paths.append(clean)
            continue
        if "/plants/" in clean:
            sub = clean.split("/plants/")[-1]
            cand = base_dir / "data" / "plant_images" / sub
            if cand.exists():
                valid_paths.append(str(cand.resolve()))
                continue
        fname = Path(clean).name
        if fname:
            for found in (base_dir / "data" / "plant_images").rglob(fname):
                if found.exists():
                    valid_paths.append(str(found.resolve()))
                    break

    # 特殊容错：如果是天葵且无图，自动链接已提取的 5 张高质量样本图
    name = str(plant_data.get("vernacular_name") or "")
    if "天葵" in name:
        tiankui_dir = base_dir / "data" / "plant_images" / "tiankui"
        if tiankui_dir.exists():
            for fname in ["dish.png", "flower.png", "fruit.png", "leaf.png", "full.png"]:
                fp = tiankui_dir / fname
                if fp.exists() and str(fp.resolve()) not in valid_paths:
                    valid_paths.append(str(fp.resolve()))

    return valid_paths


def render_trivia_slides(
    plant_data: dict[str, Any],
    script: TriviaScript
) -> list[SlideData]:
    """
    根据草本趣闻脚本生成全部 5 张 SlideData：
    Slide 1: 封面概述（每日认识一种植物 + 药用盘装图 + 拼音大字 + 星轨科属）
    Slide 2: 形态特征（花朵高清图 + 爆款黄字黑边）
    Slide 3: 植物趣闻（果实特写 + 趣闻物候故事）
    Slide 4: 适生范围（生境高清图 + 耐阴土壤分布）
    Slide 5: 美图收尾（全屏大景深写真赏析）
    """
    slides: list[SlideData] = []
    bg = load_trivia_bg()
    local_images = resolve_plant_images(plant_data)

    def get_img(idx: int) -> str:
        if not local_images:
            return ""
        return local_images[idx % len(local_images)]

    # ------------------ SLIDE 1: 封面 ------------------
    tc1 = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
    # 顶部标牌
    draw_cloud_banner(tc1, "每日认识一种植物", y_pos=180, font_size=82)

    # 副标（黄色黑边）
    s1_draw = ImageDraw.Draw(tc1)
    f_sub = get_body_font(60, bold=True)
    badge_text = f"（ {script.cover_badge} ）"
    draw_text_with_outline(
        s1_draw, (V_WIDTH // 2, 290), badge_text, f_sub,
        fill=(255, 235, 40), outline_color=(70, 45, 10), outline_width=4, anchor="mm"
    )

    # 药材白瓷盘
    pc1, pos1 = create_dish_card(get_img(0), size=620)

    # 拼音（白字带粉红光晕）
    f_py = get_latin_pinyin_font(62)
    py_x, py_y = V_WIDTH // 2, 1070
    for dx in range(-4, 5):
        for dy in range(-4, 5):
            if dx * dx + dy * dy <= 16:
                s1_draw.text((py_x + dx, py_y + dy), script.pinyin, fill=(255, 90, 110, 140), font=f_py, anchor="mm")
    s1_draw.text((py_x, py_y), script.pinyin, fill=(255, 255, 255), font=f_py, anchor="mm")

    # 植物中文大名（粗体大红带白描边与红晕）
    f_name_size = 128
    f_name = get_banner_font(f_name_size)
    while f_name.getlength(script.plant_name) > 860 and f_name_size > 64:
        f_name_size -= 8
        f_name = get_banner_font(f_name_size)
    name_x, name_y = V_WIDTH // 2, 1200
    for dx in range(-6, 7):
        for dy in range(-6, 7):
            if dx * dx + dy * dy <= 36:
                s1_draw.text((name_x + dx, name_y + dy), script.plant_name, fill=(240, 50, 70, 120), font=f_name, anchor="mm")
    draw_text_with_outline(
        s1_draw, (name_x, name_y), script.plant_name, f_name,
        fill=(235, 45, 55), outline_color=(255, 255, 255), outline_width=5, anchor="mm"
    )

    # 透视星轨环
    orbit_p = TRIVIA_ASSETS_DIR / "orbit_ring.png"
    if orbit_p.exists():
        try:
            orbit = Image.open(str(orbit_p)).convert("RGBA")
            tc1.paste(orbit, (V_WIDTH // 2 - orbit.width // 2, 1340), orbit)
        except Exception:
            pass

    # 别名与科属（爆款亮黄黑描边）
    import re
    clean_aliases = re.sub(r"\(.*?\)|（.*?）", "", script.aliases).strip()
    clean_aliases = re.sub(r"[、,，\s]+", "、", clean_aliases).strip("、")
    if len(clean_aliases) > 18:
        clean_aliases = clean_aliases[:18] + "…"

    f_meta = get_body_font(52, bold=True)
    draw_text_with_outline(
        s1_draw, (V_WIDTH // 2, 1410), f"别名：{clean_aliases}", f_meta,
        fill=(255, 240, 30), outline_color=(35, 25, 10), outline_width=4, anchor="mm"
    )
    draw_text_with_outline(
        s1_draw, (V_WIDTH // 2, 1495), f"科属：{script.family_genus}", f_meta,
        fill=(255, 240, 30), outline_color=(35, 25, 10), outline_width=4, anchor="mm"
    )

    fs1 = bg.copy()
    fs1.paste(tc1, (0, 0), tc1)
    fs1.paste(pc1, pos1, pc1)
    slides.append(SlideData(fs1.convert("RGB"), tc1, pc1, pos1))

    # ------------------ 通用内容 Slide 构造器 ------------------
    def _build_content_slide(title: str, text: str, img_idx: int):
        tc = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
        draw_cloud_banner(tc, title, y_pos=180, font_size=86)

        # 正文排版：针对 50~75 字多行图文卡片智能动态字号与行距
        f_size = 48
        f_content = get_body_font(f_size, bold=True)
        wrapped_lines = wrap_text_cjk(text, f_content, max_width=920)

        if len(wrapped_lines) > 4:
            f_size = 44
            f_content = get_body_font(f_size, bold=True)
            wrapped_lines = wrap_text_cjk(text, f_content, max_width=920)
            line_height = 70
        elif len(wrapped_lines) <= 2:
            f_size = 52
            f_content = get_body_font(f_size, bold=True)
            wrapped_lines = wrap_text_cjk(text, f_content, max_width=920)
            line_height = 80
        else:
            line_height = 74

        draw_c = ImageDraw.Draw(tc)
        y_text = 1060

        for line in wrapped_lines:
            draw_text_with_outline(
                draw_c, (90, y_text), line, f_content,
                fill=(255, 238, 20), outline_color=(30, 20, 10), outline_width=4, anchor="la"
            )
            y_text += line_height

        pc, pos = create_photo_card(get_img(img_idx), w=1000, h=660)
        fs = bg.copy()
        fs.paste(tc, (0, 0), tc)
        fs.paste(pc, pos, pc)
        slides.append(SlideData(fs.convert("RGB"), tc, pc, pos))

    # SLIDE 2: 形态特征
    _build_content_slide(script.morphology_title, script.morphology_text, 1)

    # SLIDE 3: 植物趣闻
    _build_content_slide(script.trivia_title, script.trivia_text, 2)

    # SLIDE 4: 适生范围
    _build_content_slide(script.habitat_title, script.habitat_text, 3)

    # ------------------ SLIDE 5: 全屏美图收尾 ------------------
    tc5 = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
    d5 = ImageDraw.Draw(tc5)
    
    left_str = f"《{script.plant_name}》"
    right_str = "草木有灵"
    gap_str = "    "
    full_str = f"{left_str}{gap_str}{right_str}"

    f_end_size = 92
    f_end = get_banner_font(f_end_size)
    # 动态防溢出：确保标题不超出 960px 宽度
    while f_end.getlength(full_str) > 960 and f_end_size > 48:
        f_end_size -= 4
        f_end = get_banner_font(f_end_size)

    # 精确计算水平居中及中间黄金圆点坐标（避免任何字体缺少·字符导致方块乱码）
    w_left = f_end.getlength(left_str)
    w_gap = f_end.getlength(gap_str)
    w_right = f_end.getlength(right_str)
    total_w = w_left + w_gap + w_right
    start_x = (V_WIDTH - total_w) / 2
    y_pos = 1720

    # 绘制左《植物名》
    draw_text_with_outline(
        d5, (int(start_x + w_left / 2), y_pos), left_str, f_end,
        fill=(255, 235, 50), outline_color=(50, 30, 10), outline_width=5, anchor="mm"
    )
    # 绘制中间精致立体金点
    dot_x = int(start_x + w_left + w_gap / 2)
    dot_r = max(5, int(f_end_size * 0.08))
    d5.ellipse(
        (dot_x - dot_r - 4, y_pos - dot_r - 4, dot_x + dot_r + 4, y_pos + dot_r + 4),
        fill=(50, 30, 10)
    )
    d5.ellipse(
        (dot_x - dot_r, y_pos - dot_r, dot_x + dot_r, y_pos + dot_r),
        fill=(255, 235, 50)
    )
    # 绘制右 草木有灵
    draw_text_with_outline(
        d5, (int(start_x + w_left + w_gap + w_right / 2), y_pos), right_str, f_end,
        fill=(255, 235, 50), outline_color=(50, 30, 10), outline_width=5, anchor="mm"
    )

    pc5, pos5 = create_photo_card(get_img(4), w=1020, h=1300, corner_radius=28)
    # 将收尾大图稍微上移居中
    pos5 = (pos5[0], 240)

    fs5 = bg.copy()
    fs5.paste(tc5, (0, 0), tc5)
    fs5.paste(pc5, pos5, pc5)
    slides.append(SlideData(fs5.convert("RGB"), tc5, pc5, pos5))

    return slides
