"""
Librarian dashboard. Skeleton for now - real features (register
students, issue/return books etc) come in later phases.
"""

import tkinter as tk


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

    def handle_logout(self):
        self.root.destroy()

        from dashboard.login_screen import LoginScreen
        new_root = tk.Tk()
        LoginScreen(new_root)
        new_root.mainloop()