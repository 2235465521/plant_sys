-- 数据库用户表字符集与命名规范清洗迁移
-- 规则：
-- 1. 将包含下划线的测试管理员账号 test_admin 重命名为规范的 testadmin
-- 2. 将非纯字母数字/乱码历史临时账号更名（严格符合 ^[a-z0-9]+$）并停用（is_active = 0）
SET NAMES utf8mb4;

UPDATE plant_admin_users
SET username = 'testadmin'
WHERE username = 'test_admin';

UPDATE plant_admin_users
SET username = CONCAT('legacy', id), is_active = 0
WHERE username NOT REGEXP '^[a-zA-Z0-9]+$';
