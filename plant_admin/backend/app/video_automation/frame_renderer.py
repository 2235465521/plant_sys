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
    """获取 Windows 系统默认中文字体（微软雅黑/黑体/宋体）。"""
    candidates = []
    if bold:
        candidates.extend([
            "C:\\Windows\\Fonts\\msyhbd.ttc",  # 微软雅黑 粗体
            "C:\\Windows\\Fonts\\simhei.ttf",  # 黑体
        ])
    candidates.extend([
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
            
    return Image.new("RGB", (V_WIDTH, V_HEIGHT), (245, 240, 230))


def create_foreground_card(img_path: str) -> tuple[Image.Image, tuple[int, int]]:
    """
    制作中间的植物照片卡片 RGBA 图层（含圆角与细边框），并计算 (x, y) 坐标。
    """
    max_fg_w = V_WIDTH - 60
    max_fg_h = 900
    
    if not img_path or not os.path.exists(img_path):
        empty = Image.new("RGBA", (800, 600), (255, 255, 255, 0))
        return empty, ((V_WIDTH - 800) // 2, 390)

    try:
        orig = Image.open(img_path).convert("RGBA")
    except Exception:
        empty = Image.new("RGBA", (800, 600), (255, 255, 255, 0))
        return empty, ((V_WIDTH - 800) // 2, 390)
    
    orig_w, orig_h = orig.size
    fg_scale = min(max_fg_w / orig_w, max_fg_h / orig_h)
    fg_w = max(100, int(orig_w * fg_scale))
    fg_h = max(100, int(orig_h * fg_scale))
    fg_img = orig.resize((fg_w, fg_h), Image.Resampling.LANCZOS)
    
    fg_x = (V_WIDTH - fg_w) // 2
    fg_y = 240 + (max_fg_h - fg_h) // 2
    
    fg_mask = Image.new("L", (fg_w, fg_h), 0)
    fg_mask_draw = ImageDraw.Draw(fg_mask)
    fg_mask_draw.rounded_rectangle([0, 0, fg_w, fg_h], radius=20, fill=255)
    
    fg_canvas = Image.new("RGBA", (fg_w, fg_h), (255, 255, 255, 255))
    fg_canvas.paste(fg_img, (0, 0), fg_mask)
    
    fg_draw = ImageDraw.Draw(fg_canvas)
    fg_draw.rounded_rectangle([0, 0, fg_w, fg_h], radius=20, outline=(101, 80, 60, 150), width=3)
    
    return fg_canvas, (fg_x, fg_y)


def create_circular_card(img_path: str, size: int = 650) -> tuple[Image.Image, tuple[int, int]]:
    """制作封面专属的圆形带白框照片卡片 RGBA 图层。"""
    fg_x = (V_WIDTH - size) // 2
    fg_y = 420
    
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if not img_path or not os.path.exists(img_path):
        return canvas, (fg_x, fg_y)

    try:
        orig = Image.open(img_path).convert("RGBA")
    except Exception:
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
    """将虚拟路径解析为本地绝对路径。"""
    if not server_path:
        return ""
    base_dir = Path(__file__).resolve().parent.parent.parent
    prefix = "/api/media/plants/"
    if server_path.startswith(prefix):
        sub_path = server_path[len(prefix):]
        resolved = base_dir / "data" / "plant_images" / sub_path
        if resolved.exists():
            return str(resolved.resolve())
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
        
    font_title = get_custom_font("2.ttf", 80, bold=True)      
    font_body_bold = get_custom_font("1.ttf", 46, bold=True)
    font_body = get_custom_font("1.ttf", 42)
    
    font_cover_top = get_custom_font("2.ttf", 75, bold=True)      
    font_cover_sub = get_custom_font("2.ttf", 55, bold=True)      
    font_cover_title = get_custom_font("2.ttf", 110, bold=True)   
    font_cover_meta = get_custom_font("2.ttf", 46, bold=True)
    
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
