"""
test_login.py

Manual check for the login flow -- run after seed_admin.py to confirm
auth_service.login() correctly authenticates, and correctly rejects
bad credentials.
"""

from database import init_pool, close_pool
from auth.auth_service import login, AuthenticationError


def main():
    init_pool()

    # Case 1: correct credentials -- should succeed
    try:
        user = login("admin@test.com", "Admin@123")
        print("Login succeeded:")
        print(f"  user_id: {user.user_id}")
        print(f"  name:    {user.name}")
        print(f"  role:    {user.role}")
    except AuthenticationError as e:
        print("Unexpected failure on correct credentials:", e)

    # Case 2: wrong password -- should fail
    try:
        login("admin@test.com", "wrongpassword")
        print("BUG: wrong password was accepted!")
    except AuthenticationError:
        print("Correctly rejected wrong password.")

    # Case 3: unknown email -- should fail with same generic message
    try:
        login("nobody@nowhere.com", "whatever")
        print("BUG: unknown email was accepted!")
    except AuthenticationError:
        print("Correctly rejected unknown email.")

    close_pool()


if __name__ == "__main__":
    main()