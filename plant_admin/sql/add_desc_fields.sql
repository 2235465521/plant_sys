-- 添加时令描述字段
SET NAMES utf8mb4;

ALTER TABLE plant_classification_import
ADD COLUMN harvest_months_desc TEXT DEFAULT NULL COMMENT '最佳采收月份详细说明',
ADD COLUMN food_therapy_months_desc TEXT DEFAULT NULL COMMENT '适合食疗入药月份详细说明';
