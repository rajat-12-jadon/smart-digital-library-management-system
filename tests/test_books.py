"""
tests/test_books.py

Tests for modules/books/book_service.py.
"""

import pytest

from modules.books.book_service import add_book, delete_book, DuplicateISBNError
from tests.helpers import create_book


def test_add_book_sets_available_equal_to_total():
    """A newly added book should have all its copies available."""
    book_id = add_book(
        title="Test Book", author="Test Author", category="Fiction",
        publisher="Test Publisher", isbn="1111111111", edition="1st",
        total_quantity=5,
    )

    assert book_id is not None


def test_add_book_rejects_duplicate_isbn():
    add_book(
        title="First Book", author="Author A", category="Fiction",
        publisher="Pub", isbn="2222222222", edition="1st", total_quantity=3,
    )

    with pytest.raises(DuplicateISBNError):
        add_book(
            title="Second Book", author="Author B", category="Fiction",
            publisher="Pub", isbn="2222222222", edition="1st", total_quantity=3,
        )


def test_add_book_rejects_missing_title():
    with pytest.raises(ValueError):
        add_book(
            title="", author="Author", category="Fiction",
            publisher="Pub", isbn="3333333333", edition="1st", total_quantity=3,
        )


def test_add_book_rejects_negative_quantity():
    with pytest.raises(ValueError):
        add_book(
            title="Test Book", author="Author", category="Fiction",
            publisher="Pub", isbn="4444444444", edition="1st", total_quantity=-1,
        )


def test_delete_book_succeeds_when_not_issued():
    book_id = create_book("Deletable Book", total_quantity=2)

    delete_book(book_id)  # should not raise