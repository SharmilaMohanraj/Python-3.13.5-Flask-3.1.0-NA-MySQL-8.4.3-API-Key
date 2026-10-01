-- LMS database schema (MySQL 8.4.3)
-- Raw SQL DDL, no ORM. Run once at container startup / migration time.

CREATE DATABASE IF NOT EXISTS lms_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE lms_db;

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(255)        NOT NULL,
    email           VARCHAR(255)        NOT NULL,
    password_hash   VARCHAR(255)        NOT NULL,
    role            ENUM('instructor', 'student') NOT NULL,
    created_at      DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_users_email UNIQUE (email)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- courses
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS courses (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    instructor_id   BIGINT UNSIGNED     NOT NULL,
    title           VARCHAR(255)        NOT NULL,
    description     TEXT,
    category        VARCHAR(120),
    created_at      DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_courses_instructor FOREIGN KEY (instructor_id) REFERENCES users (id) ON DELETE CASCADE,
    INDEX idx_courses_category (category),
    INDEX idx_courses_instructor (instructor_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- modules
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modules (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    course_id       BIGINT UNSIGNED     NOT NULL,
    title           VARCHAR(255)        NOT NULL,
    order_index     INT                 NOT NULL,
    CONSTRAINT fk_modules_course FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
    INDEX idx_modules_course (course_id, order_index)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- lessons
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lessons (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    module_id       BIGINT UNSIGNED     NOT NULL,
    title           VARCHAR(255)        NOT NULL,
    order_index     INT                 NOT NULL,
    CONSTRAINT fk_lessons_module FOREIGN KEY (module_id) REFERENCES modules (id) ON DELETE CASCADE,
    INDEX idx_lessons_module (module_id, order_index)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- enrollments
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS enrollments (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    student_id      BIGINT UNSIGNED     NOT NULL,
    course_id       BIGINT UNSIGNED     NOT NULL,
    enrolled_at     DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status          ENUM('active', 'completed') NOT NULL DEFAULT 'active',
    CONSTRAINT fk_enrollments_student FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_enrollments_course FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
    CONSTRAINT uq_enrollments_student_course UNIQUE (student_id, course_id),
    INDEX idx_enrollments_course (course_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- lesson_progress
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lesson_progress (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    student_id          BIGINT UNSIGNED     NOT NULL,
    lesson_id           BIGINT UNSIGNED     NOT NULL,
    status              ENUM('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED') NOT NULL DEFAULT 'NOT_STARTED',
    module_completed    BOOLEAN             NOT NULL DEFAULT FALSE,
    updated_at          DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_progress_student FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_progress_lesson FOREIGN KEY (lesson_id) REFERENCES lessons (id) ON DELETE CASCADE,
    CONSTRAINT uq_progress_student_lesson UNIQUE (student_id, lesson_id),
    INDEX idx_progress_lesson (lesson_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- certificates
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS certificates (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    student_id      BIGINT UNSIGNED     NOT NULL,
    course_id       BIGINT UNSIGNED     NOT NULL,
    issued_at       DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_certificates_student FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_certificates_course FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
    CONSTRAINT uq_certificates_student_course UNIQUE (student_id, course_id),
    INDEX idx_certificates_student (student_id)
) ENGINE=InnoDB;
