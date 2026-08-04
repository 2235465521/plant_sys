# -*- coding: utf-8 -*-
"""画图渲染模块。使用 Pillow 绘制竖屏 1080x1920 每一帧的基础画面，提供毛玻璃和高清缩放效果。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# 预设画布尺寸
V_WIDTH = 1080
V_HEIGHT = 1920

INVALID_TEXT_VALUES = {
    "无", "暂无", "无记载", "未知", "暂无详细形态描述。", "暂无详细形态描述",
    "无说明", "暂无说明", "暂无详细信息", "暂无描述", "无数据", "暂无数据"
}


def is_valid_text(val: Any) -> bool:
    """判断字段值是否为有效的显示文本，过滤掉 '无'、'暂无'、'无记载' 等无意义占位词。"""
    if val is None:
        return False
    s = str(val).strip()
    if not s:
        return False
    if s in INVALID_TEXT_VALUES:
        return False
    return True


class SlideData:
    """封装单个 Slide 的图层：包含完整合成帧、独立透明文字层、中间照片 RGBA 图层与其坐标。"""
    def __init__(
        self,
        full_slide: Image.Image,
        text_canvas: Image.Image,
        photo_canvas: Image.Image,
        photo_pos: tuple[int, int]
    ):
        self.full_slide = full_slide        # 完整合成 RGB 帧 (1080x1920)
        self.text_canvas = text_canvas      # 纯透明 RGBA 文字/标题图层 (1080x1920)
        self.photo_canvas = photo_canvas    # 中间植物照片 RGBA 图层
        self.photo_pos = photo_pos          # 照片在画布上的 (x, y) 坐标


def get_pinyin_for_name(name: str) -> str:
    """使用 pypinyin 库动态生成中文名拼音（带声调），以空格分隔。"""
    try:
        import pypinyin
        py_list = pypinyin.lazy_pinyin(name, style=pypinyin.Style.TONE)
        return " ".join(py_list)
    except Exception:
        return ""


def get_system_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """
    获取系统与全平台通用中文字体。
    优先加载项目自带的高保真全字符集中文字体 backend/data/video_assets/fonts/1.ttf 或 2.ttf，
    100% 避免在 Linux/Windows 服务器上回退到 Pillow 默认位图字体导致豆腐块方块 (tofu/XXXX) 乱码。
    """
    base_dir = Path(__file__).resolve().parent.parent.parent
    font_1 = base_dir / "data" / "video_assets" / "fonts" / "1.ttf"
    font_2 = base_dir / "data" / "video_assets" / "fonts" / "2.ttf"
    
    if font_1.exists():
        try:
            return ImageFont.truetype(str(font_1.resolve()), size)
        except Exception:
            pass
            
    if font_2.exists():
        try:
            return ImageFont.truetype(str(font_2.resolve()), size)
        except Exception:
            pass

    candidates = []
    if bold:
        candidates.extend([
            "C:\\Windows\\Fonts\\msyhbd.ttc",  # 微软雅黑 粗体
            "C:\\Windows\\Fonts\\simhei.ttf",  # 黑体
        ])
    candidates.extend([
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "C:\\Windows\\Fonts\\msyh.ttc",      # 微软雅黑 Regular
        "C:\\Windows\\Fonts\\simsun.ttc",     # 宋体
        "C:\\Windows\\Fonts\\FZSTK.TTF",      # 方正舒体
    ])
    
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
                
    return ImageFont.load_default()


def get_art_font(size: int) -> ImageFont.FreeTypeFont:
    """获取艺术中文字体（如方正舒体/华文行楷/楷体/隶书），提升大标题视觉效果。"""
    base_dir = Path(__file__).resolve().parent.parent.parent
    font_path = base_dir / "data" / "video_assets" / "fonts" / "2.ttf"
    if font_path.exists():
        try:
            return ImageFont.truetype(str(font_path.resolve()), size)
        except Exception:
            pass
            
    art_candidates = [
        "C:\\Windows\\Fonts\\FZSTK.TTF",    # 方正舒体
        "C:\\Windows\\Fonts\\STXINGKA.TTF", # 华文行楷
        "C:\\Windows\\Fonts\\STLITI.TTF",   # 华文隶书
        "C:\\Windows\\Fonts\\SIMLI.TTF",    # 隶书
        "C:\\Windows\\Fonts\\simkai.ttf",   # 楷体
        "C:\\Windows\\Fonts\\msyhbd.ttc",   # 微软雅黑 粗体
    ]
    for path in art_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return get_system_font(size, bold=True)


def get_custom_font(font_name: str, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """获取 data/video_assets/fonts 下指定的自定义字体，如果不存在则回退至系统字体。"""
    base_dir = Path(__file__).resolve().parent.parent.parent
    font_path = base_dir / "data" / "video_assets" / "fonts" / font_name
    if font_path.exists():
        try:
            return ImageFont.truetype(str(font_path.resolve()), size)
        except Exception:
            pass
    return get_system_font(size, bold=bold)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """根据文本在一行内所占的最大像素宽度进行中文自动换行折行。"""
    if not text:
        return []
    lines = []
    current_line = ""
    for char in text:
        w = font.getlength(current_line + char)
        if w <= max_width:
            current_line = current_line + char
        else:
            if current_line:
                lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)
    return lines


def load_paper_background() -> Image.Image:
    """加载古风背景纸底图，并强制缩放裁剪至 1080x1920。"""
    base_dir = Path(__file__).resolve().parent.parent.parent
    bg_path = base_dir / "data" / "video_assets" / "bg_paper.jpg"
    if bg_path.exists():
        try:
            img = Image.open(str(bg_path.resolve())).convert("RGB")
            if img.size == (V_WIDTH, V_HEIGHT):
                return img
            
            w, h = img.size
            scale = max(V_WIDTH / w, V_HEIGHT / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            x = (new_w - V_WIDTH) // 2
            y = (new_h - V_HEIGHT) // 2
            return resized.crop((x, y, x + V_WIDTH, y + V_HEIGHT))
        except Exception:
            pass
            
    img = Image.new("RGB", (V_WIDTH, V_HEIGHT), (245, 238, 220))
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, V_WIDTH - 40, V_HEIGHT - 40], outline=(200, 180, 150), width=3)
    return img


def crop_bottom_watermark(img: Image.Image, percent: float = 0.10) -> Image.Image:
    """自动裁切原生植物图片底部 percent 区域（移除大部分水印/标签）"""
    w, h = img.size
    if h > 100:
        crop_h = max(50, int(h * (1.0 - percent)))
        return img.crop((0, 0, w, crop_h))
    return img


def create_foreground_card(img_path: str) -> tuple[Image.Image, tuple[int, int]]:
    """
    制作中间的植物照片卡片 RGBA 图层（含圆角与精美古风规则双边框）。
    """
    card_w = 880
    card_h = 680
    card_x = (V_WIDTH - card_w) // 2  # 100
    card_y = 360                     # 下移至 360，避免挤压顶部
    
    real_img_path = resolve_local_img_path(img_path) if img_path else ""
    if not real_img_path or not os.path.exists(real_img_path):
        empty = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 0))
        return empty, (card_x, card_y)

    try:
        orig = Image.open(real_img_path).convert("RGBA")
        orig = crop_bottom_watermark(orig, percent=0.10)
    except Exception:
        empty = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 0))
        return empty, (card_x, card_y)
    
    orig_w, orig_h = orig.size
    
    # 智能自适应 Fill/Cover 模式：保持高保真自适应自充满 880x680，消除竖图边框过大留白
    scale = max(card_w / float(orig_w), card_h / float(orig_h))
    new_w = max(1, int(orig_w * scale))
    new_h = max(1, int(orig_h * scale))
    resized = orig.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    crop_x = (new_w - card_w) // 2
    crop_y = (new_h - card_h) // 2
    fg_img = resized.crop((crop_x, crop_y, crop_x + card_w, crop_y + card_h))
    
    # 精致圆角遮罩 (radius=24)
    fg_mask = Image.new("L", (card_w, card_h), 0)
    fg_mask_draw = ImageDraw.Draw(fg_mask)
    fg_mask_draw.rounded_rectangle([0, 0, card_w, card_h], radius=24, fill=255)
    
    fg_canvas = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 255))
    fg_canvas.paste(fg_img, (0, 0), fg_mask)
    
    # 绘制双重古风边框 (红色外框 + 金色内衬框)
    fg_draw = ImageDraw.Draw(fg_canvas)
    fg_draw.rounded_rectangle([0, 0, card_w, card_h], radius=24, outline=(141, 24, 32, 200), width=4)
    fg_draw.rounded_rectangle([6, 6, card_w - 6, card_h - 6], radius=20, outline=(210, 170, 100, 150), width=2)
    
    return fg_canvas, (card_x, card_y)



def create_circular_card(img_path: str, size: int = 650) -> tuple[Image.Image, tuple[int, int]]:
    """制作封面圆形古风花窗植物照片图层。"""
    fg_x = (V_WIDTH - size) // 2
    fg_y = 440
    
    real_img_path = resolve_local_img_path(img_path) if img_path else ""
    if not real_img_path or not os.path.exists(real_img_path):
        canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        return canvas, (fg_x, fg_y)
        
    try:
        orig = Image.open(real_img_path).convert("RGBA")
        orig = crop_bottom_watermark(orig, percent=0.10)
    except Exception:
        canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        return canvas, (fg_x, fg_y)
        
    orig_w, orig_h = orig.size
    scale = max(size / orig_w, size / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    resized = orig.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    x = (new_w - size) // 2
    y = (new_h - size) // 2
    cropped = resized.crop((x, y, x + size, y + size))
    
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, size, size), fill=255)
    
    canvas.paste(cropped, (0, 0), mask)
    
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((0, 0, size, size), outline=(255, 255, 255), width=6)
    return canvas, (fg_x, fg_y)


def resolve_local_img_path(server_path: str) -> str:
    """将虚拟 API/Web 图片路径解析为物理磁盘绝对路径，支持多种前缀与绝对/相对路径。"""
    if not server_path:
        return ""
    
    server_path = str(server_path).strip()
    if os.path.exists(server_path):
        return server_path

    base_dir = Path(__file__).resolve().parent.parent.parent
    clean_p = server_path.replace("\\", "/")

    if "/plants/" in clean_p:
        sub_path = clean_p.split("/plants/")[-1]
        resolved = base_dir / "data" / "plant_images" / sub_path
        if resolved.exists():
            return str(resolved.resolve())

    fname = Path(clean_p).name
    if fname:
        for p in (base_dir / "data" / "plant_images").rglob(fname):
            if p.exists():
                return str(p.resolve())

    return ""



def get_6_slide_images(plant_data: dict[str, Any]) -> list[SlideData]:
    """
    根据 6 个模板页，生成 6 张包含透明文字层与分离式前景照片的 SlideData 图层对象。
    严格过滤 '无'、'暂无'、'无记载' 等空字段。
    """
    slides: list[SlideData] = []
    paths = plant_data.get("image_server_paths") or []
    local_paths = [resolve_local_img_path(p) for p in paths if resolve_local_img_path(p)]
    
    def get_path_for_slide(idx: int) -> str:
        if not local_paths:
            return ""
        return local_paths[idx % len(local_paths)]
        
    font_title = get_art_font(96)
    font_body_bold = get_custom_font("1.ttf", 54, bold=True)
    font_body = get_custom_font("1.ttf", 50)
    
    font_cover_top = get_art_font(85)
    font_cover_sub = get_art_font(65)
    font_cover_title = get_art_font(130)
    font_cover_meta = get_custom_font("2.ttf", 50, bold=True)
    
    # ------------------ SLIDE 1: 封面 ------------------
    text_canvas1 = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
    s1_draw = ImageDraw.Draw(text_canvas1)
    
    top_text = "每日认识一种植物"
    s1_draw.text((V_WIDTH//2, 200), top_text, fill=(120, 85, 30), font=font_cover_top, anchor="mm")
    
    med_part = plant_data.get("medicinal_part")
    if is_valid_text(med_part):
        sub_text = f"（ {med_part}入药 ）"
        s1_draw.text((V_WIDTH//2, 310), sub_text, fill=(120, 85, 30), font=font_cover_sub, anchor="mm")
    
    photo_canvas1, photo_pos1 = create_circular_card(get_path_for_slide(0), size=650)
    
    name = plant_data.get("vernacular_name") or "未知植物"
    pinyin_text = get_pinyin_for_name(name)
    s1_draw.text((V_WIDTH//2, 1160), pinyin_text, fill=(198, 40, 40), font=font_cover_sub, anchor="mm")
    
    name_x, name_y = V_WIDTH // 2, 1290
    outline_width = 3
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                s1_draw.text((name_x + dx, name_y + dy), name, fill=(255, 255, 255), font=font_cover_title, anchor="mm")
    s1_draw.text((name_x, name_y), name, fill=(186, 12, 47), font=font_cover_title, anchor="mm")
    
    meta_lines = []
    alt_names = plant_data.get("alternative_names_zh")
    if not is_valid_text(alt_names) and plant_data.get("aliases_list"):
        valid_als = [a for a in plant_data["aliases_list"] if is_valid_text(a)]
        if valid_als:
            alt_names = "、".join(valid_als[:3])
    if is_valid_text(alt_names):
        meta_lines.append((f"别名：{alt_names}", 1460))
        
    fam = plant_data.get("family")
    gen = plant_data.get("genus")
    if is_valid_text(fam) and is_valid_text(gen):
        meta_lines.append((f"科属：{fam}科{gen}属", 1540 if meta_lines else 1460))
    elif is_valid_text(fam):
        meta_lines.append((f"科属：{fam}科", 1540 if meta_lines else 1460))
    elif is_valid_text(gen):
        meta_lines.append((f"科属：{gen}属", 1540 if meta_lines else 1460))
        
    for text, y_pos in meta_lines:
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx != 0 or dy != 0:
                    s1_draw.text((V_WIDTH//2 + dx, y_pos + dy), text, fill=(255, 255, 255), font=font_cover_meta, anchor="mm")
        s1_draw.text((V_WIDTH//2, y_pos), text, fill=(40, 40, 40), font=font_cover_meta, anchor="mm")
        
    full_slide1 = load_paper_background()
    full_slide1.paste(text_canvas1, (0, 0), text_canvas1)
    full_slide1.paste(photo_canvas1, photo_pos1, photo_canvas1)
    slides.append(SlideData(full_slide1, text_canvas1, photo_canvas1, photo_pos1))
    
    # ------------------ SLIDE 2: 科属名片 ------------------
    text_canvas2 = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
    s2_draw = ImageDraw.Draw(text_canvas2)
    s2_draw.text((V_WIDTH//2, 180), "科属名片", fill=(141, 24, 32), font=font_title, anchor="mm")
    
    lines2 = []
    v_name = plant_data.get('vernacular_name')
    if is_valid_text(v_name):
        lines2.append(f"中文学名：{v_name}")
        
    s_name = plant_data.get('scientific_name')
    if is_valid_text(s_name):
        lines2.append(f"拉丁学名：{s_name}")
        
    fam_gen = []
    if is_valid_text(fam):
        fam_gen.append(f"{fam}科")
    if is_valid_text(gen):
        fam_gen.append(f"{gen}属")
    if fam_gen:
        lines2.append(f"科属分类：{' · '.join(fam_gen)}")
        
    div = plant_data.get('division')
    subc = plant_data.get('subclass')
    div_sub = []
    if is_valid_text(div):
        div_sub.append(str(div))
    if is_valid_text(subc):
        div_sub.append(str(subc))
    if div_sub:
        lines2.append(f"门纲分类：{' · '.join(div_sub)}")
        
    if plant_data.get("aliases_list"):
        valid_als = [a for a in plant_data["aliases_list"] if is_valid_text(a)]
        if valid_als:
            lines2.append(f"常见别名：{'、'.join(valid_als[:2])}")
        
    y_start = 1240
    for line in lines2:
        wrapped = wrap_text(line, font_body, 820)
        for wl in wrapped:
            s2_draw.text((130, y_start), wl, fill=(40, 40, 40), font=font_body)
            y_start += 60
            
    photo_canvas2, photo_pos2 = create_foreground_card(get_path_for_slide(1))
    full_slide2 = load_paper_background()
    full_slide2.paste(text_canvas2, (0, 0), text_canvas2)
    full_slide2.paste(photo_canvas2, photo_pos2, photo_canvas2)
    slides.append(SlideData(full_slide2, text_canvas2, photo_canvas2, photo_pos2))
    
    # ------------------ SLIDE 3: 形态特征 ------------------
    text_canvas3 = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
    s3_draw = ImageDraw.Draw(text_canvas3)
    s3_draw.text((V_WIDTH//2, 180), "形态特征", fill=(141, 24, 32), font=font_title, anchor="mm")
    
    morph_txt = plant_data.get("morphology_text")
    if is_valid_text(morph_txt):
        s_morph = str(morph_txt).strip()
        if len(s_morph) > 120:
            s_morph = s_morph[:120] + "..."
        wrapped_morph = wrap_text(s_morph, font_body, 820)
        y_start = 1230
        for wl in wrapped_morph[:7]:
            s3_draw.text((130, y_start), wl, fill=(40, 40, 40), font=font_body)
            y_start += 60
            
    photo_canvas3, photo_pos3 = create_foreground_card(get_path_for_slide(2))
    full_slide3 = load_paper_background()
    full_slide3.paste(text_canvas3, (0, 0), text_canvas3)
    full_slide3.paste(photo_canvas3, photo_pos3, photo_canvas3)
    slides.append(SlideData(full_slide3, text_canvas3, photo_canvas3, photo_pos3))
    
    # ------------------ SLIDE 4: 主要用途与价值 ------------------
    text_canvas4 = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
    s4_draw = ImageDraw.Draw(text_canvas4)
    s4_draw.text((V_WIDTH//2, 180), "主要用途与价值", fill=(141, 24, 32), font=font_title, anchor="mm")
    
    val_lines = []
    y_start = 1230
    if is_valid_text(med_part):
        med_text = f"【入药部位】 {med_part}"
        font_med = get_custom_font("2.ttf", 56, bold=True) 
        s4_draw.text((V_WIDTH//2, y_start + 10), med_text, fill=(198, 40, 40), font=font_med, anchor="mm")
        y_start += 95
    
    homology = plant_data.get("is_medicinal_food_homologous")
    if is_valid_text(homology) and str(homology).strip() not in ["0", "false", "否"]:
        val_lines.append("【药食同源】 是")
        
    shape_desc = plant_data.get("medicinal_shape")
    if is_valid_text(shape_desc):
        val_lines.append(f"【药材特征】 {shape_desc}")
        
    h_desc = plant_data.get("harvest_months_desc")
    if is_valid_text(h_desc):
        val_lines.append(f"【采收说明】 {h_desc}")
        
    for line in val_lines:
        wrapped = wrap_text(line, font_body, 820)
        for wl in wrapped:
            s4_draw.text((130, y_start), wl, fill=(40, 40, 40), font=font_body)
            y_start += 60
            if y_start > 1750:
                break
                
    photo_canvas4, photo_pos4 = create_foreground_card(get_path_for_slide(3))
    full_slide4 = load_paper_background()
    full_slide4.paste(text_canvas4, (0, 0), text_canvas4)
    full_slide4.paste(photo_canvas4, photo_pos4, photo_canvas4)
    slides.append(SlideData(full_slide4, text_canvas4, photo_canvas4, photo_pos4))
    
    # ------------------ SLIDE 5: 生长环境 ------------------
    text_canvas5 = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
    s5_draw = ImageDraw.Draw(text_canvas5)
    s5_draw.text((V_WIDTH//2, 180), "生长环境", fill=(141, 24, 32), font=font_title, anchor="mm")
    
    hab_txt = plant_data.get("habitat")
    y_start = 1230
    if is_valid_text(hab_txt):
        s5_draw.text((130, y_start), "【生长习性与生境】", fill=(20, 60, 40), font=font_body_bold)
        y_start += 66
        wrapped_hab = wrap_text(str(hab_txt).strip(), font_body, 820)
        for wl in wrapped_hab[:4]:
            s5_draw.text((130, y_start), wl, fill=(40, 40, 40), font=font_body)
            y_start += 60
        
    valid_habs = [h for h in (plant_data.get("habitats_list") or []) if is_valid_text(h)]
    if valid_habs:
        y_start = max(y_start + 20, 1580)
        tags = "  ".join([f"#{h}" for h in valid_habs[:3]])
        s5_draw.text((130, y_start), tags, fill=(0, 80, 80), font=font_body_bold)
        
    photo_canvas5, photo_pos5 = create_foreground_card(get_path_for_slide(4))
    full_slide5 = load_paper_background()
    full_slide5.paste(text_canvas5, (0, 0), text_canvas5)
    full_slide5.paste(photo_canvas5, photo_pos5, photo_canvas5)
    slides.append(SlideData(full_slide5, text_canvas5, photo_canvas5, photo_pos5))
    
    # ------------------ SLIDE 6: 产地与分布 ------------------
    text_canvas6 = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
    s6_draw = ImageDraw.Draw(text_canvas6)
    s6_draw.text((V_WIDTH//2, 180), "产地与分布", fill=(141, 24, 32), font=font_title, anchor="mm")
    
    dist_cn = plant_data.get("distribution_china")
    dist_ab = plant_data.get("distribution_abroad")
    
    y_start = 1230
    if is_valid_text(dist_cn):
        s6_draw.text((130, y_start), "【国内分布】", fill=(198, 40, 40), font=font_body_bold)
        y_start += 60
        wrapped_cn = wrap_text(str(dist_cn).strip(), font_body, 820)
        for wl in wrapped_cn[:2]:
            s6_draw.text((130, y_start), wl, fill=(40, 40, 40), font=font_body)
            y_start += 60
        
    if is_valid_text(dist_ab):
        y_start += 20
        s6_draw.text((130, y_start), "【国外分布】", fill=(120, 85, 30), font=font_body_bold)
        s6_draw.text((130, y_start + 60), str(dist_ab).strip(), fill=(40, 40, 40), font=font_body)
            
    photo_canvas6, photo_pos6 = create_foreground_card(get_path_for_slide(5))
    full_slide6 = load_paper_background()
    full_slide6.paste(text_canvas6, (0, 0), text_canvas6)
    full_slide6.paste(photo_canvas6, photo_pos6, photo_canvas6)
    slides.append(SlideData(full_slide6, text_canvas6, photo_canvas6, photo_pos6))
    
    return slides


def render_title_curtain_frame(title: str, subtitle: str = "中国植物库 · 专题精选") -> SlideData:
    """渲染合集视频的主题片头幕 (1080x1920)。"""
    paper = load_paper_background()
    text_canvas = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_canvas)

    # 装饰框
    draw.rectangle([60, 60, V_WIDTH - 60, V_HEIGHT - 60], outline=(141, 24, 32), width=6)
    draw.rectangle([75, 75, V_WIDTH - 75, V_HEIGHT - 75], outline=(180, 140, 60), width=2)

    font_main = get_art_font(90)
    font_sub = get_system_font(42, bold=True)
    font_tip = get_system_font(32)

    # 专题大标题换行
    wrapped_title = wrap_text(title, font_main, 850)
    y_title = 750 - (len(wrapped_title) * 55)
    for line in wrapped_title:
        draw.text((V_WIDTH // 2, y_title), line, fill=(141, 24, 32), font=font_main, anchor="mm")
        y_title += 110

    # 副标题与古风落款印章图形
    draw.line([(V_WIDTH // 2 - 200, y_title + 40), (V_WIDTH // 2 + 200, y_title + 40)], fill=(180, 140, 60), width=3)
    draw.text((V_WIDTH // 2, y_title + 100), subtitle, fill=(40, 60, 40), font=font_sub, anchor="mm")
    
    # 底部说明
    draw.text((V_WIDTH // 2, 1720), "AI 智能自动合成 · 卷轴画卷", fill=(100, 100, 100), font=font_tip, anchor="mm")

    # 照片层空，整体合成
    paper.paste(text_canvas, (0, 0), text_canvas)
    empty_photo = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    return SlideData(paper, text_canvas, empty_photo, (0, 0))


def render_outro_curtain_frame(text: str = "中国植物库 · 自动生成出品") -> SlideData:
    """渲染合集视频的专题片尾幕 (1080x1920)。"""
    paper = load_paper_background()
    text_canvas = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_canvas)

    draw.rectangle([80, 80, V_WIDTH - 80, V_HEIGHT - 80], outline=(141, 24, 32), width=4)
    font_main = get_art_font(72)
    font_sub = get_system_font(38)

    draw.text((V_WIDTH // 2, V_HEIGHT // 2 - 60), "全篇完", fill=(141, 24, 32), font=font_main, anchor="mm")
    draw.text((V_WIDTH // 2, V_HEIGHT // 2 + 60), text, fill=(50, 50, 50), font=font_sub, anchor="mm")

    paper.paste(text_canvas, (0, 0), text_canvas)
    empty_photo = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    return SlideData(paper, text_canvas, empty_photo, (0, 0))


def get_condensed_slide_images(plant_data: dict, chapter_badge: str = "01/08") -> list[SlideData]:
    """为合集视频渲染 3 帧精简版 Slide（带有章节序号角标）。"""
    slides: list[SlideData] = []
    
    paths = plant_data.get("image_server_paths") or []
    local_paths = [resolve_local_img_path(p) for p in paths if resolve_local_img_path(p)]

    def get_img_path(idx: int) -> str:
        if not local_paths:
            return ""
        return local_paths[idx % len(local_paths)]


    font_badge = get_system_font(32, bold=True)
    font_vname = get_art_font(84)
    font_sname = get_system_font(34)
    font_title = get_art_font(60)
    font_body = get_system_font(36)
    font_body_bold = get_system_font(38, bold=True)

    vernacular_name = plant_data.get("vernacular_name") or "未命名植物"
    scientific_name = plant_data.get("scientific_name") or ""

    def draw_badge(draw_obj: ImageDraw.ImageDraw):
        """在右上角绘制形如 [ 01/08 人参 ] 的古风红框标签。"""
        badge_str = f"NO.{chapter_badge}  {vernacular_name}"
        draw_obj.rectangle([60, 60, 60 + 420, 60 + 64], fill=(141, 24, 32, 230))
        draw_obj.text((60 + 210, 60 + 32), badge_str, fill=(255, 255, 240), font=font_badge, anchor="mm")

    # ----- 章节 SLIDE 1: 封面大图与名片 -----
    tc1 = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
    d1 = ImageDraw.Draw(tc1)
    draw_badge(d1)

    d1.text((V_WIDTH // 2, 200), vernacular_name, fill=(141, 24, 32), font=font_vname, anchor="mm")
    if is_valid_text(scientific_name):
        d1.text((V_WIDTH // 2, 275), scientific_name, fill=(100, 100, 100), font=font_sname, anchor="mm")

    med_part = plant_data.get("medicinal_part")
    if is_valid_text(med_part):
        d1.text((V_WIDTH // 2, 1260), f"【入药部位】 {med_part}", fill=(198, 40, 40), font=font_body_bold, anchor="mm")

    morph = plant_data.get("morphology_text")
    if is_valid_text(morph):
        wrapped = wrap_text(str(morph).strip(), font_body, 820)
        y = 1340
        for line in wrapped[:3]:
            d1.text((130, y), line, fill=(40, 40, 40), font=font_body)
            y += 55

    pc1, pos1 = create_foreground_card(get_img_path(0))
    fs1 = load_paper_background()
    fs1.paste(tc1, (0, 0), tc1)
    fs1.paste(pc1, pos1, pc1)
    slides.append(SlideData(fs1, tc1, pc1, pos1))

    # ----- 章节 SLIDE 2: 药用性状与特征 -----
    tc2 = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(tc2)
    draw_badge(d2)
    d2.text((V_WIDTH // 2, 180), "药材性状特征", fill=(141, 24, 32), font=font_title, anchor="mm")

    med_shape = plant_data.get("medicinal_shape")
    if is_valid_text(med_shape):
        d2.text((130, 1230), "【饮片与鉴别特征】", fill=(180, 80, 20), font=font_body_bold)
        wrapped = wrap_text(str(med_shape).strip(), font_body, 820)
        y = 1295
        for line in wrapped[:4]:
            d2.text((130, y), line, fill=(40, 40, 40), font=font_body)
            y += 55

    pc2, pos2 = create_foreground_card(get_img_path(1))
    fs2 = load_paper_background()
    fs2.paste(tc2, (0, 0), tc2)
    fs2.paste(pc2, pos2, pc2)
    slides.append(SlideData(fs2, tc2, pc2, pos2))

    # ----- 章节 SLIDE 3: 产地分布与环境 -----
    tc3 = Image.new("RGBA", (V_WIDTH, V_HEIGHT), (0, 0, 0, 0))
    d3 = ImageDraw.Draw(tc3)
    draw_badge(d3)
    d3.text((V_WIDTH // 2, 180), "生境与分布", fill=(141, 24, 32), font=font_title, anchor="mm")

    habitat = plant_data.get("habitat")
    dist = plant_data.get("distribution_china")
    y = 1230
    if is_valid_text(habitat):
        d3.text((130, y), "【生态习性】", fill=(20, 60, 40), font=font_body_bold)
        y += 55
        wrapped = wrap_text(str(habitat).strip(), font_body, 820)
        for line in wrapped[:2]:
            d3.text((130, y), line, fill=(40, 40, 40), font=font_body)
            y += 50
    if is_valid_text(dist):
        y += 15
        d3.text((130, y), "【主要产地】", fill=(198, 40, 40), font=font_body_bold)
        y += 55
        wrapped = wrap_text(str(dist).strip(), font_body, 820)
        for line in wrapped[:2]:
            d3.text((130, y), line, fill=(40, 40, 40), font=font_body)
            y += 50

    pc3, pos3 = create_foreground_card(get_img_path(2))
    fs3 = load_paper_background()
    fs3.paste(tc3, (0, 0), tc3)
    fs3.paste(pc3, pos3, pc3)
    slides.append(SlideData(fs3, tc3, pc3, pos3))

    return slides

