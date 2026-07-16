"""
dashboard/change_password_screen.py

Shown right after login, ONLY when current_user.force_password_change
is True -- i.e. someone else (an admin/librarian) set this account's
current password, and the real owner has never chosen their own.
"""

import tkinter as tk
from tkinter import messagebox

from auth.auth_service import change_password


class ChangePasswordScreen:
    def __init__(self, root, current_user, on_success):
        """
        on_success is a callback (no arguments) -- this screen doesn't
        know or care what the "correct next screen" is (that's a
        dashboard, and which one depends on role). Whoever opens this
        screen passes in what to do next, once the password is changed.
        """
        self.root = root
        self.current_user = current_user
        self.on_success = on_success

        self.root.title("Change Your Password")
        self.root.geometry("400x300")

        self.build_widgets()

    def build_widgets(self):
        info_label = tk.Label(
            self.root,
            text="Your password was set by an admin/librarian.\nPlease choose your own password to continue.",
            wraplength=350,
            justify="center",
        )
        info_label.pack(pady=20)

        tk.Label(self.root, text="New Password:").pack()
        self.new_password_entry = tk.Entry(self.root, width=30, show="*")
        self.new_password_entry.pack(pady=5)

        tk.Label(self.root, text="Confirm Password:").pack()
        self.confirm_password_entry = tk.Entry(self.root, width=30, show="*")
        self.confirm_password_entry.pack(pady=5)

        submit_button = tk.Button(
            self.root, text="Set New Password", command=self.handle_submit
        )
        submit_button.pack(pady=15)

        self.error_label = tk.Label(self.root, text="", fg="red")
        self.error_label.pack()

    def handle_submit(self):
        new_password = self.new_password_entry.get()
        confirm_password = self.confirm_password_entry.get()

        if not new_password:
            self.error_label.config(text="Password cannot be empty.")
            return

        if new_password != confirm_password:
            self.error_label.config(text="Passwords do not match.")
            return

        try:
            change_password(self.current_user.user_id, new_password)
        except ValueError as e:
            self.error_label.config(text=str(e))
            return

        messagebox.showinfo("Success", "Password updated. Continuing to your dashboard.")
        self.on_success()