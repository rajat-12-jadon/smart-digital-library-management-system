"""
Student dashboard. Skeleton for now - real features (search books,
reserve, view issued books/fines) come in later phases.
"""

import tkinter as tk


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

    def open_change_password(self):
        from dashboard.change_password_dialog import ChangePasswordDialog
        ChangePasswordDialog(self.root, self.current_user)

    def handle_logout(self):
        self.root.destroy()

        from dashboard.login_screen import LoginScreen
        new_root = tk.Tk()
        LoginScreen(new_root)
        new_root.mainloop()