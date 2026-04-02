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

from modules.sms_client import send_credentials
from datetime import datetime, timedelta, timezone
import sqlite3
import bcrypt
import secrets


def parse_db_datetime(value):
    """
    Parse SQLite datetime string back to timezone-aware datetime object.
    SQLite stores datetimes as ISO format strings (YYYY-MM-DD HH:MM:SS.SSS).
    Converts to UTC timezone-aware datetime to avoid deprecation warnings.

    Args:
        value: DateTime string from SQLite, or None

    Returns:
        datetime object (UTC timezone-aware), or None if input is None or empty
    """
    if value is None or value == "":
        return None
    try:
        # Parse ISO format and ensure timezone-aware
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # If naive, add UTC timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        try:
            # Fallback: parse without timezone and add UTC
            dt = datetime.strptime(value.split(".")[0], "%Y-%m-%d %H:%M:%S")
            return dt.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            return None


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
    """
    Generate a cryptographically secure 4-digit temporary PIN for first-year students.

    Returns:
        str: Zero-padded 4-digit PIN (e.g., "0001", "8472")
             Generated using secrets.randbelow() for cryptographic randomness

    Usage:
        Called during batch loading to create temp PIN for first-year students
        Sent alongside OTP via SMS + Email
        Example: temp_pin = generate_temp_pin() → "8472"

    Security Notes:
        - Differs from permanent PIN (user-chosen), temporary PIN is system-generated
        - 4-digit space (10,000 possibilities) acceptable for temporary use during batch loading
        - Students must set permanent PIN on first collection (is_temp_pin flag transition)
    """
    temp_pin_num = secrets.randbelow(10_000)  # Random int [0, 9999]
    return f"{temp_pin_num:04d}"  # Zero-pad to 4 digits


def hash_credential(data):
    """
    Hash any credential (OTP, PIN, password) using bcrypt for secure storage.

    Args:
        data: Plain-text string to hash (e.g., OTP "847291" or PIN "1234")

    Returns:
        bytes: Bcrypt hash blob (e.g., b'$2b$12$...') with embedded salt
              Hash is one-way: cannot derive original data from hash

    Called by:
        - store_otp_to_db() for OTP hashing
        - store_temp_pin_to_db() for system-generated temp PIN hashing
        - set_pin() for user-chosen permanent PIN hashing

    Security Notes:
        - bcrypt.gensalt() embeds random salt in hash (prevents rainbow table attacks)
        - 12-round cost factor slows hash computation (prevents brute force)
        - Each call produces different hash (same input → different output)
        - Hash never logged, stored only in SQLite authentication table
    """
    return bcrypt.hashpw(
        data.encode("utf-8"), bcrypt.gensalt()
    )  # Encode string to bytes, apply bcrypt hashing


def set_pin(reg_number, pin, db_path="data/kiosk.db"):
    """
    Verify PIN strength, hash, and store permanent PIN to authentication table.

    Args:
        reg_number: Student registration number (primary key in authentication table)
        pin: User-chosen PIN string to validate and store (must be 4-6 numeric digits)
        db_path: Path to SQLite database (default: data/kiosk.db)

    Returns:
        dict: Status response with keys:
            - 'success': bool (True if PIN set successfully, False if validation fails)
            - 'error': str or None (error code: INVALID if constraints violated)
            - 'message': str (human-readable description for UI display)

    Side Effects on Success:
        - Hashes PIN with bcrypt.gensalt()
        - Updates authentication table: pin_hash = hashed_pin, is_temp_pin = FALSE
        - Transitions student from temporary PIN (system-generated) to permanent PIN (user-chosen)

    Validation Rules:
        - PIN length: 4–6 digits (4-digit minimum to prevent trivial PINs)
        - PIN format: only numeric characters (digits only, no symbols/letters)
        - Invalid PINs return INVALID error immediately (no database update)

    Called by:
        - Student collection screen during first-year student flow
        - After verify_otp() succeeds and is_temp_pin=TRUE check triggers PIN setup screen

    Security Notes:
        - Permanent PIN is user-chosen (stronger than system-generated temp PIN)
        - is_temp_pin flag transition prevents accidental re-entry into PIN setup screen
        - Changes remain visible to student until collection confirmation
    """
    # Validate PIN format: 4-6 digits, numeric only
    if not (4 <= len(pin) <= 6) or not pin.isdigit():
        return {
            "success": False,
            "error": "INVALID",
            "message": "PIN must be 4-6 digits",
        }

    # Hash PIN and update database record
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


