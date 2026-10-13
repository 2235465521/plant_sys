# -*- coding: utf-8 -*-
"""Unit tests for TypographyStyle value object and rendering engine."""
import math
import sys
import unittest
from pathlib import Path
from pydantic import ValidationError

# Ensure backend root is on sys.path for runner invoked from repo root
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.video_automation.typography import TypographyStyle


class TestTypographyStyle(unittest.TestCase):
    def test_default_values_match_benchmark(self):
        style = TypographyStyle()
        self.assertEqual(style.slant_deg, -10.0)
        self.assertEqual(style.fill_hex.upper(), "#FFEE14")
        self.assertEqual(style.outline_hex.upper(), "#140F05")
        self.assertEqual(style.outline_width, 4)
        self.assertEqual(style.font_preset, "calligraphy")

    def test_shear_factor_calculation(self):
        style = TypographyStyle(slant_deg=-10.0)
        expected_shear = -math.tan(math.radians(-10.0))
        self.assertAlmostEqual(style.shear_factor, expected_shear, places=4)
        self.assertAlmostEqual(style.shear_factor, 0.1763, places=3)

        # 0 degree means no shear
        upright = TypographyStyle(slant_deg=0.0)
        self.assertAlmostEqual(upright.shear_factor, 0.0, places=4)

    def test_rgb_color_conversion(self):
        style = TypographyStyle(fill_hex="#FFEE14", outline_hex="#140F05")
        self.assertEqual(style.fill_rgb, (255, 238, 20))
        self.assertEqual(style.outline_rgb, (20, 15, 5))

        white_black = TypographyStyle(fill_hex="#FFFFFF", outline_hex="#000000")
        self.assertEqual(white_black.fill_rgb, (255, 255, 255))
        self.assertEqual(white_black.outline_rgb, (0, 0, 0))

    def test_validation_bounds(self):
        # Angle must be between -30 and +20
        with self.assertRaises(ValidationError):
            TypographyStyle(slant_deg=-45.0)

        with self.assertRaises(ValidationError):
            TypographyStyle(slant_deg=25.0)

        # Outline width must be between 0 and 12
        with self.assertRaises(ValidationError):
            TypographyStyle(outline_width=-1)

        with self.assertRaises(ValidationError):
            TypographyStyle(outline_width=20)

        # HEX format must be 6 hex digits
        with self.assertRaises(ValidationError):
            TypographyStyle(fill_hex="red")

        with self.assertRaises(ValidationError):
            TypographyStyle(fill_hex="#123")

    def test_factory_presets(self):
        tian = TypographyStyle.preset_benchmark_tian()
        self.assertEqual(tian.slant_deg, -10.0)
        self.assertEqual(tian.font_preset, "calligraphy")

        upright = TypographyStyle.preset_upright_classic()
        self.assertEqual(upright.slant_deg, 0.0)
        self.assertEqual(upright.font_preset, "kaiti")

        minimal = TypographyStyle.preset_modern_minimal()
        self.assertEqual(minimal.slant_deg, -5.0)
        self.assertEqual(minimal.font_preset, "sans")

    def test_font_resolution(self):
        style = TypographyStyle.preset_benchmark_tian()
        primary_font, fallback_font = style.resolve_fonts(size=52)
        self.assertIsNotNone(primary_font)
        self.assertIsNotNone(fallback_font)

    def test_render_slanted_line_with_style(self):
        from app.video_automation.trivia_renderer import render_slanted_line
        style = TypographyStyle.preset_upright_classic()
        f_pri, f_fb = style.resolve_fonts(50)
        img = render_slanted_line(
            "测试直立无倾斜楷体文本",
            primary_font=f_pri,
            fallback_font=f_fb,
            fill=style.fill_rgb,
            outline_color=style.outline_rgb,
            outline_width=style.outline_width,
            shear=style.shear_factor
        )
        self.assertEqual(img.mode, "RGBA")
        self.assertGreater(img.width, 100)
        self.assertGreater(img.height, 30)

    def test_render_trivia_slides_with_typography(self):
        from app.video_automation.trivia_renderer import render_trivia_slides
        from app.video_automation.trivia_script import TriviaScript

        dummy_plant = {
            "id": 999,
            "vernacular_name": "天葵子",
            "scientific_name": "Semiaquilegia adoxoides",
            "family": "毛茛科",
            "genus": "天葵属",
            "image_server_paths": []
        }
        dummy_script = TriviaScript(
            plant_name="天葵子",
            pinyin="tiān kuí zǐ",
            cover_badge="清热解毒",
            aliases="千年老鼠屎、金钱吊葫芦",
            family_genus="毛茛科 · 天葵属",
            morphology_title="形态特征",
            morphology_text="多年生草本，块根纺锤形，花小呈白色或浅粉色。",
            trivia_title="植物趣闻",
            trivia_text="因块根深褐色似老鼠粪便，民间戏称千年老鼠屎。",
            habitat_title="适生范围",
            habitat_text="生于海拔200-1000米的山坡疏林下或草丛中。"
        )

        custom_style = TypographyStyle.preset_modern_minimal()
        slides = render_trivia_slides(dummy_plant, dummy_script, typography=custom_style)
        self.assertEqual(len(slides), 5)
        for s in slides:
            self.assertIsNotNone(s.full_slide)
            self.assertEqual(s.full_slide.size, (1080, 1920))


if __name__ == "__main__":
    unittest.main()
