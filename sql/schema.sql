-- Schema snapshot aligned with app/migrations/0001_initial.py (business tables).
-- Notes:
-- 1) This file covers project business tables in app/models.py.
-- 2) Django system tables (auth/contenttypes/admin/sessions/django_migrations)
--    are still managed by `python manage.py migrate`.

CREATE DATABASE IF NOT EXISTS `gene_tree`
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `gene_tree`;

CREATE TABLE IF NOT EXISTS `user` (
    `password` VARCHAR(128) NOT NULL,
    `last_login` DATETIME(6) NULL,
    `is_superuser` BOOLEAN NOT NULL DEFAULT FALSE,
    `username` VARCHAR(150) NOT NULL UNIQUE,
    `first_name` VARCHAR(150) NOT NULL DEFAULT '',
    `last_name` VARCHAR(150) NOT NULL DEFAULT '',
    `is_staff` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `date_joined` DATETIME(6) NOT NULL,
    `user_id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `email` VARCHAR(254) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `genealogy` (
    `genealogy_id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(255) NOT NULL,
    `surname` VARCHAR(100) NOT NULL,
    `created_at` DATETIME(6) NOT NULL,
    `created_by_id` BIGINT NOT NULL,
    CONSTRAINT `fk_genealogy_created_by`
        FOREIGN KEY (`created_by_id`) REFERENCES `user`(`user_id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `genealogy_user` (
    `genealogy_user_id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `genealogy_id` BIGINT NOT NULL,
    `role` VARCHAR(20) NOT NULL,
    CONSTRAINT `fk_genealogy_user_user`
        FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`)
        ON DELETE CASCADE,
    CONSTRAINT `fk_genealogy_user_genealogy`
        FOREIGN KEY (`genealogy_id`) REFERENCES `genealogy`(`genealogy_id`)
        ON DELETE CASCADE,
    CONSTRAINT `uq_genealogy_user_user_genealogy`
        UNIQUE (`user_id`, `genealogy_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `member` (
    `member_id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `genealogy_id` BIGINT NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `gender` CHAR(1) NOT NULL,
    `birth_year` INT UNSIGNED NULL,
    `death_year` INT UNSIGNED NULL,
    `biography` LONGTEXT NOT NULL,
    CONSTRAINT `fk_member_genealogy`
        FOREIGN KEY (`genealogy_id`) REFERENCES `genealogy`(`genealogy_id`)
        ON DELETE CASCADE,
    CONSTRAINT `chk_member_gender`
        CHECK (`gender` IN ('M', 'F'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `parent_child` (
    `parent_id` BIGINT NOT NULL,
    `child_id` BIGINT NOT NULL,
    `relation_type` VARCHAR(10) NOT NULL,
    PRIMARY KEY (`parent_id`, `child_id`),
    CONSTRAINT `fk_parent_child_parent`
        FOREIGN KEY (`parent_id`) REFERENCES `member`(`member_id`)
        ON DELETE CASCADE,
    CONSTRAINT `fk_parent_child_child`
        FOREIGN KEY (`child_id`) REFERENCES `member`(`member_id`)
        ON DELETE CASCADE,
    CONSTRAINT `chk_relation_type`
        CHECK (`relation_type` IN ('father', 'mother')),
    CONSTRAINT `chk_parent_not_self`
        CHECK (`parent_id` <> `child_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `marriage` (
    `marriage_id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `spouse1_id` BIGINT NOT NULL,
    `spouse2_id` BIGINT NOT NULL,
    `start_date` DATE NULL,
    `end_date` DATE NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    CONSTRAINT `fk_marriage_spouse1`
        FOREIGN KEY (`spouse1_id`) REFERENCES `member`(`member_id`)
        ON DELETE CASCADE,
    CONSTRAINT `fk_marriage_spouse2`
        FOREIGN KEY (`spouse2_id`) REFERENCES `member`(`member_id`)
        ON DELETE CASCADE,
    CONSTRAINT `chk_spouse_not_same`
        CHECK (`spouse1_id` <> `spouse2_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_parent ON parent_child(parent_id);
CREATE INDEX idx_child ON parent_child(child_id);
CREATE INDEX idx_parent_child ON parent_child(parent_id, child_id);
CREATE INDEX idx_member_name ON member(name);
