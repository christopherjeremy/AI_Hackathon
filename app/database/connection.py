import sqlite3
from typing import Generator
from app.config import settings

def get_db_connection() -> sqlite3.Connection:
    """
    Returns a read-only SQLite database connection.
    Uses 'mode=ro' to ensure data integrity is never compromised.
    """
    db_path = settings.DATABASE_PATH
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found at {db_path}")

    # Open connection in strict read-only mode using URI
    uri_path = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri_path, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
