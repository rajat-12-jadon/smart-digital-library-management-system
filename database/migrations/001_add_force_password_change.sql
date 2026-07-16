-- Migration: add force_password_change flag to Users
--
-- Why this is a separate migration file instead of just editing
-- schema.sql: schema.sql was already run once against the live
-- database in Phase 1. Editing it now wouldn't retroactively add
-- the column to a database that already exists -- ALTER TABLE is
-- what actually changes an existing database. schema.sql is also
-- updated (see below) so a completely FRESH install includes this
-- column from the start, but this migration is what you actually
-- run against the current database.

ALTER TABLE Users
    ADD COLUMN force_password_change BOOLEAN NOT NULL DEFAULT FALSE;

-- existing accounts (the admin/librarian you already created) don't
-- need to be forced to change their password retroactively -- only
-- NEW accounts created going forward will have this set to TRUE
-- (that happens in register_student() / register_librarian(), not here)