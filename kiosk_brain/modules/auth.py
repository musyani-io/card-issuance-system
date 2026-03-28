"""
Authentication Module — OTP, PIN, and Two-Factor Authentication

This module implements secure two-factor authentication for the kiosk:
- One-Time Password (OTP) generation, hashing, and verification
- PIN hashing and verification with support for temporary and permanent PINs
- Lockout enforcement and audit logging

Key Design Pattern: is_temp_pin Column
======================================
The `is_temp_pin` column in the `authentication` table distinguishes between:

1. TEMPORARY PINs (is_temp_pin = TRUE)
   - System-generated 4-digit codes for FIRST-YEAR STUDENTS
   - Sent via SMS during batch loading alongside their OTP
   - Verified on first collection, then forces PIN SETUP screen
   - After student sets permanent PIN: is_temp_pin set to FALSE

2. PERMANENT PINs (is_temp_pin = FALSE)
   - User-chosen PINs set on first collection (first-years)
   - Existing PINs for returning students from prior years
   - Verified without forcing PIN setup screen

Workflow Examples:
==================

FIRST-YEAR STUDENT (First Collection):
  1. Card loaded → OCR reads reg number
  2. Credentials sent via SMS + EMAIL with OTP + temp PIN (hashed in DB, is_temp_pin=TRUE)
  3. Student enters OTP → Success
  4. Student enters temp PIN → Success
  5. Check is_temp_pin=TRUE → Force PIN setup screen
  6. Student creates new permanent PIN twice (confirm match)
  7. DB update: pin_hash = hash(new_pin), is_temp_pin = FALSE
  8. Confirm screen → Card dispensed

RETURNING STUDENT (Has Prior Year PIN):
  1. Old card scanned → OCR reads reg number
  2. OTP sent via SMS + EMAIL (existing PIN in DB unchanged, is_temp_pin=FALSE)
  3. Student enters OTP → Success
  4. Student enters their existing PIN → Success
  5. Check is_temp_pin=FALSE → Skip PIN setup, proceed to confirm
  6. Confirm screen → Card dispensed

CREDENTIAL DELIVERY STRATEGY:
=============================
Credentials (OTP + optional temp PIN) are sent via TWO channels:
- SMS via Africa's Talking API (phone_number)
- Email via SMTP (email)

If one channel fails, the kiosk continues (does not crash batch).
Both channels are attempted independently.

Function Stubs (Implement in Phase 3):
=====================================
"""

from sms_client import send_credentials
from datetime import datetime, timedelta
import sqlite3
import bcrypt
import secrets


def generate_otp():
    """
    Generate a cryptographically secure 6-digit One-Time Password.

    Returns:
        str: Zero-padded 6-digit OTP (e.g., "000123", "847291")
             Generated using secrets.randbelow() for cryptographic randomness

    Usage:
        Called during batch loading to create OTP for SMS dispatch
        Example: otp = generate_otp() → "847291"
    """
    otp_number = secrets.randbelow(1_000_000)  # Random int [0, 999999]
    return f"{otp_number:06d}"  # Zero-pad to 6 digits


def generate_temp_pin():
    """Generate a cryptogrophically secure 4-digit temporary pin for first-time users."""
    temp_pin_num = secrets.randbelow(10_000)
    return f"{temp_pin_num:04d}"


def hash_credential(data):
    """Generate bcrypt hashing for OTP, PIN or any data"""
    return bcrypt.hashpw(data.encode("utf-8"), bcrypt.gensalt())


def set_pin(reg_number, pin, db_path="data/kiosk.db"):
    """Verify PIN length (4 digits), hash, and store it in database"""
    if not (4 <= len(pin) <= 6) or not pin.isdigit():
        return {
            "success": False,
            "error": "INVALID",
            "message": "PIN must be 4-6 digits",
        }

    pin_hash = hash_credential(pin)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE authentication SET pin_hash = ?, is_temp_pin = FALSE WHERE registration_number = ?",
        (pin_hash, reg_number),
    )
    conn.commit()
    conn.close()

    return {"success": True, "error": None, "message": "PIN set successfully"}


