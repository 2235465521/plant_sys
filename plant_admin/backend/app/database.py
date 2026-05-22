from __future__ import annotations

from collections.abc import Generator
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import pymysql
from pymysql.cursors import DictCursor

from app.config import get_settings


def _pymysql_password_param(password: str) -> str | bytes:
    """PyMySQL 对 str 密码强制 latin-1 编码；含中文等字符时会失败，改为传入 UTF-8 字节。"""
    if not password:
        return ""
    try:
        password.encode("latin-1")
        return password
    except UnicodeEncodeError:
        return password.encode("utf-8")


def _mysql_connect_kwargs(database_url: str) -> dict[str, Any]:
    u = database_url.strip()
    if u.startswith("mysql+pymysql://"):
        u = "mysql://" + u.split("mysql+pymysql://", 1)[1]
    elif not u.startswith("mysql://"):
        u = "mysql://" + u.split("://", 1)[1]
    parsed = urlparse(u)
    db = (parsed.path or "/").lstrip("/").split("?")[0]
    qs = parse_qs(parsed.query)
    charset = (qs.get("charset") or ["utf8mb4"])[0]
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username) if parsed.username else "",
        "password": unquote(parsed.password) if parsed.password else "",
        "database": db,
        "charset": charset,
        "cursorclass": DictCursor,
        "autocommit": False,
        "connect_timeout": 10,   # 防止 MySQL 连接挂起超过 10s 导致线程池耗尽
        "read_timeout": 30,
        "write_timeout": 30,
    }


def connect_mysql() -> pymysql.connections.Connection:
    settings = get_settings()
    kw = _mysql_connect_kwargs(settings.database_url)
    cursorclass = kw.pop("cursorclass")
    kw["password"] = _pymysql_password_param(kw["password"] or "")
    return pymysql.connect(**kw, cursorclass=cursorclass)


def get_db() -> Generator[pymysql.connections.Connection, None, None]:
    conn = connect_mysql()
    try:
        yield conn
    finally:
        conn.close()
