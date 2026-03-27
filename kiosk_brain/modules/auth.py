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

from datetime import datetime, timedelta
import sqlite3
import bcrypt
import secrets

def generate_otp():
    """Generate a cryptographically secure 6-digit OTP"""
    otp_number = secrets.randbelow(1_000_000)
    return f"{otp_number:06d}"

def store_otp_to_db(reg_number, otp_num, db_path="data/kiosk.db"):
    """Stores the OTP hash and adds a 24-hour expiry"""
    otp_hash = bcrypt.hashpw(otp_num.encode('utf-8'), bcrypt.gensalt())
    otp_expiry = datetime.utcnow() + timedelta(hours=24)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE authentication SET otp_hash = ?, otp_expiry = ? WHERE registration_number = ?", 
                   (otp_hash, otp_expiry, reg_number))
    
    conn.commit()
    conn.close()

def verify_otp(reg_number, otp_num, db_path="data/kiosk.db"):
    """Compares the student's OTP entry with the DB's"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT otp_hash, otp_expiry FROM authentication WHERE registration_number = ?", (reg_number,))
    result = cursor.fetchone()
    
    if result is None:
        conn.close()
        return {'success': False, 'error': 'NOT FOUND', 'message': "Registration number not found"}
    
    if result[1] < datetime.utcnow():
        conn.close()
        return {'success': False, 'error': 'EXPIRED', 'message': 'OTP has expired. Contact SMARTCARD'}
    
    is_valid = bcrypt.checkpw(otp_num.encode('utf-8'), result[0])
    if not is_valid:
        cursor.execute("UPDATE authentication SET failed_otp_attempts = failed_otp_attempts + 1 WHERE registration_number = ?", (reg_number,))
        conn.commit()

        cursor.execute("SELECT failed_otp_attempts FROM authentication WHERE registration_number = ?", (reg_number,))
        failed_otp_attempts = cursor.fetchone()

        if failed_otp_attempts[0] >= 3:
            lockout_time = datetime.utcnow() + timedelta(minutes=30)
            cursor.execute("UPDATE authentication SET lockout_expiry = ? WHERE registration_number = ?", (lockout_time, reg_number))
            conn.commit()
            conn.close()
            return {'success': False, 'error': 'LOCKED', 'message': 'Too many retries. Try after 30 minutes'}

        conn.close()
        return {'success': False, 'error': 'INVALID', 'message': 'Incorrect OTP. Try again.'}
    
    conn.close()
    return {'success': True, 'error': None, 'message': 'OTP verified successfully'}