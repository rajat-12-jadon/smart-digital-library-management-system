"""
modules/reservation/reservation_ui.py

Two windows in this file:
- ReserveBookWindow: what a STUDENT sees -- pick an unavailable book,
  reserve it, and see their own reservation history/status.
- PendingPickupsWindow: what a LIBRARIAN sees -- fulfilled reservations
  waiting to be physically handed over, with an "Issue to Student" button.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from modules.reservation.reservation_service import reserve_book, get_reservations_for_student
from modules.issue_return.issue_service import get_pending_pickups, issue_reserved_book
from modules.books.book_service import get_all_books


class ReserveBookWindow:
    def __init__(self, parent, current_user):
        self.window = tk.Toplevel(parent)
        self.window.title("Reserve a Book")
        self.window.geometry("650x550")
        self.window.minsize(600, 500)

        self.current_user = current_user
        self.book_lookup = {}

        self.build_form()
        self.build_table()

        self.load_dropdown_data()
        self.refresh_table()

    def build_form(self):
        form_frame = tk.Frame(self.window)
        form_frame.pack(pady=15)

        tk.Label(
            form_frame,
            text="Only books with zero copies available can be reserved.\n"
                 "If a book has copies available, ask a librarian to issue it directly.",
            fg="grey", wraplength=500, justify="center",
        ).pack(pady=(0, 10))

        row_frame = tk.Frame(form_frame)
        row_frame.pack()

        tk.Label(row_frame, text="Book:").pack(side="left", padx=5)
        self.book_combo = ttk.Combobox(row_frame, width=40, state="readonly")
        self.book_combo.pack(side="left", padx=5)

        reserve_button = tk.Button(form_frame, text="Reserve Book", command=self.handle_reserve)
        reserve_button.pack(pady=15)

    def build_table(self):
        columns = ("reservation_id", "book", "reservation_date", "status")

        tk.Label(self.window, text="Your Reservations", font=("Arial", 11, "bold")).pack(pady=(10, 0))

        self.tree = ttk.Treeview(self.window, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=130)

        self.tree.pack(pady=10, fill="both", expand=True)

    def load_dropdown_data(self):
        books = get_all_books()
        book_display_names = []
        for book in books:
            # only show books with ZERO available copies -- that's
            # the whole point of reserving, this list is the opposite
            # filter from issue_ui.py's dropdown
            if book["available_quantity"] == 0:
                display = f"{book['title']} by {book['author']}"
                book_display_names.append(display)
                self.book_lookup[display] = book["book_id"]
        self.book_combo["values"] = book_display_names

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        reservations = get_reservations_for_student(self.current_user.user_id)
        for r in reservations:
            self.tree.insert("", "end", values=(
                r["reservation_id"], r["book_title"], r["reservation_date"], r["status"]
            ))

    def handle_reserve(self):
        book_display = self.book_combo.get()
        if not book_display:
            messagebox.showerror("Error", "Select a book first.")
            return

        book_id = self.book_lookup[book_display]

        try:
            reserve_book(self.current_user.user_id, book_id)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        messagebox.showinfo("Success", "Book reserved. You'll be notified when it's your turn.")
        self.book_combo.set("")
        self.load_dropdown_data()
        self.refresh_table()


class PendingPickupsWindow:
    def __init__(self, parent, current_user):
        self.window = tk.Toplevel(parent)
        self.window.title("Pending Reservation Pickups")
        self.window.geometry("650x500")
        self.window.minsize(600, 450)

        self.current_user = current_user  # need librarian_id for the issue record

        self.build_table()
        self.refresh_table()

    def build_table(self):
        columns = ("reservation_id", "student", "book", "reservation_date")

        # button packed first (bottom) so it never gets pushed
        # off-screen when resized -- same fix as other modules
        issue_button = tk.Button(
            self.window, text="Issue to Selected Student", command=self.handle_issue
        )
        issue_button.pack(side="bottom", pady=5)

        self.tree = ttk.Treeview(self.window, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=140)

        self.tree.pack(pady=10, fill="both", expand=True)

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        pickups = get_pending_pickups()
        for p in pickups:
            self.tree.insert("", "end", values=(
                p["reservation_id"], p["student_name"], p["book_title"], p["reservation_date"]
            ))

    def handle_issue(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a reservation first.")
            return

        values = self.tree.item(selected[0])["values"]
        reservation_id = values[0]
        student_name = values[1]
        book_title = values[2]

        confirm = messagebox.askyesno(
            "Confirm Issue", f"Issue '{book_title}' to {student_name}?"
        )
        if not confirm:
            return

        try:
            issue_id, due_date = issue_reserved_book(reservation_id, self.current_user.user_id)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        messagebox.showinfo("Issued", f"Issued. Due date: {due_date}")
        self.refresh_table()