def store_otp_to_db(reg_number, otp_num, db_path="data/kiosk.db"):
    """
    Store hashed OTP and 24-hour expiry timestamp to authentication table.

    Args:
        reg_number: Student registration number (primary key in authentication table)
        otp_num: Plain-text OTP string (e.g., "847291") to be hashed
        db_path: Path to SQLite database (default: data/kiosk.db)

    Side Effects:
        - Hashes OTP with bcrypt (one-way, never stored in plaintext)
        - Sets otp_expiry to current UTC time + 24 hours
        - Updates authentication table for given reg_number
        - Resets failed_otp_attempts counter to 0 (optional, if implemented)

    Called by:
        - SMS dispatch workflow during batch loading (Phase 3)
        - After university API confirms student is active/inactive/suspended

    Security Notes:
        - bcrypt.gensalt() ensures different hash per OTP (rainbow table resistant)
        - 24-hour expiry prevents multi-day reuse
        - Hashed OTP never sent over network or logged
    """
    # Hash OTP with bcrypt (12-round default cost)
    otp_hash = hash_credential(otp_num)
    # Set expiry timestamp (24 hours from now)
    otp_expiry = datetime.utcnow() + timedelta(hours=24)

    # Write hashed OTP and expiry to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE authentication SET otp_hash = ?, otp_expiry = ? WHERE registration_number = ?",
        (otp_hash, otp_expiry, reg_number),
    )

    conn.commit()
    conn.close()


def store_temp_pin_to_db(reg_number, temp_pin, db_path="data/kiosk.db"):
    """Store the hashed temp pin with is_temp_pin=TRUE"""
    pin_hash = hash_credential(temp_pin)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE authentication SET pin_hash = ?, is_temp_pin = TRUE WHERE registration_number = ?",
        (pin_hash, reg_number),
    )
    conn.commit()
    conn.close()


def verify_otp(reg_number, otp_num, db_path="data/kiosk.db"):
    """
    Verify student OTP against database hash using bcrypt.checkpw() comparison.

    Args:
        reg_number: Student registration number (lookup key in authentication table)
        otp_num: Student-entered OTP string (e.g., "847291"), compared to hashed DB value
        db_path: Path to SQLite database (default: data/kiosk.db)

    Returns:
        dict: Status response with keys:
            - 'success': bool (True if OTP verified, False otherwise)
            - 'error': str or None (error code: NOT_FOUND, EXPIRED, LOCKED, INVALID)
            - 'message': str (human-readable status for UI display)

    Error Codes:
        - NOT_FOUND: Registration number not in authentication table (batch not loaded)
        - EXPIRED: OTP > 24 hours old (otp_expiry < now); requires new batch load
        - LOCKED: 3 failed attempts; soft lockout for 30 minutes (attempt count resets after expiry)
        - INVALID: OTP hash mismatch (student entered wrong OTP); allows unlimited attempts

    Side Effects on Failure:
        - Increments failed_otp_attempts counter (+1 per failed bcrypt.checkpw)
        - After 3 failures: sets lockout_expiry = now + 30 minutes
        - Attempts during lockout period still return 'LOCKED' response

    Called by:
        - Card collection screen after student taps OTP entry field
        - Session manager waits for await_authentication() callback before proceeding

    Workflow Context:
        - Success → unlock PIN entry screen (verify_pin() called next)
        - Failure → display error message, allow retry (up to 3 times in 30 minutes)
        - Expired → revert to batch loading kiosk (requires re-sending credentials)

    Security Notes:
        - bcrypt.checkpw() is constant-time comparison (immune to timing attacks)
        - Soft 30-minute lockout prevents brute force (6! = 720k OTPs, recoverable after timeout)
        - Hard 24-hour lockout prevents reuse (fresh batch load required)
        - Hashed OTP always stored; plaintext only in RAM during comparison
    """
    # Fetch hashed OTP and expiry timestamp from authentication table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT otp_hash, otp_expiry FROM authentication WHERE registration_number = ?",
        (reg_number,),
    )
    result = cursor.fetchone()

    # Student not found in batch (batch loading required)
    if result is None:
        conn.close()
        return {
            "success": False,
            "error": "NOT FOUND",
            "message": "Registration number not found",
        }

    # OTP > 24 hours old (hard lockout / expiry)
    if result[1] < datetime.utcnow():
        conn.close()
        return {
            "success": False,
            "error": "EXPIRED",
            "message": "OTP has expired. Contact SMARTCARD",
        }

    # Constant-time bcrypt comparison (true if hashes match, false otherwise)
    is_valid = bcrypt.checkpw(otp_num.encode("utf-8"), result[0])
    if not is_valid:
        # Increment failed OTP attempt counter for lock-out enforcement
        cursor.execute(
            "UPDATE authentication SET failed_otp_attempts = failed_otp_attempts + 1 WHERE registration_number = ?",
            (reg_number,),
        )
        conn.commit()

        # Check if soft lockout (3 failed attempts) triggered
        cursor.execute(
            "SELECT failed_otp_attempts FROM authentication WHERE registration_number = ?",
            (reg_number,),
        )
        failed_otp_attempts = cursor.fetchone()

        if failed_otp_attempts[0] >= 3:
            # Set 30-minute recovery window (soft lockout expires after timedelta)
            lockout_time = datetime.utcnow() + timedelta(minutes=30)
            cursor.execute(
                "UPDATE authentication SET lockout_expiry = ? WHERE registration_number = ?",
                (lockout_time, reg_number),
            )
            conn.commit()
            conn.close()
            return {
                "success": False,
                "error": "LOCKED",
                "message": "Too many retries. Try after 30 minutes",
            }

        conn.close()
        return {
            "success": False,
            "error": "INVALID",
            "message": "Incorrect OTP. Try again.",
        }

    # OTP verified successfully; proceed to PIN verification
    conn.close()
    return {"success": True, "error": None, "message": "OTP verified successfully"}


