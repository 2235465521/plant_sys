-- 扩展功能数据库表结构
SET NAMES utf8mb4;

-- 1. 为现有植物表添加时令药材月份字段（逗号分隔的月份数字，例如 "8,9,10"）
ALTER TABLE plant_classification_import
ADD COLUMN harvest_months VARCHAR(128) DEFAULT NULL COMMENT '最佳采收月，逗号分隔，如 8,9',
ADD COLUMN food_therapy_months VARCHAR(128) DEFAULT NULL COMMENT '适合食疗入药月，逗号分隔，如 5,6';

-- 2. 新增别称系统表
CREATE TABLE IF NOT EXISTS plant_aliases (
    id BIGINT NOT NULL AUTO_INCREMENT,
    plant_id BIGINT NOT NULL COMMENT '关联的植物ID',
    alias_type VARCHAR(64) NOT NULL COMMENT '别名类型（药典标准名、古书古名、民间通用俗称、各地方言名、药房处方名、市场商品名、易混淆错用名）',
    alias_name VARCHAR(128) NOT NULL COMMENT '别名内容',
    origin_desc TEXT DEFAULT NULL COMMENT '简单由来说明',
    PRIMARY KEY (id),
    KEY idx_plant_aliases_plant_id (plant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='中药材分类别名系统';

-- 3. 新增场景分类表
CREATE TABLE IF NOT EXISTS plant_habitats (
    id BIGINT NOT NULL AUTO_INCREMENT,
    plant_id BIGINT NOT NULL COMMENT '关联的植物ID',
    habitat_type VARCHAR(64) NOT NULL COMMENT '场景分类（海产类、水边湿地类、山林山地类、平原田间类、荒漠耐旱类等）',
    PRIMARY KEY (id),
    KEY idx_plant_habitats_plant_id (plant_id),
    UNIQUE KEY uq_plant_habitats (plant_id, habitat_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='植物场景分类关联';

-- 4. 新增特色排行榜数据
CREATE TABLE IF NOT EXISTS plant_rankings (
    id BIGINT NOT NULL AUTO_INCREMENT,
    plant_id BIGINT NOT NULL,
    ranking_type VARCHAR(64) NOT NULL COMMENT '榜单维度（如：最甜药材、最苦药材、珍贵程度、生长周期等）',
    ranking_value VARCHAR(128) DEFAULT NULL COMMENT '排名或具体数值/标签',
    description TEXT DEFAULT NULL COMMENT '上榜理由或描述',
    PRIMARY KEY (id),
    KEY idx_plant_rankings_plant_id (plant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='中药材特色排行榜';

-- 5. 新增各省代表道地药材关联
CREATE TABLE IF NOT EXISTS plant_regions (
    id BIGINT NOT NULL AUTO_INCREMENT,
    plant_id BIGINT NOT NULL,
    region_name VARCHAR(64) NOT NULL COMMENT '省份名称，如：浙江、河南',
    combo_name VARCHAR(64) DEFAULT NULL COMMENT '经典组合名称，如：浙八味、四大怀药',
    PRIMARY KEY (id),
    KEY idx_plant_regions_plant_id (plant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='道地药材与地区关联';

-- 6. 新增易混淆、同名异物专题组
CREATE TABLE IF NOT EXISTS plant_confusion_groups (
    id BIGINT NOT NULL AUTO_INCREMENT,
    group_name VARCHAR(128) NOT NULL COMMENT '专题名称，如：五种“胡”',
    description TEXT DEFAULT NULL COMMENT '专题介绍',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='易混淆专题组';

-- 7. 易混淆组成员
CREATE TABLE IF NOT EXISTS plant_confusion_items (
    id BIGINT NOT NULL AUTO_INCREMENT,
    group_id BIGINT NOT NULL,
    plant_id BIGINT NOT NULL,
    distinguish_point TEXT DEFAULT NULL COMMENT '与其他药材的区别要点/辨识特征',
    PRIMARY KEY (id),
    KEY idx_plant_confusion_items_group (group_id),
    KEY idx_plant_confusion_items_plant (plant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='易混淆专题成员植物';
