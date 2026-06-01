"""
Database Initialization Module — SQLite Schema Setup

This module provides utilities to initialize the SQLite database with the complete schema
for the Smart ID Card Distribution Kiosk system.

SCHEMA OVERVIEW:
================
The initialize_database() function creates 5 tables with relationships:

1. students
   - Columns: student_id (PK), registration_number (UNIQUE), name, email, phone, year
   - Purpose: Store student information from UDSM mock API
   - Foreign Keys: None

2. authentication
   - Columns: auth_id (PK), student_id (FK), otp_hash, pin_hash, is_temp_pin, failed_attempts, lockout_until
   - Purpose: Store OTP and PIN credentials for each student
   - Key Pattern: is_temp_pin distinguishes temporary (system-generated) vs permanent (user-set) PINs
   - Relationships: Links to students via student_id

3. cards
   - Columns: card_id (PK), student_id (FK), batch_id (FK), status, printed_date, collected_date
   - Purpose: Track physical ID card details and collection status
   - Status Values: pending, printed, collected, dispensed, lost
   - Relationships: Links to students (student_id) and batches (batch_id)

4. audit_log
   - Columns: log_id (PK), student_id (FK), action, timestamp, details, ip_address
   - Purpose: Immutable transaction log for compliance and debugging
   - Actions: otp_sent, otp_verified, pin_verified, card_dispensed, authentication_failed, etc.
   - Relationships: Links to students via student_id

5. batches
   - Columns: batch_id (PK), batch_name, loaded_date, total_cards, status
   - Purpose: Group cards into batches for bulk loading and tracking
   - Status Values: pending, in_progress, completed, partially_failed
   - Relationships: Referenced by cards table

DATABASE FILE:
==============
Location: kiosk_brain/db/kiosk.db (SQLite3 database)
Initialization: Automatic on app startup if file doesn't exist
Schema File: db/schema.sql (contains all CREATE TABLE statements)
Permissions: Read/write for kiosk app process, readable for admin users

USAGE:
======
# Standalone initialization script
python3 db/init_db.py

# Import and use in app
from db.init_db import initialize_database
initialize_database(db_path="~/data/kiosk.db")

ERROR HANDLING:
===============
- FileNotFoundError: schema.sql not found in same directory
- sqlite3.DatabaseError: Invalid SQL syntax in schema.sql
- IOError: Permission denied writing to db_path
- All errors logged to file via logging module
"""

import sqlite3
import os
import sys
from pathlib import Path
import logging


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def initialize_database(db_path=None):
    """
    Initialize SQLite database with complete schema.

    This function reads schema.sql from the same directory and executes all CREATE TABLE
    statements to set up the 5-table relational database for the kiosk system.

    Args:
        db_path (str): Path to SQLite database file to create/initialize.
                      Default: "kiosk.db" (current working directory)
                      Can be absolute or relative path.

    Raises:
        FileNotFoundError: If schema.sql not found in db/ directory
        sqlite3.DatabaseError: If SQL syntax errors in schema.sql
        IOError: If permission denied writing to db_path
        Exception: Any other errors during execution (logged)

    Side Effects:
        1. Creates kiosk.db file at specified db_path if it doesn't exist
        2. Executes all CREATE TABLE statements from schema.sql
        3. Commits transaction to persist schema
        4. Logs success message with database path

    Return:
        None (success indicated by logging and no exceptions)

    Example:
        >>> from db.init_db import initialize_database
        >>> initialize_database()  # Create db/kiosk.db in the db directory
        >>> initialize_database("/data/production.db")  # Use absolute path

    Note:
        - Safe to run multiple times (idempotent): IF NOT EXISTS in schema.sql
        - Should run once on app startup before connecting application
    """
    current_dir = Path(__file__).parent
    schema_path = current_dir / "schema.sql"
    if db_path is None:
        db_path = str(current_dir / "kiosk.db")
    else:
        db_path = str(Path(db_path).expanduser())

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with open(schema_path, "r") as f:
        schema_sql = f.read()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(schema_sql)
    conn.commit()
    conn.close()

    logging.info(f"Database initialized successfully at {db_path}")


if __name__ == "__main__":
    import sys
    from modules.database import clear_database
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--reset":
            # Clear all data, keep schema
            print("🔄 Clearing database...")
            result = clear_database()
            if result.get("success"):
                print(f"✓ Database cleared successfully!")
                print(f"  Deleted: {result['deleted_records']}")
                # Re-initialize schema
                print("📝 Re-initializing schema...")
                initialize_database()
                print("✓ Schema re-initialized!")
            else:
                print(f"✗ Clear failed: {result['error']}")
        else:
            # Normal initialization
            initialize_database()
            print("✓ Database initialized successfully!")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
