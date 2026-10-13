# -*- coding: utf-8 -*-
"""
typography.py - 视频排版与字体样式深模块 (Typography Deep Module)

将字体倾斜角度、颜色空间转换、描边粗细与多平台字体级联等图形学复杂性
完全封装在小型、纯净、自校验的值对象后。
"""
from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Tuple

from PIL import ImageFont
from pydantic import BaseModel, Field



class TypographyStyle(BaseModel):
    """
    排版样式接口：提供极小表面积与自校验机制。
    """
    slant_deg: float = Field(
        default=-10.0,
        ge=-30.0,
        le=20.0,
        description="字体倾斜角度（度数）：负值向右倾斜（行楷爆款风），0 为端正直立"
    )
    fill_hex: str = Field(
        default="#FFEE14",
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="字体填充颜色（6位 HEX 代码）"
    )
    outline_hex: str = Field(
        default="#140F05",
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="文字描边颜色（6位 HEX 代码）"
    )
    outline_width: int = Field(
        default=4,
        ge=0,
        le=12,
        description="描边粗细像素（0 表示无描边）"
    )
    font_preset: Literal["calligraphy", "kaiti", "sans"] = Field(
        default="calligraphy",
        description="字体形态预设：calligraphy(行楷书法), kaiti(端庄楷体), sans(现代黑体)"
    )

    # ──────────────── 工厂预设 ────────────────
    @classmethod
    def preset_benchmark_tian(cls) -> TypographyStyle:
        """对标《天.MOV》爆款行楷 10° 倾斜亮黄黑边（默认黄金标准）"""
        return cls(
            slant_deg=-10.0,
            fill_hex="#FFEE14",
            outline_hex="#140F05",
            outline_width=4,
            font_preset="calligraphy",
        )

    @classmethod
    def preset_upright_classic(cls) -> TypographyStyle:
        """经典端庄正楷（直立无倾斜，纯白黑边）"""
        return cls(
            slant_deg=0.0,
            fill_hex="#FFFFFF",
            outline_hex="#101010",
            outline_width=4,
            font_preset="kaiti",
        )

    @classmethod
    def preset_modern_minimal(cls) -> TypographyStyle:
        """现代科技感微倾黑体（-5°，暖黄深蓝边）"""
        return cls(
            slant_deg=-5.0,
            fill_hex="#FFD166",
            outline_hex="#073B4C",
            outline_width=3,
            font_preset="sans",
        )

    # ──────────────── 深层领域属性与方法 ────────────────
    @property
    def shear_factor(self) -> float:
        """
        根据倾斜度数计算 PIL AFFINE 变换所需的水平切变系数。
        由于 PIL AFFINE 是逆映射 (output -> input)，取 -tan(rad) 使得:
        slant_deg < 0 时字顶向右前倾 (+X)，与 CSS transform: skewX(...) 达到 1:1 精准同步。
        """
        return -math.tan(math.radians(self.slant_deg))

    @property
    def fill_rgb(self) -> Tuple[int, int, int]:
        """解析十六进制填充色为 RGB 三元组"""
        h = self.fill_hex.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    @property
    def outline_rgb(self) -> Tuple[int, int, int]:
        """解析十六进制描边色为 RGB 三元组"""
        h = self.outline_hex.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    def resolve_fonts(self, size: int) -> Tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
        """
        根据当前预设解析主字体与 CJK 降级保底字体。
        """
        from app.video_automation.trivia_renderer import (
            get_calligraphy_font,
            get_cjk_fallback_font,
            get_system_font,
        )
        if self.font_preset == "calligraphy":
            return get_calligraphy_font(size), get_cjk_fallback_font(size)
        elif self.font_preset == "kaiti":
            return get_cjk_fallback_font(size), get_system_font(size, bold=True)
        else:  # sans
            return get_system_font(size, bold=True), get_cjk_fallback_font(size)
