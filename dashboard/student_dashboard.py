"""
Student dashboard. Skeleton for now - real features (search books,
reserve, view issued books/fines) come in later phases.
"""

import tkinter as tk
from tkinter import ttk

from modules.fine.fine_service import get_fines_for_student


class StudentDashboard:
    def __init__(self, root, current_user):
        self.root = root
        self.current_user = current_user

        self.root.title("Student Dashboard")
        self.root.geometry("500x400")

        self.build_widgets()

    def build_widgets(self):
        welcome_label = tk.Label(
            self.root,
            text=f"Welcome, {self.current_user.name} (Student)",
            font=("Arial", 16, "bold"),
        )
        welcome_label.pack(pady=30)

        # reservation is the first real student feature. more buttons
        # (search books, view issued books, view fines) will go here
        # in later phases
        reserve_button = tk.Button(
            self.root, text="Reserve a Book", command=self.open_reserve_book, width=20
        )
        reserve_button.pack(pady=5)

        my_fines_button = tk.Button(
            self.root, text="My Fines", command=self.open_my_fines, width=20
        )
        my_fines_button.pack(pady=5)

        change_password_button = tk.Button(
            self.root, text="Change Password", command=self.open_change_password, width=20
        )
        change_password_button.pack(pady=5)

        logout_button = tk.Button(
            self.root, text="Logout", command=self.handle_logout, width=15
        )
        logout_button.pack(pady=10)

    def open_reserve_book(self):
        from modules.reservation.reservation_ui import ReserveBookWindow
        ReserveBookWindow(self.root, self.current_user)

    def open_my_fines(self):
        MyFinesWindow(self.root, self.current_user)

    def open_change_password(self):
        from dashboard.change_password_dialog import ChangePasswordDialog
        ChangePasswordDialog(self.root, self.current_user)

    def handle_logout(self):
        self.root.destroy()

        from dashboard.login_screen import LoginScreen
        new_root = tk.Tk()
        LoginScreen(new_root)
        new_root.mainloop()


class MyFinesWindow:
    """
    Read-only -- students can see what they owe (and their fine
    history) but can't mark anything as paid themselves. That's
    intentionally the librarian's job (ManageFinesWindow, in
    librarian_dashboard.py), since paying happens in person.
    """

    def __init__(self, parent, current_user):
        self.window = tk.Toplevel(parent)
        self.window.title("My Fines")
        self.window.geometry("600x450")
        self.window.minsize(550, 400)

        self.current_user = current_user

        self.build_table()
        self.refresh_table()

    def build_table(self):
        columns = ("fine_id", "book", "late_days", "amount", "status")

        self.tree = ttk.Treeview(self.window, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=110)

        self.tree.pack(pady=10, fill="both", expand=True)

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        fines = get_fines_for_student(self.current_user.user_id)
        for fine in fines:
            status = "Paid" if fine["paid"] else "Unpaid"
            self.tree.insert("", "end", values=(
                fine["fine_id"], fine["book_title"], fine["late_days"],
                f"Rs. {fine['fine_amount']}", status,
            ))