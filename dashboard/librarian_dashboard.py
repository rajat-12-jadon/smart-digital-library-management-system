"""
Librarian dashboard. Skeleton for now - real features (register
students, issue/return books etc) come in later phases.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from modules.fine.fine_service import get_pending_fines, mark_fine_paid


class LibrarianDashboard:
    def __init__(self, root, current_user):
        self.root = root
        self.current_user = current_user

        self.root.title("Librarian Dashboard")
        self.root.geometry("500x400")

        self.build_widgets()

    def build_widgets(self):
        welcome_label = tk.Label(
            self.root,
            text=f"Welcome, {self.current_user.name} (Librarian)",
            font=("Arial", 16, "bold"),
        )
        welcome_label.pack(pady=30)

        # student management is the first real librarian feature.
        # more buttons (issue/return, reservations, fines) will go
        # here in later phases
        manage_students_button = tk.Button(
            self.root, text="Manage Students", command=self.open_student_management, width=20
        )
        manage_students_button.pack(pady=5)

        issue_book_button = tk.Button(
            self.root, text="Issue Book", command=self.open_issue_book, width=20
        )
        issue_book_button.pack(pady=5)

        pending_pickups_button = tk.Button(
            self.root, text="Pending Pickups", command=self.open_pending_pickups, width=20
        )
        pending_pickups_button.pack(pady=5)

        manage_fines_button = tk.Button(
            self.root, text="Manage Fines", command=self.open_manage_fines, width=20
        )
        manage_fines_button.pack(pady=5)

        change_password_button = tk.Button(
            self.root, text="Change Password", command=self.open_change_password, width=20
        )
        change_password_button.pack(pady=5)

        logout_button = tk.Button(
            self.root, text="Logout", command=self.handle_logout, width=15
        )
        logout_button.pack(pady=10)

    def open_student_management(self):
        from modules.students.student_ui import StudentManagementWindow
        StudentManagementWindow(self.root)

    def open_issue_book(self):
        from modules.issue_return.issue_ui import IssueBookWindow
        IssueBookWindow(self.root, self.current_user)

    def open_pending_pickups(self):
        from modules.reservation.reservation_ui import PendingPickupsWindow
        PendingPickupsWindow(self.root, self.current_user)

    def open_manage_fines(self):
        ManageFinesWindow(self.root)

    def open_change_password(self):
        from dashboard.change_password_dialog import ChangePasswordDialog
        ChangePasswordDialog(self.root, self.current_user)

    def handle_logout(self):
        self.root.destroy()

        from dashboard.login_screen import LoginScreen
        new_root = tk.Tk()
        LoginScreen(new_root)
        new_root.mainloop()


class ManageFinesWindow:
    """
    Kept inline in this file rather than a separate fine_ui.py --
    small and simple enough (one table, one button) that a whole
    extra module felt like overkill. fine_service.py still holds all
    the actual DB logic, this class is UI only.
    """

    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Manage Fines")
        self.window.geometry("650x500")
        self.window.minsize(600, 450)

        self.build_table()
        self.refresh_table()

    def build_table(self):
        columns = ("fine_id", "student", "book", "late_days", "amount")

        # button packed first (bottom) so it never gets pushed
        # off-screen when resized -- same fix as other modules
        mark_paid_button = tk.Button(
            self.window, text="Mark Selected as Paid", command=self.handle_mark_paid
        )
        mark_paid_button.pack(side="bottom", pady=5)

        self.tree = ttk.Treeview(self.window, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=120)

        self.tree.pack(pady=10, fill="both", expand=True)

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        fines = get_pending_fines()
        for fine in fines:
            self.tree.insert("", "end", values=(
                fine["fine_id"], fine["student_name"], fine["book_title"],
                fine["late_days"], f"Rs. {fine['fine_amount']}",
            ))

    def handle_mark_paid(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a fine first.")
            return

        values = self.tree.item(selected[0])["values"]
        fine_id = values[0]
        student_name = values[1]
        amount = values[4]

        confirm = messagebox.askyesno(
            "Confirm Payment", f"Mark {amount} fine for {student_name} as paid?"
        )
        if not confirm:
            return

        try:
            mark_fine_paid(fine_id)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        messagebox.showinfo("Success", "Fine marked as paid.")
        self.refresh_table()