"""
Login screen for the app.
Takes email + password, checks with auth_service, shows dashboard or error.
"""

import tkinter as tk

from auth.auth_service import login, AuthenticationError


class LoginScreen:
    # made this a class so I can access the entry widgets from any method
    # using self, instead of using global variables everywhere

    def __init__(self, root):
        self.root = root
        self.root.title("Smart Digital Library - Login")
        self.root.geometry("400x300")

        self.build_widgets()

    def build_widgets(self):
        # heading
        title_label = tk.Label(
            self.root, text="Smart Digital Library", font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)

        # email field
        email_label = tk.Label(self.root, text="Email:")
        email_label.pack()
        self.email_entry = tk.Entry(self.root, width=30)
        self.email_entry.pack(pady=5)

        # password field, show="*" hides what you type
        password_label = tk.Label(self.root, text="Password:")
        password_label.pack()
        self.password_entry = tk.Entry(self.root, width=30, show="*")
        self.password_entry.pack(pady=5)

        # login button, calls handle_login() when clicked
        login_button = tk.Button(
            self.root, text="Login", command=self.handle_login, width=15
        )
        login_button.pack(pady=15)

        # this stays empty until there's an error/success message to show
        self.error_label = tk.Label(self.root, text="", fg="red")
        self.error_label.pack()

    def handle_login(self):
        # get whatever the user typed
        email = self.email_entry.get()
        password = self.password_entry.get()

        try:
            current_user = login(email, password)
        except AuthenticationError as e:
            # wrong email/password, just show it on screen, don't crash
            self.error_label.config(text=str(e))
            return

        # login worked, close this window and open the right dashboard
        # based on role. importing here (not at top of file) to avoid
        # circular imports, since the dashboards import LoginScreen back
        # for their logout button
        self.root.destroy()

        new_root = tk.Tk()

        if current_user.role == "admin":
            from dashboard.admin_dashboard import AdminDashboard
            AdminDashboard(new_root, current_user)
        elif current_user.role == "librarian":
            from dashboard.librarian_dashboard import LibrarianDashboard
            LibrarianDashboard(new_root, current_user)
        elif current_user.role == "student":
            from dashboard.student_dashboard import StudentDashboard
            StudentDashboard(new_root, current_user)
        else:
            # shouldn't happen since DB only allows these 3 roles,
            # but just in case
            tk.Label(new_root, text=f"Unknown role: {current_user.role}").pack()

        new_root.mainloop()