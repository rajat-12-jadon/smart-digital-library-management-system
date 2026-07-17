"""
Admin dashboard. Just a skeleton for now - real features (manage
librarians, view reports etc) come in later phases.
"""

import tkinter as tk


class AdminDashboard:
    def __init__(self, root, current_user):
        self.root = root
        self.current_user = current_user

        self.root.title("Admin Dashboard")
        self.root.geometry("500x400")

        self.build_widgets()

    def build_widgets(self):
        welcome_label = tk.Label(
            self.root,
            text=f"Welcome, {self.current_user.name} (Admin)",
            font=("Arial", 16, "bold"),
        )
        welcome_label.pack(pady=30)

        # book management is the first real admin feature. more
        # buttons (manage librarians, reports, etc) will go here
        # in later phases
        manage_books_button = tk.Button(
            self.root, text="Manage Books", command=self.open_book_management, width=20
        )
        manage_books_button.pack(pady=5)

        manage_librarians_button = tk.Button(
            self.root, text="Manage Librarians", command=self.open_librarian_management, width=20
        )
        manage_librarians_button.pack(pady=5)

        change_password_button = tk.Button(
            self.root, text="Change Password", command=self.open_change_password, width=20
        )
        change_password_button.pack(pady=5)

        logout_button = tk.Button(
            self.root, text="Logout", command=self.handle_logout, width=15
        )
        logout_button.pack(pady=10)

    def open_book_management(self):
        from modules.books.book_ui import BookManagementWindow
        BookManagementWindow(self.root)

    def open_librarian_management(self):
        from modules.librarians.librarian_ui import LibrarianManagementWindow
        LibrarianManagementWindow(self.root)

    def open_change_password(self):
        from dashboard.change_password_dialog import ChangePasswordDialog
        ChangePasswordDialog(self.root, self.current_user)

    def handle_logout(self):
        # close this window and go back to login
        self.root.destroy()

        from dashboard.login_screen import LoginScreen
        new_root = tk.Tk()
        LoginScreen(new_root)
        new_root.mainloop()