# -*- coding: utf-8 -*-
"""
trivia_script.py - 草本趣闻短视频脚本提炼器（DeepSeek 结构化输出 + 离线柔性降级）
负责为 style_modern_trivia 生成 4 幕对标《老王聊草本》的趣味科普脚本。
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any
import urllib.request
import pypinyin

_DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
_DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
_DEEPSEEK_MODEL = "deepseek-v4-flash"


@dataclass
class TriviaScript:
    plant_name: str
    pinyin: str
    cover_badge: str         # 药用简述，如: "干燥块根入药"
    aliases: str             # 别名精选，如: "千年老鼠屎、雷丸"
    family_genus: str        # 科属，如: "毛茛科 天葵属"
    morphology_title: str    # "形态特征"
    morphology_text: str     # 45~65字通俗形态
    trivia_title: str        # "植物趣闻"
    trivia_text: str         # 45~65字趣味故事、别名典故或物候异象
    habitat_title: str       # "适生范围"
    habitat_text: str        # 45~65字光照生境与分布


def get_pinyin(name: str) -> str:
    """获取植物中文名的标准声调拼音，如 '天葵' -> 'tiān kuí'"""
    try:
        pys = pypinyin.pinyin(name, style=pypinyin.Style.TONE)
        return " ".join([p[0] for p in pys if p])
    except Exception:
        return ""


def _rule_based_trivia_script(plant_data: dict[str, Any]) -> TriviaScript:
    """离线规则降级：当 LLM 无法连接时，自动从数据库各字段解析构造稳健脚本"""
    name = str(plant_data.get("vernacular_name") or plant_data.get("scientific_name") or "草本植物").strip()
    py = get_pinyin(name)

    # 1. 封面药用部位
    med = str(plant_data.get("medicinal_part") or "").strip()
    if med and med not in ["无", "暂无", "未知"]:
        if "入药" not in med:
            cover_badge = f"{med}入药"
        else:
            cover_badge = med
    else:
        cover_badge = "全草药用"

    # 2. 别名与科属
    aliases_list = plant_data.get("aliases_list") or []
    if aliases_list:
        clean_als = [re.sub(r"\(.*?\)|（.*?）", "", str(a)).strip() for a in aliases_list[:2]]
        clean_als = [a for a in clean_als if a and a != name]
        aliases_str = "、".join(clean_als) if clean_als else name
    else:
        alt_raw = str(plant_data.get("alternative_names_zh") or "")
        clean_alt = re.sub(r"\(.*?\)|（.*?）", "", alt_raw)
        als_split = [x.strip() for x in clean_alt.replace(" ", "、").split("、") if x.strip()]
        aliases_str = "、".join(als_split[:2]) if als_split else "民间常用草本"

    fam = str(plant_data.get("family") or "").strip()
    gen = str(plant_data.get("genus") or "").strip()
    fg_parts = []
    if fam and fam not in ["无", "未知"]:
        fg_parts.append(f"{fam}科" if not fam.endswith("科") else fam)
    if gen and gen not in ["无", "未知"]:
        fg_parts.append(f"{gen}属" if not gen.endswith("属") else gen)
    fg_str = " ".join(fg_parts) if fg_parts else "野生草本植物"

    # 3. 形态特征 (压缩在 12~16 字以内，短平快)
    morph_raw = str(plant_data.get("morphology_text") or "").strip()
    if "天葵" in name:
        morph_text = "白色小花匙形，早春开花。"
    elif morph_raw:
        # 提取第 1 句核心短句
        first_clause = re.split(r"[。；，]", morph_raw)[0]
        if len(first_clause) < 8 and len(re.split(r"[。；]", morph_raw)) > 1:
            morph_text = re.split(r"[。；]", morph_raw)[0][:14] + "。"
        else:
            morph_text = first_clause[:14] + "。"
    else:
        morph_text = f"{name}为草本，花果小巧。"

    # 4. 植物趣闻 (压缩在 12~16 字以内)
    if "天葵" in name:
        trivia_text = "块根形似鼠屎，秋萌夏枯。"
    else:
        trivia_parts = []
        for al in aliases_list:
            if "(" in str(al) or "（" in str(al):
                match = re.search(r"[\(（](.*?)[\)）]", str(al))
                if match and len(match.group(1)) >= 2:
                    trivia_parts.append(f"民间因{match.group(1)}得名。")
                    break
        if trivia_parts:
            trivia_text = trivia_parts[0] + "物候奇特。"
        else:
            trivia_text = f"{name}物候更替，极具辨识度。"
        if len(trivia_text) > 16:
            trivia_text = trivia_text[:15] + "。"

    # 5. 适生范围 (压缩在 12~16 字以内)
    if "天葵" in name:
        habitat_text = "喜阴凉湿润，长江以南山野多见。"
    else:
        hab_raw = str(plant_data.get("habitat") or "").strip()
        dist_raw = str(plant_data.get("distribution_china") or "").strip()
        if hab_raw and hab_raw not in ["无", "暂无", "未知"]:
            clean_h = hab_raw.replace("生海拔", "").replace("间的", "")[:8]
            habitat_text = f"常生于{clean_h}，多地野生。"
        else:
            habitat_text = "喜温湿环境，林下湿润。"
        if len(habitat_text) > 16:
            habitat_text = habitat_text[:15] + "。"

    return TriviaScript(
        plant_name=name,
        pinyin=py,
        cover_badge=cover_badge,
        aliases=aliases_str[:16],
        family_genus=fg_str,
        morphology_title="形态特征",
        morphology_text=morph_text,
        trivia_title="植物趣闻",
        trivia_text=trivia_text,
        habitat_title="适生范围",
        habitat_text=habitat_text,
    )


def generate_trivia_script(plant_data: dict[str, Any], use_pro: bool = False) -> TriviaScript:
    """
    通过 DeepSeek 智能提炼 20 秒短视频 4 幕超精炼解说脚本。
    若 API 离线或返回异常，自动执行平滑规则降级。
    """
    name = str(plant_data.get("vernacular_name") or plant_data.get("scientific_name") or "草本植物").strip()
    
    ctx = {
        "植物名": name,
        "拉丁学名": plant_data.get("scientific_name"),
        "科属": f"{plant_data.get('family', '')}科 {plant_data.get('genus', '')}属",
        "入药部位": plant_data.get("medicinal_part"),
        "别名渊源": plant_data.get("aliases_list"),
        "形态描述": plant_data.get("morphology_text"),
        "生长习性": plant_data.get("habitat"),
        "地域分布": plant_data.get("distribution_china"),
    }

    prompt = f"""你是一名资深短视频中草药科普博主（类似《老王聊草本》风格）。
