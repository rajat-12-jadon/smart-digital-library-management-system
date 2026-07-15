"""
Entry point of the app. Run this file to start everything.
python main.py
"""

import tkinter as tk

from database import init_pool, close_pool
from dashboard.login_screen import LoginScreen


def main():
    # connect to db before opening any window
    init_pool()

    root = tk.Tk()
    LoginScreen(root)

    # so if I close the window with the X button, it still closes
    # the db connections properly instead of just leaving them open
    root.protocol("WM_DELETE_WINDOW", lambda: on_close(root))

    root.mainloop()


def on_close(root):
    close_pool()
    root.destroy()


if __name__ == "__main__":
    main()