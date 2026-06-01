"""
Database Transaction Wrapper and Card Ingestion Integration

This module provides database operations for SQLite transactions:
- Card ingestion from university API lookups with slot assignment
- Local kiosk_db reads for the UI
- OTP generation and credential delivery (SMS + Email)
- Atomic transactions with rollback on failure
- Database reset utility for fresh test cycles

**WORKFLOW:**
Staff scans card → ingest_card(reg_number) → {
  - Fetch student from University API
  - Generate OTP + check for existing PIN
  - Generate temp PIN if first-year
  - Send SMS + Email with credentials
  - Update authentication table
  - Assign slot and create card record
  - Log audit event
}

Core Functions:
===============
- get_db_connection() - Get SQLite connection with configurable db_path
- get_student_from_db() - Read a student record from kiosk_db for the UI
- get_next_available_slot() - Find first available slot (0-3), return None if full
- check_student_has_pin() - Check if student already has PIN (first-year vs returning)
- ingest_card(reg_number) - Atomic transaction: fetch student, generate OTP, send credentials, assign slot
- clear_database() - Delete all data (for testing), keep schema intact

Atomic Transaction Pattern:
===========================
    try:
        conn = get_db_connection()
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("INSERT INTO students ...")
        cursor.execute("INSERT INTO authentication ...")
        cursor.execute("INSERT INTO cards ...")
        cursor.execute("INSERT INTO audit_log ...")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
"""

import sqlite3
import uuid
from datetime import datetime, timedelta
from config import DB_PATH
from modules.api_client import get_student
from modules.auth import (
    generate_otp,
    generate_temp_pin,
    hash_credential,
)
from modules.sms_client import send_credentials
import logging

# Configure logging for database operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_SLOTS = 4
TOTAL_SLOTS = list(range(MAX_SLOTS))  # [0, 1, 2, 3]
OTP_EXPIRY_HOURS = 24


def get_db_connection(db_path=None):
    """
    Get SQLite database connection.

    Args:
        db_path (str): Path to SQLite database file. Defaults to config.DB_PATH.
                       Use absolute path for production, relative for testing.

    Returns:
        sqlite3.Connection: Database connection object with row factory set

    Raises:
        sqlite3.DatabaseError: If database file is corrupted or inaccessible

    Usage:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students")
        conn.close()
    """
    if db_path is None:
        db_path = DB_PATH
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    except sqlite3.DatabaseError as e:
        logger.error(f"Database connection failed: {e}")
        raise


def get_student_from_db(reg_number, db_path=None):
    """
    Read a student record from kiosk_db for the UI.

    This is the UI-facing path. The kiosk Pi ingestion flow is responsible for
    populating the local database first; the UI only reads the stored record.

    Args:
        reg_number (str): Registration number to look up.
        db_path (str): Optional database path override.

    Returns:
        dict: {'success': True, 'data': {...}} when found, or
              {'success': False, 'error': 'Student not found'} when missing.
    """
    conn = None
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT registration_number, first_name, surname, email, programme,
                   phone_number, registration_status
            FROM students
            WHERE registration_number = ?
            """,
            (reg_number,),
        )
        row = cursor.fetchone()
        if row is None:
            return {"success": False, "error": "Student not found"}

        return {
            "success": True,
            "data": {
                "registration_number": row["registration_number"],
                "first_name": row["first_name"],
                "surname": row["surname"],
                "email": row["email"],
                "programme": row["programme"],
                "phone_number": row["phone_number"],
                "registration_status": row["registration_status"],
            },
        }
    finally:
        if conn:
            conn.close()


def get_next_available_slot(conn=None):
    """
    Find the next available slot (0-3) for card assignment.

    Query logic:
        - Fetch all slot_index values where card_status != 'collected'
        - Return first unoccupied slot from [0, 1, 2, 3]
        - Return None if all 4 slots are occupied (batch full)

    Args:
        conn (sqlite3.Connection): Optional connection object. 
                                  If None, opens new connection (less efficient in transactions).

    Returns:
        int: Next available slot_index (0, 1, 2, or 3), or None if batch full

    Raises:
        sqlite3.OperationalError: If cards table missing or query fails

    Usage:
        slot = get_next_available_slot()
        if slot is None:
            raise ValueError("Batch full, all 4 slots assigned")
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    
    try:
        cursor = conn.cursor()
        # Fetch all occupied slots (cards not yet collected)
        cursor.execute(
            "SELECT slot_index FROM cards WHERE card_status != 'collected' ORDER BY slot_index"
        )
        occupied_slots = set(row[0] for row in cursor.fetchall())
        
        # Find first unoccupied slot
        for slot in TOTAL_SLOTS:
            if slot not in occupied_slots:
                logger.info(f"Next available slot: {slot}")
                return slot
        
        # All slots occupied
        logger.warning("Batch full: all 4 slots assigned")
        return None
    finally:
        if close_conn:
            conn.close()


