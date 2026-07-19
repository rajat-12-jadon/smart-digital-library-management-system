# Smart Digital Library Management System

A desktop-based Library Management System built with **Python**, **Tkinter**, and **PostgreSQL**, simulating a real-world digital library with role-based access for Admins, Librarians, and Students.

---

## Overview

This project follows a layered architecture (Presentation → Authentication → Business Logic → Data Access → Database) and covers the full lifecycle of a library system: user management, book cataloging, issuing/returning books, reservations, fines, QR-code-based scanning, email notifications, and reporting.

---

## Features

### Admin
- Manage librarians (register, update, delete, reset password)
- Manage books (add, search, delete, view QR code)
- View reports (most/least issued books, top readers, pending fines, monthly issue/return counts)
- Change own password

### Librarian
- Register and manage students (with search, edit, and password reset)
- Issue and return books, including QR-code scanning to select a book/return instantly
- View and fulfill reservation pickups
- Collect and mark fines as paid
- Send email reminders (due tomorrow, overdue, reservation ready) to students
- Change own password

### Student
- Reserve books that are currently unavailable
- View own reservation status
- View own fine history (read-only)
- Change own password

### Security
- Passwords hashed with bcrypt (never stored in plaintext)
- SQL-injection-safe parameterized queries throughout
- Forced password change on first login for any account created by someone else
- Password reuse prevention (new password must differ from the current one)
- "Forgot Password" flow with a randomly generated temporary password, emailed to the account holder
- Activity logging for sensitive actions (logins, password resets/changes)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| GUI | Tkinter |
| Database | PostgreSQL (via psycopg2) |
| Password Hashing | bcrypt |
| QR Codes | qrcode, Pillow, OpenCV, pyzbar |
| Email | smtplib (Gmail SMTP) |
| Testing | pytest |
| Version Control | Git & GitHub |

---

## Architecture

```
Presentation (Tkinter UI)
        ↓
Authentication Layer
        ↓
Business Logic Layer (*_service.py files)
        ↓
Data Access Layer (database.py)
        ↓
PostgreSQL Database
```

Each feature module (books, students, librarians, issue/return, reservation, fine, reports, notifications) is split into a `*_service.py` file (business logic and database queries) and a `*_ui.py` file (Tkinter interface) — the UI never talks to the database directly.

---

## Project Structure

```
Library Management System/
├── main.py                    # Entry point
├── config.py                  # Environment-based configuration
├── database.py                # Pooled PostgreSQL connection layer
├── requirements.txt
│
├── auth/                      # Login, password hashing, forgot password
├── dashboard/                 # Role-based dashboards and shared screens
│
├── modules/
│   ├── books/
│   ├── students/
│   ├── librarians/
│   ├── issue_return/
│   ├── reservation/
│   ├── fine/
│   ├── reports/
│   └── notifications/
│
├── utils/                     # QR code and email utilities
├── database/
│   ├── schema.sql             # Full database schema
│   └── migrations/            # Schema changes made after initial deployment
│
├── tests/                     # pytest test suite (separate test database)
└── docs/                      # Additional documentation
```

---

## Database Schema

Six core tables: `Users`, `Books`, `Book_Issue`, `Reservation`, `Fine`, `Activity_Log` — linked by foreign keys, with PostgreSQL ENUM types and CHECK constraints enforcing valid roles, statuses, and business rules (e.g. available copies can never exceed total copies).

See [`database/schema.sql`](database/schema.sql) for the full DDL.

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- A Gmail account with an [App Password](https://myaccount.google.com/apppasswords) generated (for email features)

### 1. Clone the repository
```bash
git clone https://github.com/rajat-12-jadon/smart-digital-library-management-system.git
cd smart-digital-library-management-system
```

### 2. Create a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

> **macOS (Apple Silicon) note:** `pyzbar` requires the system `zbar` library, which isn't installed by pip.
> ```bash
> brew install zbar
> export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH
> ```
> Add the `export` line to your `~/.zshrc` to make it permanent.

### 4. Set up the database
```bash
createdb library_management_system
psql -d library_management_system -f database/schema.sql
```

### 5. Set environment variables
Add to your `~/.zshrc` (or `.bashrc`):
```bash
export LMS_DB_HOST=localhost
export LMS_DB_PORT=5432
export LMS_DB_NAME=library_management_system
export LMS_DB_USER=postgres
export LMS_DB_PASSWORD='your_postgres_password'
export LMS_EMAIL_ADDRESS='your_gmail_address'
export LMS_EMAIL_APP_PASSWORD='your_gmail_app_password'
```
Then run `source ~/.zshrc`.

### 6. Create an initial admin account
```bash
python seed_admin.py
```

### 7. Run the app
```bash
python main.py
```

---

## Running Tests

Tests run against a **separate test database** so they never touch real data.

```bash
createdb library_management_system_test
psql -d library_management_system_test -f database/schema.sql

python -m pytest tests/ -v
```

---

## Possible Future Improvements

- Migrate credential storage from shell environment variables to a `.env` file with `python-dotenv`
- Package as a standalone executable (PyInstaller) with a bundled/containerized database (Docker)
- Automated (scheduled) email reminders instead of a manually-triggered button
- Web-based version with a modern UI (React/Vue + REST API)

---

## License

This project was built as an academic mini-project.