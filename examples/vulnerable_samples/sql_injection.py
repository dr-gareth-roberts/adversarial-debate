"""SQL Injection Vulnerabilities - INTENTIONALLY VULNERABLE.

This file contains intentionally vulnerable code for testing purposes.
DO NOT use any of this code in production.

Vulnerability: CWE-89 - Improper Neutralization of Special Elements used in an SQL Command
OWASP: A03:2021 - Injection
"""

import sqlite3
from typing import Any


# Example 1: String concatenation
def get_user_by_id_concat(user_id: str) -> dict | None:
    """VULNERABLE: String concatenation in SQL query.

    Attack: user_id = "1 OR 1=1"
    Result: Returns all users
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # BAD: Direct string concatenation
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()


# Example 2: f-string interpolation
def get_user_by_name_fstring(username: str) -> dict | None:
    """VULNERABLE: f-string interpolation in SQL query.

    Attack: username = "'; DROP TABLE users; --"
    Result: Table deletion
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # BAD: f-string interpolation
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()


# Example 3: format() method
def search_users_format(search_term: str) -> list:
    """VULNERABLE: format() method in SQL query.

    Attack: search_term = "%' UNION SELECT password FROM users WHERE '1'='1"
    Result: Password extraction
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # BAD: format() method
    query = "SELECT * FROM users WHERE name LIKE '%{}%'".format(search_term)
    cursor.execute(query)
    return cursor.fetchall()


# Example 4: % string formatting
def get_user_by_email_percent(email: str) -> dict | None:
    """VULNERABLE: %-style string formatting in SQL query.

    Attack: email = "test@test.com' OR '1'='1"
    Result: Authentication bypass
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # BAD: %-style formatting
    query = "SELECT * FROM users WHERE email = '%s'" % email
    cursor.execute(query)
    return cursor.fetchone()


# Example 5: LIKE clause injection
def search_products_like(search: str) -> list:
    """VULNERABLE: LIKE clause with user input.

    Attack: search = "%" (returns all)
    Attack: search = "%' OR '1'='1" (always true)
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # BAD: User input in LIKE without escaping
    query = f"SELECT * FROM products WHERE name LIKE '%{search}%'"
    cursor.execute(query)
    return cursor.fetchall()


# Example 6: ORDER BY injection
def get_users_sorted(column: str, direction: str) -> list:
    """VULNERABLE: Dynamic ORDER BY clause.

    Attack: column = "1; DROP TABLE users; --"
    Attack: direction = "ASC; DELETE FROM users; --"
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # BAD: Dynamic ORDER BY from user input
    query = f"SELECT * FROM users ORDER BY {column} {direction}"
    cursor.execute(query)
    return cursor.fetchall()


# Example 7: IN clause injection
def get_users_by_ids(user_ids: list[str]) -> list:
    """VULNERABLE: IN clause built from user input.

    Attack: user_ids = ["1) OR (1=1"]
    Result: Returns all users
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # BAD: Building IN clause from untrusted list
    ids_str = ", ".join(user_ids)
    query = f"SELECT * FROM users WHERE id IN ({ids_str})"
    cursor.execute(query)
    return cursor.fetchall()


# Example 8: Table/column name injection
def get_data_from_table(table_name: str, column_name: str) -> list:
    """VULNERABLE: Dynamic table and column names.

    Attack: table_name = "users; DROP TABLE secrets; --"
    Result: Arbitrary table access/deletion
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # BAD: Dynamic table/column names from user input
    query = f"SELECT {column_name} FROM {table_name}"
    cursor.execute(query)
    return cursor.fetchall()


# SECURE ALTERNATIVES (for comparison)

def get_user_by_id_secure(user_id: int) -> dict | None:
    """SECURE: Parameterized query."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # GOOD: Parameterized query
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()


def search_users_secure(search_term: str) -> list:
    """SECURE: Parameterized LIKE query."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # GOOD: Parameterized query with LIKE
    cursor.execute(
        "SELECT * FROM users WHERE name LIKE ?",
        (f"%{search_term}%",),
    )
    return cursor.fetchall()


ALLOWED_COLUMNS = {"id", "username", "email", "created_at"}
ALLOWED_DIRECTIONS = {"ASC", "DESC"}


def get_users_sorted_secure(column: str, direction: str) -> list:
    """SECURE: Allowlist for dynamic parts."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # GOOD: Validate against allowlist
    if column not in ALLOWED_COLUMNS:
        raise ValueError(f"Invalid column: {column}")
    if direction.upper() not in ALLOWED_DIRECTIONS:
        raise ValueError(f"Invalid direction: {direction}")

    query = f"SELECT * FROM users ORDER BY {column} {direction}"
    cursor.execute(query)
    return cursor.fetchall()
