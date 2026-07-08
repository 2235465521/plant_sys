import os
import re
import pymysql
from pathlib import Path

def load_env():
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

def get_db_connection():
    db_url = os.getenv("DATABASE_URL", "")
    if db_url:
        match = re.search(r"mysql\+pymysql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/([^?]+)", db_url)
        if match:
            user, password, host, port, dbname = match.groups()
            port = int(port) if port else 3306
            dbname = dbname.split('?')[0]
            return pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=dbname,
                charset='utf8mb4'
            )
    return pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="lsj223546",
        database="plant_db",
        charset='utf8mb4'
    )

def main():
    load_env()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Check if medicinal_part already exists
            cur.execute("SHOW COLUMNS FROM plant_classification_import LIKE 'medicinal_part'")
            result = cur.fetchone()
            if result:
                print("Column 'medicinal_part' already exists. Skip.")
            else:
                cur.execute("""
                    ALTER TABLE plant_classification_import 
                    ADD COLUMN medicinal_part VARCHAR(255) DEFAULT NULL COMMENT '入药部位（如：全草、根、叶）'
                """)
                conn.commit()
                print("Successfully added column 'medicinal_part' to plant_classification_import.")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
