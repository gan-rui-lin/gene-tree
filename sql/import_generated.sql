-- Import generated datasets (small / medium / large) into gene_tree.
--
-- Prerequisites:
--   1) mysql -u root -p < sql/schema.sql   (or run migrate first)
--   2) mysql -u root -p gene_tree < sql/init.sql  (users + genealogy 1)
--
-- Usage (run from project root directory):
--   mysql -u root -p --local-infile=1 gene_tree < sql/import_generated.sql
--
-- This script:
--   - Creates genealogy records for id=2 (medium) and id=3 (large)
--   - Links demo_admin to all three genealogies as owner
--   - Loads CSV data from sql/generated/{small,medium,large}/

SET NAMES utf8mb4;
USE `gene_tree`;

-- ============================================================
-- 1. Create genealogy records (id=1 already from init.sql)
-- ============================================================
INSERT INTO `genealogy` (`genealogy_id`, `title`, `surname`, `created_at`, `created_by_id`)
VALUES
    (1, '江氏小型族谱', '江', NOW(), 1),
    (2, '朱氏中型族谱', '朱', NOW(), 1),
    (3, '伍氏大型族谱', '伍', NOW(), 1)
ON DUPLICATE KEY UPDATE `title` = VALUES(`title`), `surname` = VALUES(`surname`);

-- Link users to genealogies
INSERT INTO `genealogy_user` (`user_id`, `genealogy_id`, `role`)
VALUES (1, 1, 'owner'), (1, 2, 'owner'), (1, 3, 'owner'), (2, 1, 'editor')
ON DUPLICATE KEY UPDATE `role` = VALUES(`role`);

-- ============================================================
-- 2. Import CSV data
-- ============================================================
SET FOREIGN_KEY_CHECKS = 0;

-- ---- SMALL (genealogy_id=1, member_id 10000~10499) ----
LOAD DATA LOCAL INFILE 'sql/generated/small/member.csv'
INTO TABLE `member` FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 ROWS
(`member_id`, `genealogy_id`, `name`, `gender`, `birth_year`, @death_year, `biography`)
SET `death_year` = NULLIF(@death_year, '');

LOAD DATA LOCAL INFILE 'sql/generated/small/parent_child.csv'
INTO TABLE `parent_child` FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 ROWS
(`parent_id`, `child_id`, `relation_type`);

LOAD DATA LOCAL INFILE 'sql/generated/small/marriage.csv'
INTO TABLE `marriage` FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 ROWS
(`marriage_id`, `spouse1_id`, `spouse2_id`, @start_date, @end_date, `status`)
SET `start_date` = NULLIF(@start_date, ''),
    `end_date`   = NULLIF(@end_date, '');

-- ---- MEDIUM (genealogy_id=2, member_id 20000~24999) ----
LOAD DATA LOCAL INFILE 'sql/generated/medium/member.csv'
INTO TABLE `member` FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 ROWS
(`member_id`, `genealogy_id`, `name`, `gender`, `birth_year`, @death_year, `biography`)
SET `death_year` = NULLIF(@death_year, '');

LOAD DATA LOCAL INFILE 'sql/generated/medium/parent_child.csv'
INTO TABLE `parent_child` FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 ROWS
(`parent_id`, `child_id`, `relation_type`);

LOAD DATA LOCAL INFILE 'sql/generated/medium/marriage.csv'
INTO TABLE `marriage` FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 ROWS
(`marriage_id`, `spouse1_id`, `spouse2_id`, @start_date, @end_date, `status`)
SET `start_date` = NULLIF(@start_date, ''),
    `end_date`   = NULLIF(@end_date, '');

-- ---- LARGE (genealogy_id=3, member_id 30000~79999) ----
LOAD DATA LOCAL INFILE 'sql/generated/large/member.csv'
INTO TABLE `member` FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 ROWS
(`member_id`, `genealogy_id`, `name`, `gender`, `birth_year`, @death_year, `biography`)
SET `death_year` = NULLIF(@death_year, '');

LOAD DATA LOCAL INFILE 'sql/generated/large/parent_child.csv'
INTO TABLE `parent_child` FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 ROWS
(`parent_id`, `child_id`, `relation_type`);

LOAD DATA LOCAL INFILE 'sql/generated/large/marriage.csv'
INTO TABLE `marriage` FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n' IGNORE 1 ROWS
(`marriage_id`, `spouse1_id`, `spouse2_id`, @start_date, @end_date, `status`)
SET `start_date` = NULLIF(@start_date, ''),
    `end_date`   = NULLIF(@end_date, '');

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 3. Verify
-- ============================================================
SELECT '=== Import Summary ===' AS info;
SELECT genealogy_id, COUNT(*) AS members FROM member GROUP BY genealogy_id ORDER BY genealogy_id;
SELECT COUNT(*) AS total_parent_child FROM parent_child;
SELECT COUNT(*) AS total_marriage FROM marriage;
