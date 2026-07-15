"""
modules/books/book_ui.py

The actual window admin sees for managing books. Doesn't touch the
database directly - calls book_service functions for all of that.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from modules.books.book_service import (
    add_book,
    get_all_books,
    search_books,
    delete_book,
    DuplicateISBNError,
)


class BookManagementWindow:
    def __init__(self, parent):
        # parent is the dashboard window this was opened from
        self.window = tk.Toplevel(parent)
        self.window.title("Manage Books")
        self.window.geometry("700x750")
        self.window.minsize(650, 650)  # so it can't get shrunk small enough to cut off buttons

        self.build_form()
        self.build_search_bar()
        self.build_table()

        self.refresh_table()

    def build_form(self):
        form_frame = tk.Frame(self.window)
        form_frame.pack(pady=10)

        # each field gets a label + entry side by side, using grid()
        # here instead of pack() since it's a proper form layout
        labels = ["Title", "Author", "Category", "Publisher", "ISBN", "Edition", "Quantity"]
        self.entries = {}

        for i, label_text in enumerate(labels):
            label = tk.Label(form_frame, text=label_text + ":")
            label.grid(row=i, column=0, sticky="e", padx=5, pady=3)

            entry = tk.Entry(form_frame, width=35)
            entry.grid(row=i, column=1, padx=5, pady=3)

            self.entries[label_text] = entry

        add_button = tk.Button(form_frame, text="Add Book", command=self.handle_add_book)
        add_button.grid(row=len(labels), column=0, columnspan=2, pady=10)

    def build_search_bar(self):
        search_frame = tk.Frame(self.window)
        search_frame.pack(pady=5)

        tk.Label(search_frame, text="Search:").pack(side="left", padx=5)

        self.search_entry = tk.Entry(search_frame, width=30)
        self.search_entry.pack(side="left", padx=5)

        search_button = tk.Button(search_frame, text="Search", command=self.handle_search)
        search_button.pack(side="left", padx=5)

        clear_button = tk.Button(search_frame, text="Clear", command=self.handle_clear_search)
        clear_button.pack(side="left", padx=5)

    def build_table(self):
        columns = ("book_id", "title", "author", "isbn", "total", "available")

        # pack the delete button at the bottom FIRST, so it always
        # reserves its own space no matter how small the window gets.
        # if the treeview (which expands to fill space) is packed
        # first, it can push this button off-screen when resized.
        delete_button = tk.Button(
            self.window, text="Delete Selected", command=self.handle_delete
        )
        delete_button.pack(side="bottom", pady=5)

        self.tree = ttk.Treeview(self.window, columns=columns, show="headings", height=8)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=100)

        self.tree.pack(pady=10, fill="both", expand=True)

    def refresh_table(self):
        # wipe whatever's currently shown and reload everything fresh
        for row in self.tree.get_children():
            self.tree.delete(row)

        books = get_all_books()
        self._fill_table(books)

    def handle_search(self):
        keyword = self.search_entry.get().strip()
        if not keyword:
            self.refresh_table()
            return

        for row in self.tree.get_children():
            self.tree.delete(row)

        books = search_books(keyword)
        self._fill_table(books)

    def handle_clear_search(self):
        # clear button should empty the search box too, not just
        # refresh the table -- otherwise old text just sits there
        self.search_entry.delete(0, tk.END)
        self.refresh_table()

    def _fill_table(self, books):
        for book in books:
            self.tree.insert("", "end", values=(
                book["book_id"],
                book["title"],
                book["author"],
                book["isbn"],
                book["total_quantity"],
                book["available_quantity"],
            ))

    def handle_add_book(self):
        title = self.entries["Title"].get().strip()
        author = self.entries["Author"].get().strip()
        category = self.entries["Category"].get().strip()
        publisher = self.entries["Publisher"].get().strip()
        isbn = self.entries["ISBN"].get().strip()
        edition = self.entries["Edition"].get().strip()
        quantity_text = self.entries["Quantity"].get().strip()

        if not title or not author:
            messagebox.showerror("Error", "Title and Author are required.")
            return

        try:
            quantity = int(quantity_text)
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a number.")
            return

        try:
            add_book(title, author, category, publisher, isbn, edition, quantity)
        except DuplicateISBNError as e:
            messagebox.showerror("Error", str(e))
            return
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        messagebox.showinfo("Success", f"'{title}' added successfully.")
        self.clear_form()
        self.refresh_table()

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)

    def handle_delete(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a book first.")
            return

        # first column in the row is book_id
        book_id = self.tree.item(selected[0])["values"][0]
        title = self.tree.item(selected[0])["values"][1]

        confirm = messagebox.askyesno(
            "Confirm Delete", f"Delete '{title}'? This can't be undone."
        )
        if not confirm:
            return

        try:
            delete_book(book_id)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        messagebox.showinfo("Deleted", f"'{title}' was deleted.")
        self.refresh_table()