"""Intentionally vulnerable mini app for demos.

Do NOT deploy this code.
"""

from __future__ import annotations

import pickle
import sqlite3
import subprocess
from typing import Any

import requests

DB_PATH = "mini_app.db"


def get_user(user_id: str) -> dict[str, Any]:
    """Return a user record.

    Demo issue: SQL injection via string formatting.
    """
    query = f"SELECT id, email FROM users WHERE id = {user_id}"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query)
    row = cursor.fetchone()
    return {"id": row[0], "email": row[1]} if row else {}


def run_report(command: str) -> str:
    """Run a report command.

    Demo issue: command injection with shell=True.
    """
    return subprocess.check_output(command, shell=True, text=True)


def fetch_profile(url: str) -> str:
    """Fetch a remote profile document.

    Demo issue: SSRF risk with user-supplied URL.
    """
    response = requests.get(url, timeout=3)
    return response.text


def load_session(raw: bytes) -> dict[str, Any]:
    """Load a session payload.

    Demo issue: insecure deserialization via pickle.
    """
    return pickle.loads(raw)
