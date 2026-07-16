"""
modules/librarians/librarian_ui.py

Window the admin sees for managing librarians. Same pattern as
student_ui.py: smart single action button (Register/Update), password
field disabled during edit, separate explicit Reset Password action.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from modules.librarians.librarian_service import (
    register_librarian,
    get_all_librarians,
    search_librarians,
    update_librarian,
    delete_librarian,
    reset_librarian_password,
    DuplicateEmailError,
)


class LibrarianManagementWindow:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Manage Librarians")
        self.window.geometry("700x700")
        self.window.minsize(650, 600)

        self.editing_user_id = None

        self.build_form()
        self.build_search_bar()
        self.build_table()

        self.refresh_table()

    def build_form(self):
        form_frame = tk.Frame(self.window)
        form_frame.pack(pady=10)

        labels = ["Name", "Email", "Phone", "Password"]
        self.entries = {}

        for i, label_text in enumerate(labels):
            label = tk.Label(form_frame, text=label_text + ":")
            label.grid(row=i, column=0, sticky="e", padx=5, pady=3)

            show_char = "*" if label_text == "Password" else None
            entry = tk.Entry(form_frame, width=35, show=show_char)
            entry.grid(row=i, column=1, padx=5, pady=3)

            self.entries[label_text] = entry

        self.action_button = tk.Button(
            form_frame, text="Register Librarian", command=self.handle_register
        )
        self.action_button.grid(row=len(labels), column=0, columnspan=2, pady=10)

    def build_search_bar(self):
        search_frame = tk.Frame(self.window)
        search_frame.pack(pady=5)

        tk.Label(search_frame, text="Search:").pack(side="left", padx=5)

        self.search_entry = tk.Entry(search_frame, width=30)
        self.search_entry.pack(side="left", padx=5)

        search_button = tk.Button(search_frame, text="Search", command=self.handle_search)
        search_button.pack(side="left", padx=5)

        clear_button = tk.Button(search_frame, text="Clear", command=self.handle_clear_search)
        clear_button.pack(side="left", padx=5)

    def build_table(self):
        columns = ("user_id", "name", "email", "phone")

        bottom_button_frame = tk.Frame(self.window)
        bottom_button_frame.pack(side="bottom", pady=5)

        edit_button = tk.Button(
            bottom_button_frame, text="Edit Selected", command=self.handle_load_for_edit
        )
        edit_button.pack(side="left", padx=5)

        reset_password_button = tk.Button(
            bottom_button_frame, text="Reset Password", command=self.handle_reset_password
        )
        reset_password_button.pack(side="left", padx=5)

        delete_button = tk.Button(
            bottom_button_frame, text="Delete Selected", command=self.handle_delete
        )
        delete_button.pack(side="left", padx=5)

        self.tree = ttk.Treeview(self.window, columns=columns, show="headings", height=8)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=130)

        self.tree.pack(pady=10, fill="both", expand=True)

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        librarians = get_all_librarians()
        self._fill_table(librarians)

    def handle_search(self):
        keyword = self.search_entry.get().strip()
        if not keyword:
            self.refresh_table()
            return

        for row in self.tree.get_children():
            self.tree.delete(row)

        librarians = search_librarians(keyword)
        self._fill_table(librarians)

    def handle_clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.refresh_table()

    def _fill_table(self, librarians):
        for librarian in librarians:
            self.tree.insert("", "end", values=(
                librarian["user_id"],
                librarian["name"],
                librarian["email"],
                librarian["phone"],
            ))

    def _validate_phone(self, phone):
        # shared by register and update -- same rule as student_ui.py:
        # optional, but if given must be exactly 10 digits
        if phone and not phone.isdigit():
            messagebox.showerror("Error", "Phone number must contain only digits.")
            return False
        if phone and len(phone) != 10:
            messagebox.showerror("Error", "Phone number must be exactly 10 digits.")
            return False
        return True

    def handle_register(self):
        name = self.entries["Name"].get().strip()
        email = self.entries["Email"].get().strip()
        phone = self.entries["Phone"].get().strip()
        password = self.entries["Password"].get()

        if not name or not email or not password:
            messagebox.showerror("Error", "Name, Email, and Password are required.")
            return

        if not self._validate_phone(phone):
            return

        try:
            register_librarian(name, email, phone, password)
        except DuplicateEmailError as e:
            messagebox.showerror("Error", str(e))
            return
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        messagebox.showinfo("Success", f"Librarian '{name}' registered successfully.")
        self.clear_form()
        self.refresh_table()

    def clear_form(self):
        for entry in self.entries.values():
            entry.config(state="normal")
            entry.delete(0, tk.END)
        self.editing_user_id = None
        self.action_button.config(text="Register Librarian", command=self.handle_register)

    def handle_load_for_edit(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a librarian first.")
            return

        values = self.tree.item(selected[0])["values"]
        user_id, name, email, phone = values

        self.editing_user_id = user_id

        self.entries["Name"].delete(0, tk.END)
        self.entries["Name"].insert(0, name)

        self.entries["Email"].delete(0, tk.END)
        self.entries["Email"].insert(0, email)

        self.entries["Phone"].delete(0, tk.END)
        self.entries["Phone"].insert(0, phone)

        self.entries["Password"].config(state="normal")
        self.entries["Password"].delete(0, tk.END)
        self.entries["Password"].insert(0, "(not editable here)")
        self.entries["Password"].config(state="disabled")

        self.action_button.config(text="Update Librarian", command=self.handle_update)

    def handle_update(self):
        if self.editing_user_id is None:
            messagebox.showerror(
                "Error", "Click 'Edit Selected' on a librarian first, then Update."
            )
            return

        name = self.entries["Name"].get().strip()
        email = self.entries["Email"].get().strip()
        phone = self.entries["Phone"].get().strip()

        if not name or not email:
            messagebox.showerror("Error", "Name and Email are required.")
            return

        if not self._validate_phone(phone):
            return

        try:
            update_librarian(self.editing_user_id, name, email, phone)
        except DuplicateEmailError as e:
            messagebox.showerror("Error", str(e))
            return
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        messagebox.showinfo("Success", f"'{name}' updated successfully.")
        self.clear_form()
        self.refresh_table()

    def handle_delete(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a librarian first.")
            return

        user_id = self.tree.item(selected[0])["values"][0]
        name = self.tree.item(selected[0])["values"][1]

        confirm = messagebox.askyesno(
            "Confirm Delete", f"Delete librarian '{name}'? This can't be undone."
        )
        if not confirm:
            return

        try:
            delete_librarian(user_id)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        messagebox.showinfo("Deleted", f"'{name}' was deleted.")
        self.refresh_table()

    def handle_reset_password(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a librarian first.")
            return

        user_id = self.tree.item(selected[0])["values"][0]
        name = self.tree.item(selected[0])["values"][1]

        confirm = messagebox.askyesno("Confirm Reset", f"Reset password for '{name}'?")
        if not confirm:
            return

        new_password = simpledialog.askstring(
            "Reset Password", f"Enter new password for '{name}':", show="*"
        )

        if new_password is None:
            return

        try:
            reset_librarian_password(user_id, new_password)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        messagebox.showinfo("Success", f"Password reset for '{name}'.")