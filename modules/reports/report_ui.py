"""
modules/reports/report_ui.py

One window, one dropdown to pick which of the 6 reports to view, one
table that rebuilds its own columns depending on which report was
picked (since "Most Issued Books" and "Monthly Issue Count" don't
have the same columns at all). Simpler than building 6 separate
windows for 6 reports that are all "pick something, see a table".
"""

import tkinter as tk
from tkinter import ttk, messagebox

from modules.reports.report_service import (
    get_most_issued_books,
    get_least_issued_books,
    get_top_readers,
    get_pending_fine_summary,
    get_monthly_issue_count,
    get_monthly_return_count,
)

# maps the dropdown's display text to (service function, column keys,
# column headers) -- adding a 7th report later means adding one entry
# here, not writing a new window
REPORT_DEFINITIONS = {
    "Most Issued Books": (
        get_most_issued_books, ["title", "author", "issue_count"],
        ["Title", "Author", "Times Issued"],
    ),
    "Least Issued Books": (
        get_least_issued_books, ["title", "author", "issue_count"],
        ["Title", "Author", "Times Issued"],
    ),
    "Top Readers": (
        get_top_readers, ["name", "email", "books_issued"],
        ["Name", "Email", "Books Issued"],
    ),
    "Monthly Issue Count": (
        get_monthly_issue_count, ["month", "issue_count"],
        ["Month", "Books Issued"],
    ),
    "Monthly Return Count": (
        get_monthly_return_count, ["month", "return_count"],
        ["Month", "Books Returned"],
    ),
}


class ReportsWindow:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Reports")
        self.window.geometry("650x550")
        self.window.minsize(600, 500)

        self.tree = None  # created fresh each time a report is generated

        self.build_form()

    def build_form(self):
        form_frame = tk.Frame(self.window)
        form_frame.pack(pady=15)

        tk.Label(form_frame, text="Report:").pack(side="left", padx=5)

        # "Pending Fine Summary" handled separately (see
        # handle_generate) since it returns one summary, not a list
        report_names = list(REPORT_DEFINITIONS.keys()) + ["Pending Fine Summary"]
        self.report_combo = ttk.Combobox(
            form_frame, width=30, state="readonly", values=report_names
        )
        self.report_combo.pack(side="left", padx=5)

        generate_button = tk.Button(form_frame, text="Generate", command=self.handle_generate)
        generate_button.pack(side="left", padx=5)

        # everything below the table area
        self.table_frame = tk.Frame(self.window)
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def handle_generate(self):
        report_name = self.report_combo.get()
        if not report_name:
            messagebox.showerror("Error", "Select a report first.")
            return

        # clear out whatever table was shown before (from a
        # previously generated report)
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        if report_name == "Pending Fine Summary":
            self._show_pending_fine_summary()
            return

        service_function, column_keys, column_headers = REPORT_DEFINITIONS[report_name]
        rows = service_function()

        self.tree = ttk.Treeview(
            self.table_frame, columns=column_keys, show="headings", height=15
        )
        for key, header in zip(column_keys, column_headers):
            self.tree.heading(key, text=header)
            self.tree.column(key, width=150)

        self.tree.pack(fill="both", expand=True)

        if not rows:
            messagebox.showinfo("No Data", "This report has no data to show yet.")
            return

        for row in rows:
            values = [row[key] for key in column_keys]
            self.tree.insert("", "end", values=values)

    def _show_pending_fine_summary(self):
        # not a list of rows -- just two numbers, so a small
        # label-based layout reads better than a one-row table
        summary = get_pending_fine_summary()

        tk.Label(
            self.table_frame,
            text=f"Pending Fines: {summary['pending_count']}",
            font=("Arial", 13),
        ).pack(pady=10)

        tk.Label(
            self.table_frame,
            text=f"Total Amount Owed: Rs. {summary['pending_total']}",
            font=("Arial", 13, "bold"),
        ).pack(pady=10)