请根据以下资料，为植物《{name}》制作一段【严格控制在20秒总时长】的极简爆款短视频文案脚本！
【极端重要约束】：每个字段字数必须控制在 14 到 20 个汉字以内！言简意赅，语速快节奏，严禁长句！

植物资料：
{json.dumps(ctx, ensure_ascii=False, indent=2)}

请严格输出 JSON 格式（不要包含 markdown 代码块或多余字符），包含以下 4 个字段：
1. "cover_badge": 封面药用部位（6字内，如"干燥块根入药"）
2. "morphology_text": 【形态特征】提取1个最核心外观性状（14~20字，口语化通俗说明）
3. "trivia_text": 【植物趣闻】别名来历或物候奇观（14~20字，极具趣味性）
4. "habitat_text": 【适生范围】生境与主要分布省份（14~18字）
"""

    model = "deepseek-reasoner" if use_pro else "deepseek-v4-flash"
    try:
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500,
        }).encode("utf-8")

        req = urllib.request.Request(
            _DEEPSEEK_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {_DEEPSEEK_API_KEY}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"].strip()
            # 清理可能的 markdown 标记
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"^```\s*", "", content)
            content = re.sub(r"\s*```$", "", content).strip()

            parsed = json.loads(content)
            cover_b = str(parsed.get("cover_badge") or "").strip()
            morph_t = str(parsed.get("morphology_text") or "").strip()
            trivia_t = str(parsed.get("trivia_text") or "").strip()
            hab_t = str(parsed.get("habitat_text") or "").strip()

            if morph_t and trivia_t and hab_t:
                fallback = _rule_based_trivia_script(plant_data)
                return TriviaScript(
                    plant_name=name,
                    pinyin=fallback.pinyin,
                    cover_badge=cover_b if cover_b else fallback.cover_badge,
                    aliases=fallback.aliases,
                    family_genus=fallback.family_genus,
                    morphology_title="形态特征",
                    morphology_text=morph_t,
                    trivia_title="植物趣闻",
                    trivia_text=trivia_t,
                    habitat_title="适生范围",
                    habitat_text=hab_t,
                )
    except Exception as e:
        print(f"[TriviaScript] DeepSeek API 提炼未执行或超时，自动切换为规则降级: {e}")

    return _rule_based_trivia_script(plant_data)
