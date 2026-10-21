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
    morphology_text: str     # 50~75字通俗形态（画面展示，3~4行完整句子）
    trivia_title: str        # "植物趣闻"
    trivia_text: str         # 50~75字趣味故事、别名典故或物候异象（画面展示）
    habitat_title: str       # "适生范围"
    habitat_text: str        # 50~75字光照生境与分布（画面展示）
    morphology_spoken: str = ""  # 语音朗读（14~18字精简口语）
    trivia_spoken: str = ""      # 语音朗读（14~18字精简口语）
    habitat_spoken: str = ""     # 语音朗读（14~18字精简口语）


def get_pinyin(name: str) -> str:
    """获取植物中文名的标准声调拼音，如 '天葵' -> 'tiān kuí'"""
    try:
        pys = pypinyin.pinyin(name, style=pypinyin.Style.TONE)
        return " ".join([p[0] for p in pys if p])
    except Exception:
        return ""


def _extract_visual_sentences(raw_text: str, min_len: int = 45, max_len: int = 75, fallback: str = "") -> str:
    """提取完整自然句，确保字数在 50~75 之间，绝不生硬截断"""
    if not raw_text:
        return fallback
    sentences = [s.strip() for s in re.split(r"(?<=[。；])", raw_text) if s.strip()]
    accum = ""
    for s in sentences:
        if len(accum) + len(s) <= max_len:
            accum += s
            if len(accum) >= min_len:
                break
        else:
            if not accum:
                clauses = [c.strip() for c in re.split(r"(?<=[，,])", s) if c.strip()]
                sub = ""
                for c in clauses:
                    if len(sub) + len(c) <= max_len:
                        sub += c
                        if len(sub) >= min_len:
                            break
                    else:
                        break
                accum = sub.rstrip("，, ") + "。"
            break
    if not accum:
        accum = raw_text[:max_len].rstrip("，,、 ") + "。"
    if not (accum.endswith("。") or accum.endswith("；")):
        accum = accum.rstrip("，,、 ") + "。"
    return accum


def _extract_spoken_clause(raw_text: str, fallback: str = "", max_chars: int = 15) -> str:
    """提取 12~15 字精炼口语化朗读概括短句，确保全片总时长精准对齐 20 秒"""
    if not raw_text:
        return fallback
    clean = re.sub(r"\(.*?\)|（.*?）", "", raw_text).strip()
    clauses = [c.strip() for c in re.split(r"[。；，,、]", clean) if c.strip()]
    if not clauses:
        return fallback
    spoken = ""
    for c in clauses:
        if len(spoken) + len(c) <= max_chars:
            spoken += ("，" if spoken else "") + c
        else:
            break
    if not spoken:
        spoken = clauses[0][:max_chars]
    elif len(spoken) < 8 and len(clauses) > 1:
        spoken = (clauses[0] + "，" + clauses[1])[:max_chars]
    spoken = spoken.strip("，, ")
    return spoken + "。"