def enforce_pin_setup(reg_number, db_path="data/kiosk.db"):
    """
    Check if student has temporary PIN and requires permanent PIN setup before collection.

    Args:
        reg_number: Student registration number (lookup key in authentication table)
        db_path: Path to SQLite database (default: data/kiosk.db)

    Returns:
        dict: Status response with keys:
            - 'success': bool (True if lookup succeeds, False if student not found)
            - 'requires_pin_setup': bool or None (True if is_temp_pin=TRUE, False if is_temp_pin=FALSE, None on error)
            - 'message': str (human-readable description)

    Side Effects:
        - None (read-only query)

    Called by:
        - Pin entry screen after verify_otp() confirms OTP is valid
        - Determines whether UI should show PIN setup screen or skip to confirmation

    Workflow Context:
        - FIRST-YEAR STUDENT: is_temp_pin=TRUE → force PIN setup screen
        - RETURNING STUDENT: is_temp_pin=FALSE → skip PIN setup, proceed to confirmation

    Security Notes:
        - Read-only operation (no state change)
        - Critical gate for first-year workflow (prevents accidental reset of permanent PINs)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Query is_temp_pin flag to determine flow
    cursor.execute(
        "SELECT is_temp_pin FROM authentication WHERE registration_number = ?",
        (reg_number,),
    )
    is_temp_pin = cursor.fetchone()
    conn.close()

    if is_temp_pin is None:
        return {"success": False, "error": "NOT FOUND", "message": "Student not found"}

    return {
        "success": True,
        "requires_pin_setup": is_temp_pin[
            0
        ],  # Boolean flag: True = temp PIN, False = permanent PIN
        "message": "PIN Check complete",
    }


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
    otp_expiry = datetime.now(timezone.utc) + timedelta(hours=24)

    # Write hashed OTP and expiry to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE authentication SET otp_hash = ?, otp_expiry = ? WHERE registration_number = ?",
        (otp_hash, otp_expiry.isoformat(), reg_number),
    )

    conn.commit()
    conn.close()


def store_temp_pin_to_db(reg_number, temp_pin, db_path="data/kiosk.db"):
    """
    Store hashed temporary PIN with is_temp_pin=TRUE flag to authentication table.

    Args:
        reg_number: Student registration number (primary key in authentication table)
        temp_pin: System-generated temp PIN string (e.g., "8472") to be hashed
        db_path: Path to SQLite database (default: data/kiosk.db)

    Side Effects:
        - Hashes temp PIN with bcrypt.gensalt()
        - Updates authentication table: pin_hash = hashed_pin, is_temp_pin = TRUE
        - Marks student as first-year (must set permanent PIN before collection)
        - Sets flag for enforce_pin_setup() gate to trigger PIN setup screen

    Called by:
        - Batch loading phase after OTP generation and storage
        - For first-year students only (returning students have permanent PINs)
        - Alongside send_credentials() to deliver temp PIN via SMS

    Security Notes:
        - Temporary PIN is system-generated (6! = 720k possibilities, same space as OTP)
        - is_temp_pin=TRUE flag ensures student cannot bypass PIN setup on first collection
        - Temporary PIN stored as hash (never plaintext, even in database)
        - Overwritten by permanent PIN on first-year student's first collection
    """
    # Hash temp PIN with bcrypt
    pin_hash = hash_credential(temp_pin)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Update authentication record: store hash and flag it as temporary
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
    # Fetch hashed OTP, expiry timestamp, lockout status, and failure count from authentication table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT otp_hash, otp_expiry, lockout_expiry, failed_otp_attempts FROM authentication WHERE registration_number = ?",
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

    # Parse datetime strings from SQLite
    otp_hash, otp_expiry_str, lockout_expiry_str, failed_attempts = result
    otp_expiry = parse_db_datetime(otp_expiry_str)
    lockout_expiry = parse_db_datetime(lockout_expiry_str)

    # Check if currently in OTP lockout (30-minute window)
    if lockout_expiry and lockout_expiry > datetime.now(timezone.utc):
        conn.close()
        return {
            "success": False,
            "error": "LOCKED",
            "message": "Too many retries. Try after 30 minutes",
        }

    # If no lockout set yet but failures >= 3, set the lockout now
    if (
        not lockout_expiry or lockout_expiry <= datetime.now(timezone.utc)
    ) and failed_attempts >= 3:
        lockout_time = datetime.now(timezone.utc) + timedelta(minutes=30)
        cursor.execute(
            "UPDATE authentication SET lockout_expiry = ? WHERE registration_number = ?",
            (lockout_time.isoformat(), reg_number),
        )
        conn.commit()
        conn.close()
        log_audit_event(reg_number, "OTP LOCKOUT", "THRESHOLD EXCEEDED", None, db_path)
        return {
            "success": False,
            "error": "LOCKED",
            "message": "Too many retries. Try after 30 minutes",
        }

    # OTP > 24 hours old (hard lockout / expiry)
    if otp_expiry and otp_expiry < datetime.now(timezone.utc):
        conn.close()
        return {
            "success": False,
            "error": "EXPIRED",
            "message": "OTP has expired. Contact SMARTCARD",
        }

    # Constant-time bcrypt comparison (true if hashes match, false otherwise)
    is_valid = bcrypt.checkpw(otp_num.encode("utf-8"), otp_hash)
    if not is_valid:
        # Increment failed OTP attempt counter for audit logging
        cursor.execute(
            "UPDATE authentication SET failed_otp_attempts = failed_otp_attempts + 1 WHERE registration_number = ?",
            (reg_number,),
        )
        conn.commit()
        conn.close()
        log_audit_event(reg_number, "OTP FAILED", "INVALID", None, db_path)
        return {
            "success": False,
            "error": "INVALID",
            "message": "Incorrect OTP. Try again.",
        }

    # OTP verified successfully; proceed to PIN verification
    conn.close()
    log_audit_event(reg_number, "OTP VERIFIED", None, None, db_path)
    return {"success": True, "error": None, "message": "OTP verified successfully"}


def verify_pin(reg_number, pin, db_path="data/kiosk.db"):
    """
    Verify student PIN against database hash using bcrypt.checkpw() comparison.

    Args:
        reg_number: Student registration number (lookup key in authentication table)
        pin: Student-entered PIN string (e.g., "1234"), compared to hashed DB value
        db_path: Path to SQLite database (default: data/kiosk.db)

    Returns:
        dict: Status response with keys:
            - 'success': bool (True if PIN verified, False otherwise)
            - 'error': str or None (error code: NOT_FOUND, LOCKED, INVALID)
            - 'message': str (human-readable status for UI display)

    Error Codes:
        - NOT_FOUND: Registration number not in authentication table
        - LOCKED: 3 failed attempts within 24-hour window (hard lockout)
        - INVALID: PIN hash mismatch (student entered wrong PIN); allows unlimited attempts

    Side Effects on Failure:
        - Increments failed_pin_attempts counter (+1 per failed bcrypt.checkpw)
        - After 3 failures: sets lockout_expiry = now + 24 hours (HARD lockout, not soft)
        - Attempts during lockout period return 'LOCKED' response and reset counter

    Called by:
        - Card collection screen after student taps PIN entry field
        - After verify_otp() succeeds (PIN is second factor)

    Workflow Context:
        - Success → proceed to confirm screen (dispatch card)
        - Failure → display error message, allow retry (up to 3 times in 24 hours)
        - Lockout → block all collection attempts for 24 hours (harder penalty than OTP)

    Security Notes:
        - bcrypt.checkpw() is constant-time comparison (immune to timing attacks)
        - Hard 24-hour lockout (vs OTP's 30-minute soft lockout) reflects higher sensitivity
        - PIN is second factor after OTP (defense in depth)
        - Failed PIN attempts audited to audit_log for suspicious pattern detection
    """
    # Fetch hashed PIN, lockout status, and failure count from authentication table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT pin_hash, lockout_expiry, failed_pin_attempts FROM authentication WHERE registration_number = ?",
        (reg_number,),
    )
    result = cursor.fetchone()

    # Student not found in authentication table
    if result is None:
        conn.close()
        return {"success": False, "error": "NOT FOUND", "message": "Student not found"}

    # Parse datetime strings from SQLite
    pin_hash, lockout_expiry_str, failed_attempts = result
    lockout_expiry = parse_db_datetime(lockout_expiry_str)

    # Check if currently in PIN lockout (24-hour hard lockout window)
    if lockout_expiry and lockout_expiry > datetime.now(timezone.utc):
        conn.close()
        return {
            "success": False,
            "error": "LOCKED",
            "message": "Too many retries. Try after 24 hours",
        }

    # If no lockout set yet but failures >= 3, set the lockout now (transition from grace to lockout)
    if (
        not lockout_expiry or lockout_expiry <= datetime.now(timezone.utc)
    ) and failed_attempts >= 3:
        lockout_time = datetime.now(timezone.utc) + timedelta(hours=24)
        cursor.execute(
            "UPDATE authentication SET lockout_expiry = ? WHERE registration_number = ?",
            (lockout_time.isoformat(), reg_number),
        )
        conn.commit()
        conn.close()
        log_audit_event(reg_number, "PIN LOCKOUT", "THRESHOLD EXCEEDED", None, db_path)
        return {
            "success": False,
            "error": "LOCKED",
            "message": "Too many retries. Try after 24 hours",
        }

    # Constant-time bcrypt comparison (true if hashes match, false otherwise)
    is_valid = bcrypt.checkpw(pin.encode("utf-8"), pin_hash)

    if not is_valid:
        # Increment failed PIN attempt counter for lockout enforcement
        cursor.execute(
            "UPDATE authentication SET failed_pin_attempts = failed_pin_attempts + 1 WHERE registration_number = ?",
            (reg_number,),
        )
        conn.commit()
        conn.close()
        log_audit_event(reg_number, "PIN FAILED", "INVALID", None, db_path)
        return {
            "success": False,
            "error": "INVALID",
            "message": "Incorrect PIN. Try again.",
        }

    # PIN verified successfully; proceed to collection confirmation
    conn.close()
    log_audit_event(reg_number, "PIN VERIFIED", None, None, db_path)
    return {"success": True, "error": None, "message": "PIN verified successfully."}


def dispatch_credentials_with_logging(
    reg_number, otp, temp_pin, batch_id=None, db_path="data/kiosk.db"
):
    """
    Send OTP and temporary PIN credentials via SMS+Email, with retry and batch audit logging.

    Args:
        reg_number: Student registration number (used to look up phone/email)
        otp: One-Time Password string (e.g., "847291") to send
        temp_pin: Temporary PIN string (e.g., "8472") or None for returning students
        batch_id: Optional batch ID to log credential delivery status to batches table
        db_path: Path to SQLite database (default: data/kiosk.db)

    Returns:
        dict: Delivery result with keys:
            - 'success': bool (True if at least one channel succeeded)
            - 'sms_sent': bool (True if SMS delivery succeeded)
            - 'email_sent': bool (True if email delivery succeeded)
            - 'error': str or None (error code if both channels failed)
            - 'message': str (human-readable description)

    Side Effects:
        - Calls send_credentials() (BRIQ Solutions SMS + SMTP email)
        - On first failure: retries via retry_send_credentials() after 10-minute grace period
        - If batch_id provided: updates batches table with sms_sent flag (True if either channel succeeded)

    Called by:
        - Batch loading phase (staff workflow)
        - After card ingestion, before storing card record
        - For both first-year (with temp PIN) and returning students (without temp PIN)

    Failure Handling:
        - SMS fails → retries after 10 minutes (graceful degradation)
        - Email fails → retries after 10 minutes (graceful degradation)
        - Both fail → credential delivery incomplete (student cannot collect card without OTP)
        - Admin must retry dispatch manually or trigger new batch load

    Audit Trail:
        - batch_id parameter links delivery status to staff batch record
        - Tracks which batches had full credential delivery vs partial/failed
    """
    # Send credentials via both SMS and email (independent channels)
    result = send_credentials(reg_number, otp, temp_pin, db_path)

    # If both channels failed, retry after 10-minute grace period
    if not result["success"]:
        result = retry_send_credentials(reg_number, otp, temp_pin, db_path)

    # Log credential delivery status to batch audit trail
    if batch_id:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Mark batch as having sent credentials if at least one channel succeeded
        sms_sent = result.get("sms_sent", False)
        email_sent = result.get("email_sent", False)
        cursor.execute(
            "UPDATE batches SET sms_sent = ? WHERE batch_id = ?",
            (int(sms_sent or email_sent), batch_id),  # Convert bool to 0/1 for SQLite
        )
        conn.commit()
        conn.close()

    return result


def retry_send_credentials(reg_number, otp, temp_pin, db_path="data/kiosk.db"):
    """
    Retry credential delivery after 10-minute grace period if initial send failed.

    Args:
        reg_number: Student registration number (lookup key)
        otp: One-Time Password string to resend
        temp_pin: Temporary PIN string to resend (or None for returning students)
        db_path: Path to SQLite database (default: data/kiosk.db)

    Returns:
        dict: Delivery result (same structure as send_credentials())
            - 'success': bool (True if retry succeeded)
            - 'sms_sent', 'email_sent': bool flags for each channel
            - 'error': str (RATE_LIMITED if < 10 minutes since OTP generation)

    Side Effects:
        - Checks elapsed time since OTP creation (otp_expiry - 24 hours)
        - If < 10 minutes: returns RATE_LIMITED error (prevents credential spam)
        - If >= 10 minutes: calls send_credentials() to retry both channels

    Called by:
        - dispatch_credentials_with_logging() on initial send failure
        - After 10-minute grace period to avoid barrage of SMS/emails

    Rate Limiting:
        - Grace period: 10 minutes (prevents credential spam)
        - Hard expiry: 24 hours (OTP expires regardless of retry attempts)
        - Allows recovery from transient network failures without overwhelming student

    Workflow Context:
        - Part of graceful credential delivery degradation
        - If retry still fails: admin must manually investigate and retry
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Query OTP expiry to calculate elapsed time since batch load
    cursor.execute(
        "SELECT otp_expiry FROM authentication WHERE registration_number = ?",
        (reg_number,),
    )
    otp_expiry = cursor.fetchone()
    conn.close()

    if not otp_expiry:
        return {"success": False, "error": "NOT_FOUND", "message": "Student not found"}

    # Calculate time elapsed since OTP generation (otp_expiry = now + 24h, so now = otp_expiry - 24h)
    time_elapsed = datetime.now(timezone.utc) - (otp_expiry[0] - timedelta(hours=24))
    # Check if grace period (10 minutes) has passed
    if time_elapsed < timedelta(minutes=10):
        return {
            "success": False,
            "error": "RATE_LIMITED",
            "message": "Please wait for another request",
        }

    # Grace period passed; retry credential delivery
    return send_credentials(reg_number, otp, temp_pin, db_path)


def log_audit_event(
    reg_number, event_type, failure_type=None, session_id=None, db_path="data/kiosk.db"
):
    "Log various events into the audit_log table"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_log (event_time, registration_number, event_type, failure_type, session_id) VALUES (?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc), reg_number, event_type, failure_type, session_id),
    )
    conn.commit()
    conn.close()
