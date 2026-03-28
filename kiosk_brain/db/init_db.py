import sqlite3
import os
from pathlib import Path
import logging


def initialize_database(db_path="kiosk.db"):
    """Initialize the SQLite Database with schema"""
    current_dir = Path(__file__).parent
    schema_path = current_dir / "schema.sql"

    with open(schema_path, "r") as f:
        schema_sql = f.read()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(schema_sql)
    conn.commit()
    conn.close()

    logging.info(f"Database initialized successfully at {db_path}")


if __name__ == "__main__":
    try:
        initialize_database()
        print("✓ Database initialized successfully!")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