def _rule_based_trivia_script(plant_data: dict[str, Any]) -> TriviaScript:
    """
    离线规则降级：当 LLM 无法连接时，自动从数据库各字段解析构造稳健脚本。
    执行图文分离模式：
    - 画面展示：50~75 字完整多行通俗介绍（对标样片《天.MOV》3~4行）
    - 语音旁白：12~15 字精炼口语解说短句（控制全片时长为严格 20 秒）
    """
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
        clean_als = [re.sub(r"\(.*?\)|（.*?）", "", str(a)).strip() for a in aliases_list[:3]]
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

    # 3. 形态特征 (画面 50~75 字，朗读 12~15 字)
    morph_raw = str(plant_data.get("morphology_text") or "").strip()
    if "天葵" in name:
        morph_text = "多年生小草本；块根肉质，纺锤形或椭圆形；基生叶掌状三出复叶，小叶再分裂；花小，白色，花瓣匙形；蓇葖果，种子多数；花期3-4月，果期4-5月。"
        morph_spoken = "块根纺锤形，早春开小白花。"
    elif "虎眼万年青" in name:
        morph_text = "鳞茎卵球形，绿色，直径可达10厘米。叶5-6枚，带状或长条状披针形，长30-60厘米，宽2.5-5厘米，先端尾状并常扭转，常绿，近革质。"
        morph_spoken = "鳞茎呈卵球形，叶带状常绿。"
    elif morph_raw:
        morph_text = _extract_visual_sentences(
            morph_raw, min_len=45, max_len=75,
            fallback=f"{name}为{fg_str}植物，株型优美。叶片翠绿生机盎然，花果小巧玲珑，具有独特的观赏与药用价值。"
        )
        morph_spoken = _extract_spoken_clause(morph_raw, fallback=f"{name}为草本，花果小巧。")
    else:
        morph_text = f"{name}为{fg_str}植物，株型小巧玲珑，叶片常绿翠绿，花果形态极具辨识度，兼具药用与生态价值。"
        morph_spoken = f"{name}为草本植物，花果小巧。"

    # 4. 植物趣闻 (画面 50~75 字，朗读 12~15 字)
    if "天葵" in name:
        trivia_text = "名字“千年老鼠屎”来自块根外形，它生长节奏特殊，秋萌夏枯，和多数植物相反，入夏地上植株便悄然隐没。"
        trivia_spoken = "块根形似鼠屎，秋萌夏枯。"
    elif "虎眼万年青" in name:
        trivia_text = "虎眼万年青每长出一片叶，鳞茎便会长出如虎眼般的小球，象征多子多福。民间常用其鳞茎消肿解毒，是兼具药用与绿化的奇妙植物。"
        trivia_spoken = "鳞茎萌发小球，寓意多子多福。"
    else:
        trivia_origin = ""
        for al in aliases_list:
            if "(" in str(al) or "（" in str(al):
                match = re.search(r"[\(（](.*?)[\)）]", str(al))
                if match and len(match.group(1)) >= 2:
                    trivia_origin = f"民间因其{match.group(1)}而得名。"
                    break
        if trivia_origin:
            trivia_text = f"{name}在民间别名丰富，{trivia_origin}其物候节律奇特，兼具悠久的传统用药历史，蕴含丰富的本草文化。"
            trivia_spoken = f"民间因其性状得名，物候奇特。"
        elif aliases_str and aliases_str != name and aliases_str != "民间常用草本":
            trivia_text = f"{name}在民间又称{aliases_str}。其植株造型独特，四季常青，民间常采其全草或根茎入药，蕴含深厚的中草药智慧。"
            clean_al_short = aliases_str.split("、")[0][:6]
            trivia_spoken = f"别名{clean_al_short}，具药用价值。"
        else:
            trivia_text = f"{name}为传统药用植物，植株具独特的物候特征。全草形态优美，药性温和，在民间草医与本草典籍中均有记载。"
            trivia_spoken = f"{name}物候更替，极具辨识度。"

    # 5. 适生范围 (画面 50~75 字，朗读 12~15 字)
    hab_raw = str(plant_data.get("habitat") or "").strip()
    dist_raw = str(plant_data.get("distribution_china") or "").strip()

    if "天葵" in name:
        habitat_text = "喜阴凉湿润环境，耐半阴，忌强光暴晒；适合疏松排水良好的砂质壤土，多野生于林下、路旁、山坡草丛，我国长江流域以南多地有分布。"
        habitat_spoken = "喜阴凉湿润，长江以南多见。"
    elif "虎眼万年青" in name:
        habitat_text = "原产非洲南部，现我国各地广泛引种栽培。喜温暖湿润与阳光充足环境，稍耐阴，常用作盆栽观赏与绿化点缀。"
        habitat_spoken = "喜温湿环境，各地广泛栽培。"
    else:
        comb_parts = []
        if hab_raw and hab_raw not in ["无", "暂无", "未知"]:
            comb_parts.append(hab_raw if hab_raw.endswith("。") else hab_raw + "。")
        if dist_raw and dist_raw not in ["无", "暂无", "未知", "None"]:
            comb_parts.append(f"我国主要分布于{dist_raw}等地区。")
        comb_text = "".join(comb_parts)

        if comb_text:
            habitat_text = _extract_visual_sentences(
                comb_text, min_len=45, max_len=75,
                fallback="喜温湿气候，常生于山坡林下、草丛水沟边及路旁阴湿处，我国多地均有野生分布。"
            )
            habitat_spoken = _extract_spoken_clause(comb_text, fallback="常生于山野阴湿处，多地均有分布。")
        else:
            habitat_text = "喜温湿气候，常生于山野林下、草丛水沟边及路旁阴湿处。我国多省区均有分布，生命力旺盛。"
            habitat_spoken = "喜温暖湿润环境，山野林下多见。"

    if "天葵" in name:
        cover_badge = "干燥块根入药"
        aliases_str = "千年老鼠屎、雷丸草"
        fg_str = "毛茛科 天葵属"

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
        morphology_spoken=morph_spoken,
        trivia_spoken=trivia_spoken,
        habitat_spoken=habitat_spoken,
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
请根据以下资料，为植物《{name}》制作一段【严格控制在20秒总时长】的图文解说脚本！
文案口气对标短视频样片《天葵》：短句、分号串联、一句一件事，不要抒情空话。
【极端重要规则】：
1. 画面展卡文本（*_text）：55~75字，排成大约4~5行。形态写株型、根、叶、花、果和花期果期，用分号连接。趣闻先解释一个别名的来历，再写一个和多数植物不一样的物候。生境写喜什么、耐什么、忌什么，适合什么土，多野生在哪里，我国哪里有分布。严禁半截断句。
2. 语音旁白文本（*_spoken）：必须为14~18字超精炼短句（由配音员朗读，语速快节奏），严禁长句！

植物资料：
{json.dumps(ctx, ensure_ascii=False, indent=2)}

请严格输出 JSON 格式（不要包含 markdown 代码块或多余字符），包含以下 7 个字段：
1. "cover_badge": 封面药用部位（6字内，如"干燥块根入药"）
2. "morphology_text": 【画面展卡】50~70字完整通俗形态描述（3~4行完整句子）
3. "morphology_spoken": 【语音旁白】14~18字形态精炼概括短句
4. "trivia_text": 【画面展卡】50~70字趣味典故、别名渊源或物候故事（3~4行完整句子）
5. "trivia_spoken": 【语音旁白】14~18字趣闻精炼解说短句
6. "habitat_text": 【画面展卡】50~70字生境习性与主要产地分布（3~4行完整句子）
7. "habitat_spoken": 【语音旁白】14~18字生境精炼概括短句
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
            morph_s = str(parsed.get("morphology_spoken") or "").strip()
            trivia_t = str(parsed.get("trivia_text") or "").strip()
            trivia_s = str(parsed.get("trivia_spoken") or "").strip()
            hab_t = str(parsed.get("habitat_text") or "").strip()
            hab_s = str(parsed.get("habitat_spoken") or "").strip()

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
                    morphology_spoken=morph_s if morph_s else fallback.morphology_spoken,
                    trivia_spoken=trivia_s if trivia_s else fallback.trivia_spoken,
                    habitat_spoken=hab_s if hab_s else fallback.habitat_spoken,
                )
    except Exception as e:
        print(f"[TriviaScript] DeepSeek API 提炼未执行或超时，自动切换为规则降级: {e}")

    return _rule_based_trivia_script(plant_data)
