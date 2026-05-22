# -*- coding: utf-8 -*-
"""从植物智 info / PPBC 物种页解析首张图并下载（供后台「拉取到本站」使用）。"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

PPBC_ORIGIN = "https://ppbc.iplant.cn"
IPLANT_ORIGIN = "https://www.iplant.cn"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_IMG_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")


def _http_get(url: str, referer: str | None = None) -> str:
    h: dict[str, str] = {"User-Agent": UA}
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def extract_spid_from_iplant_html(html: str) -> str | None:
    m = re.search(r"getspinfobarcode\.ashx\?spid=(\d+)", html)
    return m.group(1) if m else None


def ppbc_first_jpeg_url(spid: str) -> str | None:
    params = urllib.parse.urlencode(
        {"callbackparam": "jcb", "t": "outphotoinfo", "cid": spid, "m": "0.1"}
    )
    url = f"{PPBC_ORIGIN}/ashx/getotherinfo.ashx?{params}"
    raw = _http_get(url, referer=f"{IPLANT_ORIGIN}/")
    m = re.match(r"^jcb\((.*)\)\s*$", raw.strip(), re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    if not data or not isinstance(data[0], dict):
        return None
    plist = data[0].get("plist") or []
    if not plist or not isinstance(plist[0], dict):
        return None
    pid = plist[0].get("pid")
    if not pid:
        return None
    return f"https://img3.iplant.cn/image2/565/{pid}.jpg"


def resolve_remote_image_url(page_url: str) -> tuple[str | None, str]:
    """(可直接下载的图片 URL, 说明)。"""
    u = (page_url or "").strip()
    if not u:
        return None, "空链接"
    low = u.lower()
    if any(low.split("?", 1)[0].endswith(ext) for ext in _IMG_EXT):
        return u, "图片直链"

    m = re.search(r"ppbc\.iplant\.cn/sp/(\d+)", u, re.I)
    if m:
        img = ppbc_first_jpeg_url(m.group(1))
        return (img, "PPBC 物种页") if img else (None, "PPBC 无图")

    if "iplant.cn/info/" in low:
        try:
            html = _http_get(u, referer=f"{IPLANT_ORIGIN}/")
        except OSError as e:
            return None, f"打开页面失败: {e}"
        spid = extract_spid_from_iplant_html(html)
        if not spid:
            return None, "页面无物种 id"
        img = ppbc_first_jpeg_url(spid)
        return (img, "植物智 info") if img else (None, "无 PPBC 缩略图")

    return None, "暂不支持的链接类型（需植物智 info、PPBC 物种页或图片直链）"


def download_image_bytes(image_url: str) -> bytes:
    headers = {
        "User-Agent": UA,
        "Referer": f"{PPBC_ORIGIN}/",
    }
    req = urllib.request.Request(image_url, headers=headers)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()
