# -*- coding: utf-8 -*-
"""
text_summarizer.py - AI 植物简介生成器（深模块）

接口: summarize_plant_for_tts(plant_data: dict) -> str
  - 调用 DeepSeek API 生成 100~150 字 TTS 朗读词
  - 失败时降级为规则拼接，永不抛异常
"""
from __future__ import annotations
import json
import os
import urllib.request

_DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
_DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
_DEEPSEEK_MODEL = "deepseek-v4-flash"


def _rule_based_summary(plant_data: dict) -> str:
    name = plant_data.get("vernacular_name") or plant_data.get("scientific_name") or "这种植物"
    lines = ["为您介绍" + name + "。"]
    if plant_data.get("family_name"):
        lines.append("它属于" + str(plant_data["family_name"]) + "科。")
    if plant_data.get("medicinal_part"):
        lines.append("入药部位为" + str(plant_data["medicinal_part"]) + "。")
    if plant_data.get("efficacy"):
        lines.append("主要功效：" + str(plant_data["efficacy"])[:60] + "。")
    if plant_data.get("morphology_text"):
        lines.append(str(plant_data["morphology_text"])[:80] + "。")
    return "".join(lines)


def summarize_plant_for_tts(plant_data: dict) -> str:
    name = plant_data.get("vernacular_name") or plant_data.get("scientific_name") or "未知植物"
    ctx = []
    field_map = [
        ("family_name", "科"),
        ("medicinal_part", "入药部位"),
        ("efficacy", "功效"),
        ("morphology_text", "形态"),
        ("growth_habitat", "生境"),
    ]
    for k, label in field_map:
        v = plant_data.get(k)
        if v:
            ctx.append(label + "：" + str(v)[:120])
    context = "\n".join(ctx) if ctx else "无详细信息"
    prompt = (
        "请为植物《" + name + "》写一段适合视频配音朗读的中文介绍词。"
        "要求：语言自然流畅、通俗易懂、约100到150字、不要列表格式、不要括号注释。"
        "植物资料如下：\n" + context
    )
    try:
        payload = json.dumps({
            "model": _DEEPSEEK_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": 0.7,
        }).encode("utf-8")
        req = urllib.request.Request(
            _DEEPSEEK_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + _DEEPSEEK_API_KEY,
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            summary = data["choices"][0]["message"]["content"].strip()
            if summary:
                print("[TTS-Summarizer] DeepSeek 生成成功，字数:", len(summary))
                return summary
    except Exception as e:
        print("[TTS-Summarizer] DeepSeek 失败，降级为规则拼接:", e)
    return _rule_based_summary(plant_data)
