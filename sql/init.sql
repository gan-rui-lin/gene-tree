-- Seed demo data for Gene Tree project.
-- Prerequisite:
--   1) Database gene_tree already exists
--   2) Business tables exist (created by migrate, or by schema.sql + migrate app 0001 --fake)
--
-- Run:
--   mysql -u root -p gene_tree < sql/init.sql
--
-- Before running:
--   Replace the two password hash placeholders below.

SET NAMES utf8mb4;
USE `gene_tree`;

SET @ADMIN_PASSWORD_HASH = 'pbkdf2_sha256$720000$demo_admin_salt_2026$akzT5MKRZFPXbU0NJvt1ohKaHbf2kmMDxFXKdY/zA1k=';
SET @EDITOR_PASSWORD_HASH = 'pbkdf2_sha256$720000$demo_editor_salt_2026$iX8V+1CYMDl0x5zA+NOBZtC2C6Qo7kxlb2MDDoQI4Bw=';

START TRANSACTION;

INSERT INTO `user` (
    `user_id`,
    `username`,
    `password`,
    `email`,
    `first_name`,
    `last_name`,
    `is_active`,
    `is_staff`,
    `is_superuser`,
    `date_joined`
) VALUES
    (1, 'demo_admin', @ADMIN_PASSWORD_HASH, 'demo_admin@example.com', '', '', 1, 0, 0, NOW()),
    (2, 'demo_editor', @EDITOR_PASSWORD_HASH, 'demo_editor@example.com', '', '', 1, 0, 0, NOW())
ON DUPLICATE KEY UPDATE
    `password` = VALUES(`password`),
    `email` = VALUES(`email`),
    `first_name` = VALUES(`first_name`),
    `last_name` = VALUES(`last_name`),
    `is_active` = VALUES(`is_active`),
    `is_staff` = VALUES(`is_staff`),
    `is_superuser` = VALUES(`is_superuser`);

INSERT INTO `genealogy` (
    `genealogy_id`,
    `title`,
    `surname`,
    `created_at`,
    `created_by_id`
) VALUES
    (1, '张氏示例族谱', '张', NOW(), 1)
ON DUPLICATE KEY UPDATE
    `title` = VALUES(`title`),
    `surname` = VALUES(`surname`),
    `created_by_id` = VALUES(`created_by_id`);

INSERT INTO `genealogy_user` (
    `genealogy_user_id`,
    `user_id`,
    `genealogy_id`,
    `role`
) VALUES
    (1, 1, 1, 'owner'),
    (2, 2, 1, 'editor')
ON DUPLICATE KEY UPDATE
    `role` = VALUES(`role`);

INSERT INTO `member` (
    `member_id`,
    `genealogy_id`,
    `name`,
    `gender`,
    `birth_year`,
    `death_year`,
    `biography`
) VALUES
    (1001, 1, '张国富', 'M', 1940, NULL, '家族第一代（示例）'),
    (1002, 1, '李秀英', 'F', 1943, NULL, '家族第一代（示例）'),
    (1003, 1, '张建国', 'M', 1968, NULL, '家族第二代（示例）'),
    (1004, 1, '王芳',   'F', 1970, NULL, '家族第二代（示例）'),
    (1005, 1, '张磊',   'M', 1995, NULL, '家族第三代（示例）'),
    (1006, 1, '张敏',   'F', 1998, NULL, '家族第三代（示例）')
ON DUPLICATE KEY UPDATE
    `genealogy_id` = VALUES(`genealogy_id`),
    `name` = VALUES(`name`),
    `gender` = VALUES(`gender`),
    `birth_year` = VALUES(`birth_year`),
    `death_year` = VALUES(`death_year`),
    `biography` = VALUES(`biography`);

INSERT INTO `parent_child` (
    `parent_id`,
    `child_id`,
    `relation_type`
) VALUES
    (1001, 1003, 'father'),
    (1002, 1003, 'mother'),
    (1003, 1005, 'father'),
    (1004, 1005, 'mother'),
    (1003, 1006, 'father'),
    (1004, 1006, 'mother')
ON DUPLICATE KEY UPDATE
    `relation_type` = VALUES(`relation_type`);

INSERT INTO `marriage` (
    `marriage_id`,
    `spouse1_id`,
    `spouse2_id`,
    `start_date`,
    `end_date`,
    `status`
) VALUES
    (1, 1001, 1002, '1965-10-01', NULL, 'active'),
    (2, 1003, 1004, '1992-05-20', NULL, 'active')
ON DUPLICATE KEY UPDATE
    `start_date` = VALUES(`start_date`),
    `end_date` = VALUES(`end_date`),
    `status` = VALUES(`status`);

COMMIT;
