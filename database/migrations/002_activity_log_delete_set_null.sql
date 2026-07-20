-- Migration: allow deleting a user even if they have Activity_Log entries
--
-- Problem: Activity_Log.user_id had a plain foreign key with no ON DELETE
-- behavior specified, which defaults to RESTRICT -- PostgreSQL blocks
-- deleting a user if ANY Activity_Log row references them. Since every
-- login creates an Activity_Log entry, this meant almost no real account
-- could ever be deleted.
--
-- Fix: ON DELETE SET NULL. The log entry survives (audit trail preserved,
-- matching the original design intent from Phase 1), but its user_id
-- becomes NULL instead of blocking the delete. Activity_Log.user_id was
-- already nullable in the schema (no NOT NULL constraint), so this is a
-- safe change -- no existing data needs to change shape.

ALTER TABLE Activity_Log DROP CONSTRAINT activity_log_user_id_fkey;

ALTER TABLE Activity_Log
    ADD CONSTRAINT activity_log_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
    ON DELETE SET NULL;