"""
modules/issue_return/issue_ui.py

Window the librarian uses to issue a book to a student. Uses
ttk.Combobox (a dropdown) for picking student/book instead of typing
free text -- avoids typos and makes sure only real students/books can
be selected.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from modules.issue_return.issue_service import (
    issue_book, return_book, get_active_issues, get_active_issue_ids_for_book,
)
from modules.students.student_service import get_all_students
from modules.books.book_service import get_all_books
from utils.qr_utils import scan_qr_code


class IssueBookWindow:
    def __init__(self, parent, current_user):
        self.window = tk.Toplevel(parent)
        self.window.title("Issue Book")
        self.window.geometry("700x600")
        self.window.minsize(650, 550)

        self.current_user = current_user  # need librarian_id for the issue record

        # these hold the actual DB rows behind the dropdown text, so
        # we can map "what the librarian sees" back to a real book_id
        # / student user_id. keyed by the exact string shown in the
        # dropdown.
        self.student_lookup = {}
        self.book_lookup = {}

        self.build_form()
        self.build_table()

        self.load_dropdown_data()
        self.refresh_table()

    def build_form(self):
        form_frame = tk.Frame(self.window)
        form_frame.pack(pady=15)

        tk.Label(form_frame, text="Student:").grid(row=0, column=0, sticky="e", padx=5, pady=8)
        self.student_combo = ttk.Combobox(form_frame, width=40, state="readonly")
        self.student_combo.grid(row=0, column=1, padx=5, pady=8)

        tk.Label(form_frame, text="Book:").grid(row=1, column=0, sticky="e", padx=5, pady=8)
        self.book_combo = ttk.Combobox(form_frame, width=40, state="readonly")
        self.book_combo.grid(row=1, column=1, padx=5, pady=8)

        scan_qr_button = tk.Button(form_frame, text="Scan QR", command=self.handle_scan_qr)
        scan_qr_button.grid(row=1, column=2, padx=5, pady=8)

        issue_button = tk.Button(form_frame, text="Issue Book", command=self.handle_issue)
        issue_button.grid(row=2, column=0, columnspan=2, pady=15)

    def build_table(self):
        columns = ("issue_id", "student", "book", "issue_date", "due_date", "issued_by")

        tk.Label(self.window, text="Currently Issued Books", font=("Arial", 11, "bold")).pack(pady=(10, 0))

        # both buttons packed first (bottom) so they never get pushed
        # off-screen when the window is resized smaller -- same fix
        # as book_ui.py and student_ui.py. shared frame so they sit
        # side by side instead of stacking
        bottom_button_frame = tk.Frame(self.window)
        bottom_button_frame.pack(side="bottom", pady=5)

        scan_return_button = tk.Button(
            bottom_button_frame, text="Scan QR to Return", command=self.handle_scan_return
        )
        scan_return_button.pack(side="left", padx=5)

        return_button = tk.Button(
            bottom_button_frame, text="Return Selected", command=self.handle_return
        )
        return_button.pack(side="left", padx=5)

        self.tree = ttk.Treeview(self.window, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=120)

        self.tree.pack(pady=10, fill="both", expand=True)

    def load_dropdown_data(self):
        students = get_all_students()
        student_display_names = []
        for student in students:
            # "name (email)" shown in dropdown -- email disambiguates
            # if two students happen to share a name
            display = f"{student['name']} ({student['email']})"
            student_display_names.append(display)
            self.student_lookup[display] = student["user_id"]
        self.student_combo["values"] = student_display_names

        books = get_all_books()
        book_display_names = []
        self.book_id_to_display = {}  # reverse of book_lookup, needed by handle_scan_qr
        for book in books:
            # only show books that actually have a copy available --
            # no point letting the librarian pick something they can't issue
            if book["available_quantity"] > 0:
                display = f"{book['title']} (available: {book['available_quantity']})"
                book_display_names.append(display)
                self.book_lookup[display] = book["book_id"]
                self.book_id_to_display[book["book_id"]] = display
        self.book_combo["values"] = book_display_names

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        issues = get_active_issues()
        for issue in issues:
            self.tree.insert("", "end", values=(
                issue["issue_id"],
                issue["student_name"],
                issue["book_title"],
                issue["issue_date"],
                issue["due_date"],
                issue["librarian_name"],
            ))

    def handle_scan_qr(self):
        # this BLOCKS while the camera window is open (see
        # scan_qr_code's docstring) -- the whole Tkinter app will be
        # unresponsive until the librarian scans something or presses
        # Esc to cancel. Fine for a single button click like this.
        messagebox.showinfo(
            "Scan QR", "Camera will open. Show the book's QR code, or press Esc to cancel."
        )

        try:
            book_id = scan_qr_code()
        except RuntimeError as e:
            messagebox.showerror("Camera Error", str(e))
            return

        if book_id is None:
            messagebox.showinfo("Cancelled", "No QR code was scanned.")
            return

        display = self.book_id_to_display.get(book_id)
        if display is None:
            # scanned a real book, but it's not in the dropdown --
            # meaning it has zero available copies right now
            messagebox.showerror(
                "Error", "This book was scanned but currently has no available copies."
            )
            return

        self.book_combo.set(display)

    def handle_scan_return(self):
        messagebox.showinfo(
            "Scan QR", "Camera will open. Show the book's QR code, or press Esc to cancel."
        )

        try:
            book_id = scan_qr_code()
        except RuntimeError as e:
            messagebox.showerror("Camera Error", str(e))
            return

        if book_id is None:
            messagebox.showinfo("Cancelled", "No QR code was scanned.")
            return

        matching_issue_ids = get_active_issue_ids_for_book(book_id)

        if len(matching_issue_ids) == 0:
            messagebox.showerror("Error", "No active issue found for this book.")
            return

        # clear any existing selection first
        self.tree.selection_remove(self.tree.selection())

        if len(matching_issue_ids) == 1:
            # exactly one match -- find that row in the table and
            # select it automatically, so the librarian just needs to
            # confirm by clicking "Return Selected"
            target_issue_id = matching_issue_ids[0]
            for item in self.tree.get_children():
                if self.tree.item(item)["values"][0] == target_issue_id:
                    self.tree.selection_set(item)
                    self.tree.see(item)  # scrolls to it if not currently visible
                    break
            messagebox.showinfo(
                "Found", "Matching issue selected below. Click 'Return Selected' to confirm."
            )
        else:
            # multiple students currently have this book -- can't
            # guess which physical copy this is. Instead of just
            # telling the librarian the count, highlight EVERY
            # matching row so they're immediately visible -- clicking
            # any single one of them narrows the selection down to
            # just that row, ready for "Return Selected"
            matching_items = []
            for item in self.tree.get_children():
                if self.tree.item(item)["values"][0] in matching_issue_ids:
                    matching_items.append(item)

            self.tree.selection_set(matching_items)
            if matching_items:
                self.tree.see(matching_items[0])

            messagebox.showinfo(
                "Multiple Matches",
                f"{len(matching_issue_ids)} students currently have this book issued -- "
                "all of them are highlighted below. Click on the correct student's row, "
                "then click 'Return Selected'.",
            )

    def handle_issue(self):
        student_display = self.student_combo.get()
        book_display = self.book_combo.get()

        if not student_display or not book_display:
            messagebox.showerror("Error", "Select both a student and a book.")
            return

        student_id = self.student_lookup[student_display]
        book_id = self.book_lookup[book_display]

        try:
            issue_id, due_date = issue_book(student_id, self.current_user.user_id, book_id)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        messagebox.showinfo("Success", f"Book issued. Due date: {due_date}")

        # book availability changed, and the dropdown text includes the
        # available count -- reload it so it's accurate, and clear
        # the selections so the librarian doesn't accidentally issue
        # the same book twice in a row
        self.student_combo.set("")
        self.book_combo.set("")
        self.load_dropdown_data()
        self.refresh_table()

    def handle_return(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select an issued book first.")
            return

        values = self.tree.item(selected[0])["values"]
        issue_id = values[0]
        student_name = values[1]
        book_title = values[2]

        confirm = messagebox.askyesno(
            "Confirm Return", f"Return '{book_title}' from {student_name}?"
        )
        if not confirm:
            return

        try:
            late_days, fine_amount, fulfilled_student_id = return_book(issue_id)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        message_lines = []
        if late_days > 0:
            message_lines.append(f"Returned {late_days} day(s) late. Fine: Rs. {fine_amount}")
        else:
            message_lines.append("Returned on time. No fine.")

        if fulfilled_student_id is not None:
            message_lines.append(
                "\nA student had this book reserved -- their reservation is now marked "
                "as fulfilled. Issue it to them when they come in."
            )

        messagebox.showinfo("Book Returned", "\n".join(message_lines))

        # the book that was just returned should now show up as
        # available again, and might have more copies available -- so
        # reload the dropdown data too, not just the issued-books table
        self.load_dropdown_data()
        self.refresh_table()