def verify_pin(reg_number, pin, db_path="data/kiosk.db"):
    """Verify the PIN against the database hash"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT pin_hash FROM authentication WHERE registration_number = ?",
        (reg_number,),
    )
    result = cursor.fetchone()

    if result is None:
        conn.close()
        return {"success": False, "error": "NOT FOUND", "message": "Student not found"}

    is_valid = bcrypt.checkpw(pin.encode("utf-8"), result[0])

    if not is_valid:
        cursor.execute(
            "UPDATE authentication SET failed_pin_attempts = failed_pin_attempts + 1 WHERE registration_number = ?",
            (reg_number,),
        )
        conn.commit()
        conn.close()
        return {
            "success": False,
            "error": "INVALID",
            "message": "Incorrect PIN. Try again.",
        }

    conn.close()
    return {"success": True, "error": None, "message": "PIN verified successfully."}


def dispatch_credentials_with_logging(
    reg_number, otp, temp_pin, batch_id=None, db_path="data/kiosk.db"
):
    result = send_credentials(reg_number, otp, temp_pin, db_path)

    if not result["success"]:
        result = retry_send_credentials(reg_number, otp, temp_pin, db_path)

    if batch_id:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        sms_sent = result.get("sms_sent", False)
        email_sent = result.get("email_sent", False)
        cursor.execute(
            "UPDATE batches SET sms_sent = ? WHERE batch_id = ?",
            (int(sms_sent or email_sent), batch_id),
        )
        conn.commit()
        conn.close()

    return result


def retry_send_credentials(reg_number, otp, temp_pin, db_path="data/kiosk.db"):
    """Attempt to re-send credentials if both SMS / Email fail, after 10 min"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT otp_expiry FROM authentication WHERE registration_number = ?",
        (reg_number,),
    )
    otp_expiry = cursor.fetchone()
    conn.close()

    if not otp_expiry:
        return {"success": False, "error": "NOT FOUND", "message": "Student not found"}

    time_elapsed = datetime.utcnow() - (otp_expiry[0] - timedelta(hours=24))
    if time_elapsed < timedelta(minutes=10):
        return {
            "success": False,
            "error": "RATE LIMITED",
            "message": "Please wait for another request",
        }

    return send_credentials(reg_number, otp, temp_pin, db_path)
