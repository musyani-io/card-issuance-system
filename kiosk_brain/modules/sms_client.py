"""
SMS and Email Credential Delivery Client

This module sends OTP and temporary PIN credentials to students via two independent channels:
- Africa's Talking SMS gateway (primary, instant delivery)
- SMTP email via Gmail app-specific passwords (fallback, reliable)

Design Pattern: Graceful Degradation
====================================

Both channels are attempted independently:
- If SMS fails (network error, invalid number): email can still succeed
- If email fails (SMTP error, invalid address): SMS can still succeed
- If both fail: credential delivery incomplete (student must retry via admin)

Success is defined as: at least ONE channel succeeded (sms_sent OR email_sent)

Configuration:
==============

Required environment variables in config.py:
- AFRICA_TALKING_API_KEY: Africa's Talking sandbox/production API key
- AFRICA_TALKING_USERNAME: Africa's Talking username
- SMTP_EMAIL: Gmail address with app-specific password enabled
- APP_PASSWORD: Gmail app-specific password (format: "xxxx xxxx xxxx xxxx")

Migration Path:
===============

Development:  Mock credentials, no actual SMS/email sending
Production:   Real Africa's Talking account, real Gmail credentials

No code changes needed—only config.py values change between environments.
"""

from config import (
    BRIQ_API_ENDPOINT,
    BRIQ_API_KEY,
    BRIQ_SENDER_ID,
    SMTP_EMAIL,
    APP_PASSWORD,
)
from email.mime.text import MIMEText
import requests
import smtplib
import sqlite3


def send_credentials(reg_num, otp, temp_pin=None, db_path="data/kiosk.db"):
    """
    Send OTP and optional temporary PIN to student via SMS + Email.

    Args:
        reg_num: Student registration number (lookup key for phone/email)
        otp: One-Time Password string (e.g., "847291") to send
        temp_pin: Optional temporary PIN (e.g., "8472") for first-year students
                 None for returning students who have existing PINs
        db_path: Path to SQLite database (default: data/kiosk.db)

    Returns:
        dict: Delivery result with keys:
            - 'success': bool (True if at least one channel succeeded)
            - 'sms_sent': bool (True if Africa's Talking SMS delivered)
            - 'email_sent': bool (True if SMTP email sent)
            - 'sms_error': str or None (error description if SMS failed)
            - 'email_error': str or None (error description if email failed)

    Called by:
        - dispatch_credentials_with_logging() in auth.py (retry handler)
        - Batch loading phase (staff workflow)

    Database Query:
        - Fetches (first_name, surname, email, phone_number) from students table
        - Returns NOT_FOUND error if reg_num not in database

    Message Format:
        SMS: "Dear {SURNAME}, your card is available at the kiosk. Your SMARTCARD OTP is {OTP}.
             [Optional: Temporary PIN: {PIN}.] Valid for 24 hours"

        Email: HTML email with formatted credentials, personalized for student
               Includes instruction: "You will set a permanent PIN on collection." (if temp_pin)

    Failure Handling:
        - SMS error (invalid number, network timeout): sms_sent=False, continues to email
        - Email error (invalid address, SMTP failure): email_sent=False, SMS result preserved
        - Both fail: success=False, both error fields populated
        - One succeeds: success=True, student can use that channel's credentials

    Security Notes:
        - OTP/PIN never logged to file or database (transient, memory-only)
        - Email body includes HTML formatting (visual clarity)
        - Phone number and email lookup from students table (batches must load students first)
        - Africa's Talking API key and Gmail app password in config.py (not versioned)
    """

    # Query student contact info from database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT first_name, surname, email, phone_number FROM students WHERE registration_number = ?",
        (reg_num,),
    )
    student = cursor.fetchone()

    if student is None:
        conn.close()
        return {
            "success": False,
            "error": "Student not found",
            "sms_sent": False,
            "email_sent": False,
        }

    first_name, surname, email, phone_number = student
    first_name = first_name.upper()  # Format name for greeting
    surname = surname.upper()
    # Construct SMS message with OTP (and optional temp PIN)
    sms_message = f"""Dear {surname}, your card is available at the kiosk.
    Your SMARTCARD One-Time Password (OTP) is {otp}."""

    if temp_pin:
        sms_message += (
            f" Temporary PIN: {temp_pin}."  # First-year students get temp PIN
        )

    sms_message += " Valid for 24 hours"  # OTP expiry message

    # WRITE BRIQ'S CODE HERE

    # Construct HTML email message
    email_subject = "SMARTCARD OTP KIOSK"
    email_body = f"""<html><body>Dear <b>{first_name} {surname}</b>,<br><p>Your ID Card is available at the kiosk.<br>
    Your SMARTCARD One-Time Password (OTP) is <b>{otp}</b></p>"""

    if temp_pin:
        email_body += f"<p>Your temporary PIN is: <b>{temp_pin}</b>. You will set a permanent PIN on collection.</p>"  # First-year instruction

    email_body += f"<p>Please go fetch your ID Card within 24 hours.</p></body></html>"  # Expiry reminder
    # Create MIME email message
    msg = MIMEText(email_body, "html")
    msg["Subject"] = email_subject
    msg["From"] = "smartcard.kiosk@gmail.com"
    msg["To"] = email

    # Send via SMTP (Gmail)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)  # Gmail SMTP server
        server.starttls()  # Upgrade connection to TLS
        # Use APP_PASSWORD (Gmail app-specific password) instead of account password
        app_password_clean = APP_PASSWORD.replace(
            " ", ""
        )  # Remove spaces from "xxxx xxxx xxxx xxxx" format
        server.login(SMTP_EMAIL, app_password_clean)
        server.sendmail(msg["From"], msg["To"], msg.as_string())  # Send email
        server.quit()
        email_sent = True
        email_error = None

    except Exception as e:
        email_sent = False
        email_error = f"Email failed: {str(e)}"

    conn.close()

    # Return delivery result (success if at least one channel succeeded)
    return {
        "success": sms_sent or email_sent,  # At least ONE channel must succeed
        "sms_sent": sms_sent,
        "email_sent": email_sent,
        "sms_error": sms_error,
        "email_error": email_error,
    }
