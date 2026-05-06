CREATE TABLE `user` (
    `user_id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `username` VARCHAR(150) NOT NULL UNIQUE,
    `password` VARCHAR(255) NOT NULL,
    `email` VARCHAR(254) NOT NULL UNIQUE,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `is_staff` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_superuser` BOOLEAN NOT NULL DEFAULT FALSE,
    `date_joined` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `genealogy` (
    `genealogy_id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(255) NOT NULL,
    `surname` VARCHAR(100) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `created_by_id` BIGINT NOT NULL,
    CONSTRAINT `fk_genealogy_created_by`
        FOREIGN KEY (`created_by_id`) REFERENCES `user`(`user_id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `genealogy_user` (
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

CREATE TABLE `member` (
    `member_id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `genealogy_id` BIGINT NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `gender` CHAR(1) NOT NULL,
    `birth_year` INT NULL,
    `death_year` INT NULL,
    `biography` TEXT NULL,
    CONSTRAINT `fk_member_genealogy`
        FOREIGN KEY (`genealogy_id`) REFERENCES `genealogy`(`genealogy_id`)
        ON DELETE CASCADE,
    CONSTRAINT `chk_member_gender`
        CHECK (`gender` IN ('M', 'F'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `parent_child` (
    `parent_child_id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `parent_id` BIGINT NOT NULL,
    `child_id` BIGINT NOT NULL,
    `relation_type` VARCHAR(10) NOT NULL,
    CONSTRAINT `fk_parent_child_parent`
        FOREIGN KEY (`parent_id`) REFERENCES `member`(`member_id`)
        ON DELETE CASCADE,
    CONSTRAINT `fk_parent_child_child`
        FOREIGN KEY (`child_id`) REFERENCES `member`(`member_id`)
        ON DELETE CASCADE,
    CONSTRAINT `uq_parent_child` UNIQUE (`parent_id`, `child_id`),
    CONSTRAINT `chk_relation_type` CHECK (`relation_type` IN ('father', 'mother')),
    CONSTRAINT `chk_parent_not_self` CHECK (`parent_id` <> `child_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `marriage` (
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
    CONSTRAINT `chk_spouse_not_same` CHECK (`spouse1_id` <> `spouse2_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_parent ON parent_child(parent_id);
CREATE INDEX idx_child ON parent_child(child_id);
CREATE INDEX idx_parent_child ON parent_child(parent_id, child_id);
CREATE INDEX idx_member_name ON member(name);
