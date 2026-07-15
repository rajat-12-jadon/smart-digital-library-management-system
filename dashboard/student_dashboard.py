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

        # actual student features (search books, reserve, view
        # issued books, view fines) will go here in later phases

        logout_button = tk.Button(
            self.root, text="Logout", command=self.handle_logout, width=15
        )
        logout_button.pack(pady=10)

    def handle_logout(self):
        self.root.destroy()

        from dashboard.login_screen import LoginScreen
        new_root = tk.Tk()
        LoginScreen(new_root)
        new_root.mainloop()