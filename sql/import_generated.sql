-- Import generated datasets (small / medium / large) into gene_tree.
--
-- Prerequisites:
--   1) python manage.py migrate          (create Django system tables)
--   2) mysql -u root -p gene_tree < sql/init.sql  (create users)
--
-- Usage (run from project root):
--   mysql -u root -p -e "SET GLOBAL local_infile = 1;"
--   mysql -u root -p --local-infile=1 gene_tree < sql/import_generated.sql
--
-- This script will:
--   1) Clear ALL existing member / parent_child / marriage data
--   2) Create 3 genealogies: 江氏(small) / 朱氏(medium) / 伍氏(large)
--   3) Import CSV data from sql/generated/{small,medium,large}/

SET NAMES utf8mb4;
USE `gene_tree`;

-- ============================================================
-- 1. Clean existing data (keep users)
-- ============================================================
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE `parent_child`;
TRUNCATE TABLE `marriage`;
TRUNCATE TABLE `member`;
TRUNCATE TABLE `genealogy_user`;
TRUNCATE TABLE `genealogy`;
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 2. Create genealogies and user bindings
-- ============================================================
INSERT INTO `genealogy` (`genealogy_id`, `title`, `surname`, `created_at`, `created_by_id`)
VALUES
    (1, '江氏小型族谱', '江', NOW(), 1),
    (2, '朱氏中型族谱', '朱', NOW(), 1),
    (3, '伍氏大型族谱', '伍', NOW(), 1);

INSERT INTO `genealogy_user` (`user_id`, `genealogy_id`, `role`)
VALUES
    (1, 1, 'owner'), (1, 2, 'owner'), (1, 3, 'owner'),
    (2, 1, 'editor'), (2, 2, 'editor');

-- ============================================================
-- 3. Import CSV data
-- ============================================================
SET FOREIGN_KEY_CHECKS = 0;

-- ---- SMALL (genealogy_id=1, member_id 10000+) ----
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

-- ---- MEDIUM (genealogy_id=2, member_id 20000+) ----
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

-- ---- LARGE (genealogy_id=3, member_id 30000+) ----
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
-- 4. Verify
-- ============================================================
SELECT '=== Import Summary ===' AS info;
SELECT genealogy_id, title, surname, (SELECT COUNT(*) FROM member WHERE genealogy_id = g.genealogy_id) AS members FROM genealogy g ORDER BY genealogy_id;
SELECT COUNT(*) AS total_parent_child FROM parent_child;
SELECT COUNT(*) AS total_marriage FROM marriage;
