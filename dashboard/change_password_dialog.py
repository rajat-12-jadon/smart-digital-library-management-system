"""
dashboard/change_password_dialog.py

A small popup any dashboard (Admin/Librarian/Student) can open to let
the logged-in user change their own password whenever they want --
different from change_password_screen.py, which is the FORCED
first-login flow. This one asks for the current password too, as a
safeguard against someone else using an unattended session.
"""

import tkinter as tk
from tkinter import messagebox

from auth.auth_service import change_own_password


class ChangePasswordDialog:
    def __init__(self, parent, current_user):
        self.window = tk.Toplevel(parent)
        self.window.title("Change Password")
        self.window.geometry("380x320")

        self.current_user = current_user

        self.build_widgets()

    def build_widgets(self):
        tk.Label(self.window, text="Current Password:").pack(pady=(20, 0))
        self.current_password_entry = tk.Entry(self.window, width=30, show="*")
        self.current_password_entry.pack(pady=5)

        tk.Label(self.window, text="New Password:").pack(pady=(10, 0))
        self.new_password_entry = tk.Entry(self.window, width=30, show="*")
        self.new_password_entry.pack(pady=5)

        tk.Label(self.window, text="Confirm New Password:").pack(pady=(10, 0))
        self.confirm_password_entry = tk.Entry(self.window, width=30, show="*")
        self.confirm_password_entry.pack(pady=5)

        submit_button = tk.Button(self.window, text="Update Password", command=self.handle_submit)
        submit_button.pack(pady=15)

        self.error_label = tk.Label(self.window, text="", fg="red", wraplength=340)
        self.error_label.pack()

    def handle_submit(self):
        current_password = self.current_password_entry.get()
        new_password = self.new_password_entry.get()
        confirm_password = self.confirm_password_entry.get()

        if new_password != confirm_password:
            self.error_label.config(text="New passwords do not match.")
            return

        try:
            change_own_password(self.current_user.user_id, current_password, new_password)
        except ValueError as e:
            self.error_label.config(text=str(e))
            return

        messagebox.showinfo("Success", "Password updated successfully.")
        self.window.destroy()