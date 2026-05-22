-- 可选：本地/演示用初始账号（生产环境请勿执行本文件；请用 backend/create_user.py 按需建号）
-- 表结构须先由 extend_system_tables.sql 创建
SET NAMES utf8mb4;

INSERT INTO plant_admin_users (username, password_hash, role)
VALUES (
    'admin',
    '$2b$12$hUAoMZBd/6Mkc1gkR44kfuk6jWRldKwtDHe2dBuXB.cvLM7leegse',
    'admin'
) ON DUPLICATE KEY UPDATE username = username;

INSERT INTO plant_admin_users (username, password_hash, role)
VALUES (
    'viewer',
    '$2b$12$QWX6UMRPaLF/508Mm7FyEOylDBCLs5sACi2OSDhamVu/DhlTqVUoC',
    'user'
) ON DUPLICATE KEY UPDATE username = username;
