"""
在 MySQL 表 plant_admin_users 中创建或更新用户（bcrypt 哈希仅存库）。
使用前在 backend 目录配置好 .env 中的 DATABASE_URL，例如：
  cd backend && python create_user.py myuser 'your-password' --role admin
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.auth_utils import hash_password
from app.database import connect_mysql
from app.schemas import normalize_and_validate_username


def main() -> None:
    p = argparse.ArgumentParser(description="创建或更新 plant_admin 用户（密码只写入数据库 hash）")
    p.add_argument("username")
    p.add_argument("password", help="明文密码，仅用于本地生成 bcrypt 后写入数据库")
    p.add_argument("--role", choices=["admin", "user"], default="user")
    p.add_argument(
        "--update",
        action="store_true",
        help="若用户名已存在则重置密码与角色",
    )
    args = p.parse_args()

    try:
        username = normalize_and_validate_username(args.username)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    conn = connect_mysql()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM plant_admin_users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
        if row:
            if not args.update:
                print("用户已存在，请加 --update 以重置密码", file=sys.stderr)
                sys.exit(1)
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE plant_admin_users SET password_hash = %s, role = %s WHERE username = %s",
                    (hash_password(args.password), args.role, username),
                )
            conn.commit()
            print(f"已更新: {username}，角色={args.role}")
        else:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO plant_admin_users (username, password_hash, role) VALUES (%s, %s, %s)",
                    (username, hash_password(args.password), args.role),
                )
                new_id = cur.lastrowid
            conn.commit()
            print(f"已创建: {username} id={new_id} 角色={args.role}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
