-- =============================================================================
-- Smart Digital Library Management System — Database Schema
-- Phase 1: Database
--
-- Run this once against a fresh PostgreSQL database to create all tables.
-- Kept as a standalone .sql file (rather than only Python-generated DDL)
-- so it can be reviewed, versioned, and run independently via psql,
-- pgAdmin, or a migration tool later if the project grows.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- ENUM types
-- Using real Postgres ENUMs instead of free-text columns so invalid values
-- (typos like 'stuedent') are rejected at the database level, not just in
-- application code.
-- ---------------------------------------------------------------------------
CREATE TYPE user_role AS ENUM ('admin', 'librarian', 'student');
CREATE TYPE issue_status AS ENUM ('issued', 'returned', 'overdue');
CREATE TYPE reservation_status AS ENUM ('pending', 'fulfilled', 'cancelled');

-- ---------------------------------------------------------------------------
-- Users
-- Holds Admin, Librarian, and Student accounts in one table (role-based).
-- Alternative would be separate tables per role, but that complicates
-- foreign keys in Book_Issue/Reservation (which reference "a person"
-- regardless of role) and Activity_Log. Single table + role column is
-- the simpler, more maintainable choice here.
-- ---------------------------------------------------------------------------
CREATE TABLE Users (
    user_id      SERIAL PRIMARY KEY,
    name         VARCHAR(150) NOT NULL,
    email        VARCHAR(150) NOT NULL UNIQUE,
    phone        VARCHAR(20),
    password     VARCHAR(255) NOT NULL,   -- stores bcrypt hash, never plaintext
    role         user_role NOT NULL,
    force_password_change BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE for accounts created by an admin/librarian on someone else's behalf
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Books
-- ---------------------------------------------------------------------------
CREATE TABLE Books (
    book_id             SERIAL PRIMARY KEY,
    title               VARCHAR(255) NOT NULL,
    author              VARCHAR(255) NOT NULL,
    category            VARCHAR(100),
    publisher           VARCHAR(150),
    isbn                VARCHAR(20) UNIQUE,
    edition             VARCHAR(50),
    total_quantity      INTEGER NOT NULL DEFAULT 0 CHECK (total_quantity >= 0),
    available_quantity  INTEGER NOT NULL DEFAULT 0 CHECK (available_quantity >= 0),
    book_cover          VARCHAR(255),   -- file path under assets/images
    pdf_path            VARCHAR(255),
    qr_path             VARCHAR(255),   -- file path under assets/qr_codes
    CONSTRAINT available_not_exceed_total
        CHECK (available_quantity <= total_quantity)
);

-- ---------------------------------------------------------------------------
-- Book_Issue
-- ---------------------------------------------------------------------------
CREATE TABLE Book_Issue (
    issue_id      SERIAL PRIMARY KEY,
    student_id    INTEGER NOT NULL REFERENCES Users(user_id),
    librarian_id  INTEGER NOT NULL REFERENCES Users(user_id),
    book_id       INTEGER NOT NULL REFERENCES Books(book_id),
    issue_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date      DATE NOT NULL,
    return_date   DATE,
    status        issue_status NOT NULL DEFAULT 'issued'
);

-- ---------------------------------------------------------------------------
-- Reservation
-- ---------------------------------------------------------------------------
CREATE TABLE Reservation (
    reservation_id    SERIAL PRIMARY KEY,
    student_id        INTEGER NOT NULL REFERENCES Users(user_id),
    book_id           INTEGER NOT NULL REFERENCES Books(book_id),
    reservation_date  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status            reservation_status NOT NULL DEFAULT 'pending'
);

-- ---------------------------------------------------------------------------
-- Fine
-- ---------------------------------------------------------------------------
CREATE TABLE Fine (
    fine_id       SERIAL PRIMARY KEY,
    issue_id      INTEGER NOT NULL REFERENCES Book_Issue(issue_id),
    late_days     INTEGER NOT NULL CHECK (late_days >= 0),
    fine_amount   NUMERIC(10, 2) NOT NULL CHECK (fine_amount >= 0),
    paid          BOOLEAN NOT NULL DEFAULT FALSE
);

-- ---------------------------------------------------------------------------
-- Activity_Log
-- ---------------------------------------------------------------------------
CREATE TABLE Activity_Log (
    log_id      SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES Users(user_id),
    action      VARCHAR(255) NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Indexes
-- Added on foreign keys and commonly-searched columns. Postgres does NOT
-- auto-index foreign key columns (unlike primary keys), so without these,
-- joins in Issue/Return/Reservation flows would degrade as data grows.
-- ---------------------------------------------------------------------------
CREATE INDEX idx_bookissue_student   ON Book_Issue(student_id);
CREATE INDEX idx_bookissue_book      ON Book_Issue(book_id);
CREATE INDEX idx_reservation_book    ON Reservation(book_id);
CREATE INDEX idx_reservation_student ON Reservation(student_id);
CREATE INDEX idx_books_title         ON Books(title);
CREATE INDEX idx_books_author        ON Books(author);
CREATE INDEX idx_activitylog_user    ON Activity_Log(user_id);