-- 在中国植物库业务库中执行（与 plant_classification_import 同库）
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS plant_admin_users (
    id              BIGINT NOT NULL AUTO_INCREMENT,
    username        VARCHAR(64) NOT NULL COMMENT '登录名',
    password_hash   VARCHAR(255) NOT NULL COMMENT 'bcrypt',
    role            ENUM('admin', 'user') NOT NULL DEFAULT 'user',
    is_active       TINYINT(1) NOT NULL DEFAULT 1,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_plant_admin_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='后台登录用户';

CREATE TABLE IF NOT EXISTS plant_export_logs (
    id              BIGINT NOT NULL AUTO_INCREMENT,
    plant_id        BIGINT DEFAULT NULL COMMENT '物种 id',
    plant_name      VARCHAR(256) DEFAULT NULL COMMENT '导出时中文名快照',
    user_id         BIGINT NOT NULL,
    username        VARCHAR(64) NOT NULL COMMENT '导出时用户名快照',
    export_format   VARCHAR(16) NOT NULL DEFAULT 'json',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_plant_export_logs_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='物种信息与本站图片下载等导出审计（全员可查列表）';

-- 用户数据请写入表 plant_admin_users，勿在应用代码中写死账号密码。
-- 建号方式：在 backend 目录执行 python create_user.py <用户名> <密码> [--role admin|user]
-- 若需要现成演示账号（不推荐用于生产），可另外执行 sql/seed_demo_users.sql
