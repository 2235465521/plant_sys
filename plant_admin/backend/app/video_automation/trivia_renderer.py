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
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter, ImageEnhance

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


def get_calligraphy_font(size: int) -> ImageFont.FreeTypeFont:
    """
    获取样片正文字体（华文琥珀 > 幼圆 > 微软雅黑粗体 > 仓库字体）。
    《天.MOV》正文是粗圆琥珀体加右倾，不是毛笔行楷。
    """
    f_2 = FONTS_DIR / "2.ttf"
    f_1 = FONTS_DIR / "1.ttf"
    candidates = [
        "C:\\Windows\\Fonts\\STHUPO.TTF",
        "C:\\Windows\\Fonts\\SIMYOU.TTF",
        str(f_2.resolve()) if f_2.exists() else "",
        "C:\\Windows\\Fonts\\msyhbd.ttc",
        "C:\\Windows\\Fonts\\STXINGKA.TTF",
        "C:\\Windows\\Fonts\\STKAITI.TTF",
        "C:\\Windows\\Fonts\\SIMKAI.TTF",
        str(f_1.resolve()) if f_1.exists() else "",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return get_system_font(size, bold=True)


def get_cjk_fallback_font(size: int) -> ImageFont.FreeTypeFont:
    """
    获取植物学罕见字降级保底字体（如 蓇、葖、蒴 等字符）。
    使用覆盖字符集完备的华文楷体、楷体或微软雅黑。
    """
    candidates = [
        "C:\\Windows\\Fonts\\msyhbd.ttc",
        "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf",
        "C:\\Windows\\Fonts\\STKAITI.TTF",
        "C:\\Windows\\Fonts\\SIMKAI.TTF",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return get_system_font(size, bold=True)


def render_slanted_line(
    text: str,
    primary_font: ImageFont.FreeTypeFont,
    fallback_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int] = (255, 238, 20),
    outline_color: tuple[int, int, int] = (20, 15, 5),
    outline_width: int = 4,
    shear: float = -0.18,
    typography: Optional[Any] = None
) -> Image.Image:
    """
    渲染带字符级生僻字回退、深黑描边与倾斜仿射变换的单行文字图层。
    可直接使用 TypographyStyle 或独立参数。
    """
    if typography is not None:
        fill = typography.fill_rgb
        outline_color = typography.outline_rgb
        outline_width = typography.outline_width
        shear = typography.shear_factor
    chars_info = []
    total_w = 0.0
    max_h = 30
    for ch in text:
        mask_h = primary_font.getmask(ch).size[1]
        use_font = primary_font if mask_h > 0 else fallback_font
        ch_w = use_font.getlength(ch)
        chars_info.append((ch, use_font, ch_w))
        total_w += ch_w
        box = use_font.getbbox(ch)
        if box:
            max_h = max(max_h, box[3] - box[1])

    pad_w = outline_width * 4 + 40
    pad_h = outline_width * 4 + 30
    total_w_int = int(total_w) + pad_w
    total_h_int = max_h + pad_h
    layer = Image.new("RGBA", (total_w_int, total_h_int), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    curr_x = 20.0
    y_off = 10

    for ch, use_font, ch_w in chars_info:
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx * dx + dy * dy <= outline_width * outline_width:
                    d.text((curr_x + dx, y_off + dy), ch, fill=outline_color, font=use_font)
        d.text((curr_x, y_off), ch, fill=fill, font=use_font)
        curr_x += ch_w

    m = (1, shear, -shear * (total_h_int / 2), 0, 1, 0)
    extra_w = int(abs(shear) * total_h_int) + 20
    slanted = layer.transform((total_w_int + extra_w, total_h_int), Image.Transform.AFFINE, m, Image.Resampling.BILINEAR)
    return slanted


def get_body_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """
    获取正文字体（优先华文行楷 > 幼圆 > 微软雅黑粗体 > 仓库自带1.ttf > 2.ttf > Linux CJK）。
    """
    return get_calligraphy_font(size)


def get_latin_pinyin_font(size: int) -> ImageFont.FreeTypeFont:
    """获取带调号拼音字体（Arial / Segoe UI / 微软雅黑 / Linux DejaVu / 正文字体）"""
    candidates = [
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\msyhbd.ttc",
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
    return get_system_font(size, bold=False)


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


def _knockout_studio_backdrop(raw: Image.Image) -> Optional[Image.Image]:
    """
    药材盘成品图通常铺在浅色棚拍底上。四角颜色接近时，抠掉棚拍底，保留白瓷花瓣盘。
    普通风景/花朵照片四角不一致，返回 None，交给圆形入盘。
    """
    rgb = raw.convert("RGB")
    w, h = rgb.size
    if w < 8 or h < 8:
        return None
    samples = [rgb.getpixel(p) for p in ((1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2))]
    spread = 0
    for i in range(4):
        for j in range(i + 1, 4):
            spread = max(spread, max(abs(samples[i][c] - samples[j][c]) for c in range(3)))
    if spread > 22:
        return None
    bg = tuple(sum(s[c] for s in samples) // 4 for c in range(3))
    if sum(bg) / 3 < 165:
        return None
    diff = ImageChops.difference(rgb, Image.new("RGB", (w, h), bg)).convert("L")
    alpha = diff.point(lambda p: 0 if p < 16 else (255 if p > 38 else int((p - 16) * 255 / 22)))
    bbox = alpha.getbbox()
    if not bbox:
        return None
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if bw < w * 0.35 or bh < h * 0.35:
        return None
    out = raw.convert("RGBA")
    out.putalpha(alpha)
    return out.crop(bbox)


def create_dish_card(image_path: str, size: int = 680) -> tuple[Image.Image, tuple[int, int]]:
    """
    封面药材盘：
    - 棚拍白瓷花瓣盘：抠掉浅底，完整保留花瓣边缘
    - 普通照片：圆形入盘并加白瓷高光边
    卡片中心落在画布 y=690，和样片药材盘重心对齐。
    """
    cutout = None
    photo = None
    if image_path and os.path.exists(image_path):
        try:
            raw = Image.open(image_path).convert("RGBA")
            cutout = _knockout_studio_backdrop(raw)
            if cutout is None:
                photo = raw
        except Exception:
            cutout = None
            photo = None

    if cutout is not None:
        cw, ch = cutout.size
        scale = size / max(cw, ch)
        cutout = cutout.resize((max(1, int(cw * scale)), max(1, int(ch * scale))), Image.Resampling.LANCZOS)
        subject = cutout
    else:
        if photo is None:
            photo = Image.new("RGBA", (size, size), (220, 230, 240, 255))
        rw, rh = photo.size
        scale = max(size / rw, size / rh)
        nw, nh = int(rw * scale), int(rh * scale)
        resized = photo.resize((nw, nh), Image.Resampling.LANCZOS)
        x_c = (nw - size) // 2
        y_c = (nh - size) // 2
        img = resized.crop((x_c, y_c, x_c + size, y_c + size))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        subject = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        subject.paste(img, (0, 0), mask)
        rim = ImageDraw.Draw(subject)
        rim.ellipse((2, 2, size - 3, size - 3), outline=(255, 255, 255, 235), width=8)

    sw, sh = subject.size
    pad = 48
    card = Image.new("RGBA", (sw + pad * 2, sh + pad * 2), (0, 0, 0, 0))
    shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.ellipse((pad + 18, sh // 2 + 10, sw + pad - 18, sh + pad + 6), fill=(60, 90, 130, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    card.paste(shadow, (0, 0), shadow)
    card.paste(subject, (pad, pad // 3), subject)
    center_y = 690
    pos = (V_WIDTH // 2 - card.width // 2, center_y - (pad // 3 + sh // 2))
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


def create_fullbleed_hero_photo(
    image_path: str,
    w: int = 1080,
    h: int = 900
) -> tuple[Image.Image, tuple[int, int]]:
    """
    内容页通栏 1080x900 植物主画幅（对标《天.MOV》样片像素级坐标）：
    - 满幅横向 1080px 通栏铺满，无白框、无圆角、无悬浮投影
    - y 坐标固定为 310，精准贴合顶部标牌与底部解说栏分割线
    """
    pos = (0, 310)
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

    return img, pos


def create_fullscreen_photo(
    image_path: str,
    w: int = 1080,
    h: int = 1920
) -> Image.Image:
    """
    尾幕 1080x1920 全屏植物摄影收尾画幅（对标《天.MOV》样片 17s~20s 纯净唯美收尾）：
    - 底层：同图自适应高斯模糊 (radius=35) 虚化铺底
    - 中层：保持宽高比居中高清特写大图展示
    - 绝无多余文字遮挡，提供纯净视听享受
    """
    if not image_path or not os.path.exists(image_path):
        return Image.new("RGBA", (w, h), (40, 60, 40, 255))
    try:
        raw = Image.open(image_path).convert("RGBA")
        rw, rh = raw.size

        # 底层虚化铺底
        bg_scale = max(w / rw, h / rh)
        bg_w, bg_h = int(rw * bg_scale), int(rh * bg_scale)
        bg_img = raw.resize((bg_w, bg_h), Image.Resampling.LANCZOS)
        bg_crop = bg_img.crop(((bg_w - w) // 2, (bg_h - h) // 2, (bg_w - w) // 2 + w, (bg_h - h) // 2 + h))
        bg_blur = bg_crop.filter(ImageFilter.GaussianBlur(35))
        enhancer = ImageEnhance.Brightness(bg_blur.convert("RGB"))
        bg_final = enhancer.enhance(0.9).convert("RGBA")

        # 前景清晰居中（适配 1080 宽度）
        fg_scale = w / rw
        fg_w, fg_h = w, int(rh * fg_scale)
        fg_img = raw.resize((fg_w, fg_h), Image.Resampling.LANCZOS)
        fg_y = (h - fg_h) // 2
        bg_final.paste(fg_img, (0, fg_y), fg_img)
        return bg_final
    except Exception:
        return Image.new("RGBA", (w, h), (40, 60, 40, 255))


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


def _blank_canvas() -> Image.Image:
    return Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))


def _paste_at_center_y(canvas: Image.Image, img: Image.Image, cy: float) -> None:
    canvas.paste(img, ((V_WIDTH - img.width) // 2, int(cy - img.height / 2)), img)


def _load_tilted_orbit(width: int = 980, tilt: float = -13, center_y: int = 1420) -> Image.Image:
    """加载样片那圈倾斜的蓝色星轨，失败时返回空图层。"""
    orbit_p = TRIVIA_ASSETS_DIR / "orbit_ring.png"
    layer = _blank_canvas()
    if not orbit_p.exists():
        return layer
    try:
        orbit = Image.open(str(orbit_p)).convert("RGBA")
        ow, oh = orbit.size
        nh = max(1, int(oh * (width / float(ow))))
        orbit = orbit.resize((width, nh), Image.Resampling.LANCZOS)
        orbit = orbit.rotate(tilt, expand=True, resample=Image.Resampling.BICUBIC)
        _paste_at_center_y(layer, orbit, center_y)
    except Exception:
        return layer
    return layer


def _bind_motion(slide: SlideData, kind: str, layers: dict[str, Image.Image]) -> SlideData:
    slide.kind = kind
    slide.layers = layers
    return slide


def render_trivia_slides(
    plant_data: dict[str, Any],
    script: TriviaScript,
    typography: Optional[Any] = None
) -> list[SlideData]:
    """
    根据草本趣闻脚本生成全部 5 张 SlideData。
    每张片子拆成可独立淡入的图层，供编译器按《天.MOV》的节奏做入场、放大和收尾推近。
    同时仍输出一张定格合成图，方便预览和测试。
    """
    if typography is None:
        from app.video_automation.typography import TypographyStyle
        typography = TypographyStyle.preset_benchmark_tian()

    slides: list[SlideData] = []
    bg = load_trivia_bg()
    local_images = resolve_plant_images(plant_data)

    def get_img(idx: int) -> str:
        if not local_images:
            return ""
        return local_images[idx % len(local_images)]

    # ------------------ SLIDE 1: 封面（分层，方便药材盘放大和文字先后入场） ------------------
    title_l = _blank_canvas()
    draw_cloud_banner(title_l, "每日认识一种植物", y_pos=148, font_size=74)

    badge_l = _blank_canvas()
    badge_draw = ImageDraw.Draw(badge_l)
    f_sub = get_banner_font(52)
    badge_text = f"（ {script.cover_badge} ）"
    draw_text_with_outline(
        badge_draw, (V_WIDTH // 2, 276), badge_text, f_sub,
        fill=(236, 196, 122), outline_color=(118, 68, 18), outline_width=4, anchor="mm"
    )

    pc1, pos1 = create_dish_card(get_img(0), size=680)

    pinyin_l = _blank_canvas()
    py_draw = ImageDraw.Draw(pinyin_l)
    f_py = get_latin_pinyin_font(54)
    py_x, py_y = V_WIDTH // 2, 1180
    for dx in range(-7, 8):
        for dy in range(-7, 8):
            if dx * dx + dy * dy <= 49:
                py_draw.text((py_x + dx, py_y + dy), script.pinyin, fill=(220, 60, 75, 140), font=f_py, anchor="mm")
    draw_text_with_outline(
        py_draw, (py_x, py_y), script.pinyin, f_py,
        fill=(255, 255, 255), outline_color=(190, 55, 68), outline_width=2, anchor="mm"
    )

    f_name_size = 108
    f_name = get_calligraphy_font(f_name_size)
    while f_name.getlength(script.plant_name) > 760 and f_name_size > 64:
        f_name_size -= 6
        f_name = get_calligraphy_font(f_name_size)
    name_box = f_name.getbbox(script.plant_name)
    nw = (name_box[2] - name_box[0]) if name_box else 300
    nh = (name_box[3] - name_box[1]) if name_box else 120
    pad_box = 90
    name_chip = Image.new("RGBA", (nw + pad_box, nh + pad_box), (0, 0, 0, 0))
    nd = ImageDraw.Draw(name_chip)
    cx_n, cy_n = (nw + pad_box) // 2, (nh + pad_box) // 2
    for dx in range(-8, 9):
        for dy in range(-8, 9):
            if dx * dx + dy * dy <= 64:
                nd.text((cx_n + dx, cy_n + dy), script.plant_name, fill=(210, 40, 55, 150), font=f_name, anchor="mm")
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            if dx * dx + dy * dy <= 9:
                nd.text((cx_n + dx, cy_n + dy), script.plant_name, fill=(255, 255, 255), font=f_name, anchor="mm")
    nd.text((cx_n, cy_n), script.plant_name, fill=(198, 72, 86), font=f_name, anchor="mm")
    shear_n = -0.12
    m_name = (1, shear_n, -shear_n * ((nh + pad_box) / 2), 0, 1, 0)
    slanted_name = name_chip.transform(
        (nw + pad_box + 50, nh + pad_box), Image.Transform.AFFINE, m_name, Image.Resampling.BILINEAR
    )
    name_l = _blank_canvas()
    _paste_at_center_y(name_l, slanted_name, 1324)

    orbit_cover_shifted = _load_tilted_orbit(width=1180, tilt=-14, center_y=1395)

    import re
    clean_aliases = re.sub(r"\(.*?\)|（.*?）", "", script.aliases).strip()
    clean_aliases = re.sub(r"[、,，\s]+", "、", clean_aliases).strip("、")
    if len(clean_aliases) > 18:
        clean_aliases = clean_aliases[:18] + "…"

    f_meta, f_fb = typography.resolve_fonts(48)

    def render_meta_line(label: str, val: str) -> Image.Image:
        l_chars = [(ch, f_meta if f_meta.getmask(ch).size[1] > 0 else f_fb, (255, 255, 255)) for ch in label]
        v_chars = [(ch, f_meta if f_meta.getmask(ch).size[1] > 0 else f_fb, typography.fill_rgb) for ch in val]
        all_chars = l_chars + v_chars
        tot_w = sum(f.getlength(ch) for ch, f, _ in all_chars)
        tot_w_int = int(tot_w) + 60
        tot_h_int = 78
        lay = Image.new("RGBA", (tot_w_int, tot_h_int), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        curr_x = 20.0
        y_off = 10
        ow = typography.outline_width
        for ch, f, col in all_chars:
            for dx in range(-ow, ow + 1):
                for dy in range(-ow, ow + 1):
                    if dx * dx + dy * dy <= ow * ow:
                        ld.text((curr_x + dx, y_off + dy), ch, fill=typography.outline_rgb, font=f)
            ld.text((curr_x, y_off), ch, fill=col, font=f)
            curr_x += f.getlength(ch)
        m = (1, typography.shear_factor, -typography.shear_factor * (tot_h_int / 2), 0, 1, 0)
        return lay.transform((tot_w_int + 30, tot_h_int), Image.Transform.AFFINE, m, Image.Resampling.BILINEAR)

    meta_l = _blank_canvas()
    _paste_at_center_y(meta_l, render_meta_line("别名：", clean_aliases), 1466)
    _paste_at_center_y(meta_l, render_meta_line("科属：", script.family_genus), 1556)

    text_cover = _blank_canvas()
    for layer in (title_l, badge_l, orbit_cover_shifted, pinyin_l, name_l, meta_l):
        text_cover.paste(layer, (0, 0), layer)
    fs1 = bg.copy()
    fs1.paste(pc1, pos1, pc1)
    fs1.paste(text_cover, (0, 0), text_cover)
    cover = SlideData(fs1.convert("RGB"), text_cover, pc1, pos1)
    slides.append(_bind_motion(cover, "cover", {
        "title": title_l,
        "badge": badge_l,
        "orbit": orbit_cover_shifted,
        "pinyin": pinyin_l,
        "name": name_l,
        "meta": meta_l,
    }))

    # ------------------ 通用内容 Slide 构造器 (Slide 2, 3, 4) ------------------
    def _build_content_slide(title: str, text: str, img_idx: int):
        title_layer = _blank_canvas()
        draw_cloud_banner(title_layer, title, y_pos=158, font_size=72)

        pc, pos = create_fullbleed_hero_photo(get_img(img_idx), w=1080, h=900)

        orbit_shifted = _load_tilted_orbit(width=1280, tilt=-16, center_y=1505)

        # 样片正文大约每行 16 个琥珀字。50px 华文琥珀下 16 字约 750px 宽。
        font_size = 50
        max_width = 755
        f_body, f_fallback = typography.resolve_fonts(font_size)
        wrapped_lines = wrap_text_cjk(text, f_body, max_width=max_width)
        if len(wrapped_lines) > 5:
            font_size = 46
            max_width = 820
            f_body, f_fallback = typography.resolve_fonts(font_size)
            wrapped_lines = wrap_text_cjk(text, f_body, max_width=max_width)

        n_lines = max(1, len(wrapped_lines))
        line_height = 74 if n_lines >= 5 else 78
        block_h = n_lines * line_height
        y_start = int(1490 - block_h / 2)
        y_start = max(1236, y_start)
        x_start = 88

        caption = _blank_canvas()
        curr_y = y_start
        for line in wrapped_lines:
            s_line = render_slanted_line(
                line,
                primary_font=f_body,
                fallback_font=f_fallback,
                fill=typography.fill_rgb,
                outline_color=typography.outline_rgb,
                outline_width=typography.outline_width,
                shear=typography.shear_factor
            )
            caption.paste(s_line, (x_start, curr_y), s_line)
            curr_y += line_height

        text_all = _blank_canvas()
        text_all.paste(title_layer, (0, 0), title_layer)
        text_all.paste(orbit_shifted, (0, 0), orbit_shifted)
        text_all.paste(caption, (0, 0), caption)
        fs = bg.copy()
        fs.paste(pc, pos, pc)
        fs.paste(text_all, (0, 0), text_all)
        slide = SlideData(fs.convert("RGB"), text_all, pc, pos)
        slides.append(_bind_motion(slide, "content", {
            "title": title_layer,
            "orbit": orbit_shifted,
            "caption": caption,
        }))

    # SLIDE 2: 形态特征
    _build_content_slide(script.morphology_title, script.morphology_text, 1)

    # SLIDE 3: 植物趣闻
    _build_content_slide(script.trivia_title, script.trivia_text, 2)

    # SLIDE 4: 适生范围
    _build_content_slide(script.habitat_title, script.habitat_text, 3)

    # ------------------ SLIDE 5: 全屏收尾，源图略大于画布，方便前 0.5 秒推近 ------------------
    zoom_w, zoom_h = int(V_WIDTH * 1.18), int(V_HEIGHT * 1.18)
    hi5 = create_fullscreen_photo(get_img(4), w=zoom_w, h=zoom_h)
    preview = hi5.resize((V_WIDTH, V_HEIGHT), Image.Resampling.LANCZOS)
    tc5 = _blank_canvas()
    ending = SlideData(preview.convert("RGB"), tc5, hi5, (0, 0))
    slides.append(_bind_motion(ending, "ending", {}))

    return slides