def check_student_has_pin(reg_number, conn=None):
    """
    Check if student already has a PIN in authentication table.

    Used to determine if student is returning (has PIN) or first-year (no PIN).

    Args:
        reg_number (str): Student registration number
        conn (sqlite3.Connection): Optional connection for batch operations

    Returns:
        (bool, str or None): (has_pin, pin_hash)
            - has_pin: True if PIN exists in auth table, False otherwise
            - pin_hash: PIN hash if exists, None otherwise
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT pin_hash FROM authentication WHERE registration_number = ?",
            (reg_number,)
        )
        row = cursor.fetchone()
        
        if row and row[0]:  # pin_hash exists and not NULL
            logger.info(f"Student {reg_number}: returning student (PIN exists)")
            return True, row[0]
        else:
            logger.info(f"Student {reg_number}: first-year student (no PIN)")
            return False, None
    finally:
        if close_conn:
            conn.close()


def ingest_card(reg_number):
    """
    Ingest a single card: fetch student, generate OTP, send credentials, create records.

    **COMPLETE WORKFLOW:**

    Atomic transaction flow:
        1. Call api_client.get_student(reg_number) to fetch from university database
        2. If student not found: raise exception "Student not found"
        3. Generate OTP (6-digit) using secrets.randbelow()
        4. Check authentication table for existing PIN:
           - If PIN exists: returning student (is_temp_pin = FALSE)
           - If NO PIN: first-year student, generate temp PIN (is_temp_pin = TRUE)
        5. Hash OTP using bcrypt
        6. Hash PIN (if generated) using bcrypt
        7. Send SMS + Email with credentials:
           - Returning: OTP only
           - First-year: OTP + temporary PIN
        8. Find next available slot (0-3)
        9. If no slot available: raise exception "Batch full"
        10. Generate timestamp-based batch ID: "Batch_YYYYMMDD_HHMMSS"
        11. Begin transaction
        12. Insert/update student record in students table
        13. Insert/update authentication record with OTP hash, PIN hash, is_temp_pin
        14. Insert card record with slot_index, batch_id
        15. Log audit event (event_type='otp_sent', failure_type=NULL on success)
        16. Commit transaction
        17. Return success dict with slot_index, batch_id

    Args:
        reg_number (str): Student registration number (e.g., "2022-04-09050")

    Returns:
        dict: {
            'success': True,
            'slot_index': <0-3>,
            'student_name': 'First Surname',
            'batch_id': 'Batch_20260601_143025',
            'student_type': 'first_year|returning',
            'credentials_sent': True
        }
        OR
        dict: {
            'success': False,
            'error': 'Reason (Student not found|Batch full|SMS failed|etc)',
            'step': 'Which step failed: api_lookup|otp_generation|slot_assignment|sms_send|database'
        }

    Usage:
        result = ingest_card('2022-04-09050')
        if result['success']:
            print(f"✓ Card {result['slot_index']}, {result['student_type']}")
        else:
            print(f"✗ Failed at {result['step']}: {result['error']}")

    Called by:
        - main.py: handle_reg_submit() when student enters reg number manually
        - OCR pipeline: Once card capture + OCR completes (future phase)
    """
    conn = None
    try:
        # ===== STEP 1: Fetch student from university API =====
        logger.info(f"[{reg_number}] Step 1: Fetching student from university API...")
        api_result = get_student(reg_number)
        
        if not api_result.get("success"):
            error_msg = api_result.get("error", "Student not found")
            logger.error(f"[{reg_number}] API lookup failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "step": "api_lookup"
            }
        
        student_data = api_result.get("data", {})
        student_name = f"{student_data.get('first_name', '')} {student_data.get('surname', '')}"
        email = student_data.get("email")
        phone_number = student_data.get("phone_number")
        programme = student_data.get("programme", "Unknown")
        registration_status = student_data.get("registration_status", "active")
        
        logger.info(f"[{reg_number}] ✓ Student found: {student_name}")
        
        # ===== STEP 2: Generate OTP =====
        logger.info(f"[{reg_number}] Step 2: Generating OTP...")
        otp = generate_otp()
        otp_hash = hash_credential(otp)
        otp_expiry = datetime.now() + timedelta(hours=OTP_EXPIRY_HOURS)
        logger.info(f"[{reg_number}] ✓ OTP generated: {otp} (expires: {otp_expiry})")
        
        # ===== STEP 3: Check if student has existing PIN =====
        conn = get_db_connection()
        logger.info(f"[{reg_number}] Step 3: Checking for existing PIN...")
        has_pin, existing_pin_hash = check_student_has_pin(reg_number, conn)
        
        if has_pin:
            # Returning student: use existing PIN
            student_type = "returning"
            temp_pin = None
            temp_pin_hash = None
            is_temp_pin = False
            logger.info(f"[{reg_number}] ✓ Returning student (PIN exists)")
        else:
            # First-year student: generate temporary PIN
            student_type = "first_year"
            temp_pin = generate_temp_pin()
            temp_pin_hash = hash_credential(temp_pin)
            is_temp_pin = True
            logger.info(f"[{reg_number}] ✓ First-year student: temporary PIN generated {temp_pin}")
        
        # ===== STEP 4: Begin transaction for student record only =====
        logger.info(f"[{reg_number}] Step 4: Beginning student transaction...")
        cursor = conn.cursor()
        conn.execute("BEGIN TRANSACTION")
        
        # ===== STEP 5: Insert/update student record =====
        try:
            cursor.execute(
                """INSERT INTO students 
                   (registration_number, first_name, surname, email, programme, 
                    phone_number, registration_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(registration_number) DO UPDATE SET
                       first_name = excluded.first_name,
                       surname = excluded.surname,
                       email = excluded.email,
                       programme = excluded.programme,
                       phone_number = excluded.phone_number,
                       registration_status = excluded.registration_status""",
                (
                    reg_number,
                    student_data.get("first_name", ""),
                    student_data.get("surname", ""),
                    email,
                    programme,
                    phone_number,
                    registration_status,
                ),
            )
            logger.info(f"[{reg_number}] ✓ Inserted student record")
        except sqlite3.IntegrityError:
            logger.info(f"[{reg_number}] Student already exists, skipping insert")

        conn.commit()
        logger.info(f"[{reg_number}] ✓ Student transaction committed")

        # ===== STEP 6: Send SMS + Email after student row exists =====
        logger.info(f"[{reg_number}] Step 6: Sending credentials via SMS + Email...")
        try:
            send_result = send_credentials(
                reg_num=reg_number,
                otp=otp,
                temp_pin=temp_pin if student_type == "first_year" else None,
                db_path=DB_PATH,
            )

            if not send_result.get("success", False):
                logger.error(f"[{reg_number}] SMS/Email send failed: {send_result}")
                credentials_sent = False
            else:
                logger.info(f"[{reg_number}] ✓ Credentials sent successfully")
                credentials_sent = True
        except Exception as e:
            logger.error(f"[{reg_number}] SMS/Email send exception: {e}")
            credentials_sent = False

        # ===== STEP 7: Get slot assignment =====
        logger.info(f"[{reg_number}] Step 7: Finding next available slot...")
        slot_index = get_next_available_slot(conn)
        if slot_index is None:
            return {
                "success": False,
                "error": "Batch full, all 4 slots assigned",
                "step": "slot_assignment"
            }
        logger.info(f"[{reg_number}] ✓ Slot assigned: {slot_index}")

        # ===== STEP 8: Generate batch ID and session ID =====
        batch_id = datetime.now().strftime("Batch_%Y%m%d_%H%M%S")
        session_id = str(uuid.uuid4())
        logger.info(f"[{reg_number}] Generated batch_id={batch_id}, session_id={session_id}")

        # ===== STEP 9: Begin transaction for auth/card logging =====
        logger.info(f"[{reg_number}] Step 9: Beginning authentication/card transaction...")
        conn.execute("BEGIN TRANSACTION")

        # ===== STEP 10: Insert/update authentication record =====
        cursor.execute(
            "SELECT auth_id FROM authentication WHERE registration_number = ?",
            (reg_number,)
        )
        auth_exists = cursor.fetchone() is not None

        if auth_exists:
            cursor.execute(
                """UPDATE authentication 
                   SET otp_hash = ?, otp_expiry = ?, 
                       failed_otp_attempts = 0, lockout_expiry = NULL,
                       updated_at = datetime('now')
                   WHERE registration_number = ?""",
                (otp_hash, otp_expiry.isoformat(), reg_number)
            )
            logger.info(f"[{reg_number}] ✓ Updated authentication record (OTP refreshed)")
        else:
            cursor.execute(
                """INSERT INTO authentication 
                   (registration_number, otp_hash, otp_expiry, pin_hash, is_temp_pin,
                    failed_otp_attempts, failed_pin_attempts, lockout_expiry,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
                (
                    reg_number,
                    otp_hash,
                    otp_expiry.isoformat(),
                    temp_pin_hash if student_type == "first_year" else None,
                    is_temp_pin,
                    0,
                    0,
                    None,
                )
            )
            logger.info(f"[{reg_number}] ✓ Inserted authentication record")

        # ===== STEP 11: Insert card record =====
        cursor.execute(
            """INSERT INTO cards 
               (registration_number, slot_index, card_status, batch_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))""",
            (reg_number, slot_index, "pending", batch_id)
        )
        logger.info(f"[{reg_number}] ✓ Created card record (slot {slot_index})")

        # ===== STEP 12: Log audit event =====
        cursor.execute(
            """INSERT INTO audit_log 
               (event_time, registration_number, event_type, failure_type, session_id)
               VALUES (datetime('now'), ?, ?, ?, ?)""",
            (reg_number, "otp_sent", None, session_id)
        )
        logger.info(f"[{reg_number}] ✓ Logged audit event: otp_sent")

        # ===== STEP 13: Commit transaction =====
        conn.commit()
        logger.info(f"[{reg_number}] ✓ Transaction committed")
        
        return {
            "success": True,
            "slot_index": slot_index,
            "student_name": student_name,
            "batch_id": batch_id,
            "student_type": student_type,
            "credentials_sent": credentials_sent
        }
    
    except Exception as e:
        if conn:
            try:
                conn.rollback()
                logger.error(f"[{reg_number}] Transaction rolled back due to: {e}")
            except:
                pass
        logger.error(f"[{reg_number}] Ingestion failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "step": "database"
        }
    
    finally:
        if conn:
            conn.close()


def clear_database(db_path=None):
    """
    Delete all records from students, cards, authentication, audit_log, batches tables.
    
    Keeps schema intact. Useful for test cycles.
    
    Args:
        db_path (str): Path to database. Defaults to config.DB_PATH.
    
    Returns:
        dict: {'success': True, 'deleted_records': {'students': N, 'cards': N, ...}}
    
    Called by:
        - db/init_db.py with --reset CLI flag
        - Manual test setup scripts
    """
    conn = None
    try:
        if db_path is None:
            db_path = DB_PATH
        
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Delete all records (preserve foreign key relationships by order)
        deleted = {}
        
        # Delete audit log (no FK constraint)
        cursor.execute("DELETE FROM audit_log")
        deleted["audit_log"] = cursor.rowcount
        
        # Delete authentication (FK to students, but allow deletion)
        cursor.execute("DELETE FROM authentication")
        deleted["authentication"] = cursor.rowcount
        
        # Delete cards (FK to students)
        cursor.execute("DELETE FROM cards")
        deleted["cards"] = cursor.rowcount
        
        # Delete students (PK, referenced by FK)
        cursor.execute("DELETE FROM students")
        deleted["students"] = cursor.rowcount
        
        # Delete batches (referenced by cards, but already deleted cards)
        cursor.execute("DELETE FROM batches")
        deleted["batches"] = cursor.rowcount
        
        conn.commit()
        logger.info(f"Database cleared: {deleted}")
        
        return {
            "success": True,
            "deleted_records": deleted
        }
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database clear failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
    
    finally:
        if conn:
            conn.close()
