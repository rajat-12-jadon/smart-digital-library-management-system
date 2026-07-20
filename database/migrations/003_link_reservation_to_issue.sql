-- Migration: link Reservation directly to the Book_Issue that collected it
--
-- Problem: get_pending_pickups() / get_reservations_ready_for_pickup()
-- guessed whether a fulfilled reservation was "collected" by checking
-- for a CURRENTLY 'issued' Book_Issue matching the same student+book.
-- That guess breaks once the book is returned again later -- the
-- issue record's status flips to 'returned', so the reservation looks
-- "never collected" again, even though it genuinely was. Found this
-- through testing a two-student reservation queue scenario.
--
-- Fix: an explicit link. Once a reservation is fulfilled AND actually
-- handed over (issue_reserved_book()), we record WHICH issue did it.
-- "Ready for pickup" then means status='fulfilled' AND issue_id IS
-- NULL -- no more guessing from unrelated tables.

ALTER TABLE Reservation
    ADD COLUMN issue_id INTEGER REFERENCES Book_Issue(issue_id);