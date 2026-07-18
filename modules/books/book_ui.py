"""
modules/books/book_ui.py

The actual window admin sees for managing books. Doesn't touch the
database directly - calls book_service functions for all of that.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

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

        # keyed by book_id -- populated in _fill_table, used by
        # handle_view_qr to find the right image file for the
        # selected row without adding qr_path as a visible column
        self.book_qr_paths = {}

        # buttons packed first (bottom) so they never get pushed
        # off-screen, same fix as elsewhere. put both in a shared
        # frame so they sit side by side
        bottom_button_frame = tk.Frame(self.window)
        bottom_button_frame.pack(side="bottom", pady=5)

        view_qr_button = tk.Button(
            bottom_button_frame, text="View QR Code", command=self.handle_view_qr
        )
        view_qr_button.pack(side="left", padx=5)

        delete_button = tk.Button(
            bottom_button_frame, text="Delete Selected", command=self.handle_delete
        )
        delete_button.pack(side="left", padx=5)

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
            self.book_qr_paths[book["book_id"]] = book["qr_path"]

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

    def handle_view_qr(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a book first.")
            return

        book_id = self.tree.item(selected[0])["values"][0]
        title = self.tree.item(selected[0])["values"][1]
        qr_path = self.book_qr_paths.get(book_id)

        if not qr_path:
            messagebox.showerror("Error", "No QR code found for this book.")
            return

        try:
            qr_image = Image.open(qr_path)
        except FileNotFoundError:
            messagebox.showerror("Error", f"QR image file is missing: {qr_path}")
            return

        qr_window = tk.Toplevel(self.window)
        qr_window.title(f"QR Code - {title}")

        # keep a reference on the window itself (qr_window.photo = ...)
        # -- without this, Python's garbage collector can clear the
        # image right after this function returns, since nothing else
        # holds onto it, and the label would show up blank
        photo = ImageTk.PhotoImage(qr_image)
        qr_window.photo = photo

        tk.Label(qr_window, image=photo).pack(padx=20, pady=20)