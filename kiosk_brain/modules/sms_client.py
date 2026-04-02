"""
SMS and Email Credential Delivery Client

This module sends OTP and temporary PIN credentials to students via two independent channels:
- BRIQ Solutions SMS gateway (primary, instant delivery)
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
- BRIQ_API_KEY: BRIQ Solutions API key
- BRIQ_BASE_URL: BRIQ Solutions API base URL
- BRIQ_SENDER_ID: BRIQ Solutions sender identifier
- SMTP_EMAIL: Gmail address with app-specific password enabled
- APP_PASSWORD: Gmail app-specific password (format: "xxxx xxxx xxxx xxxx")

Migration Path:
===============

Development:  Mock credentials, no actual SMS/email sending
Production:   Real BRIQ Solutions account, real Gmail credentials

No code changes needed—only config.py values change between environments.
"""

from config import (
    BRIQ_BASE_URL,
    BRIQ_API_KEY,
    BRIQ_SENDER_ID,
    SMTP_EMAIL,
    APP_PASSWORD,
)
from email.mime.text import MIMEText
import requests
import smtplib
import sqlite3


def format_phone_number(phone_number):
    """
    Format phone number for BRIQ API.

    BRIQ expects format: 255XXXXXXXXX (no + prefix)
    Handles both +255... and 255... formats.

    Args:
        phone_number: str (e.g., "+255123456789" or "255123456789")

    Returns:
        str: Formatted phone number (e.g., "255123456789")
    """
    if phone_number.startswith("+"):
        return phone_number[1:]  # Remove + prefix
    return phone_number


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
            - 'sms_sent': bool (True if BRIQ Solutions SMS delivered)
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
        - BRIQ Solutions API key and Gmail app password in config.py (not versioned)
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
    sms_message = f"""Dear {first_name} {surname}, your card is available at the kiosk.
    Your SMARTCARD One-Time Password (OTP) is {otp}."""

    if temp_pin:
        sms_message += (
            f" Temporary PIN: {temp_pin}."  # First-year students get temp PIN
        )

    sms_message += " Fetch it within 24 hours."  # OTP expiry message

    # Send SMS via BRIQ API
    sms_sent = False
    sms_error = None
    try:
        # Format phone number: remove + prefix if present (BRIQ expects 255... format)
        formatted_phone = format_phone_number(phone_number)

        url = BRIQ_BASE_URL + "/v1/message/send-instant"
        payload = {
            "content": sms_message,
            "recipients": [formatted_phone],
            "sender_id": BRIQ_SENDER_ID,
        }
        headers = {"X-API-Key": BRIQ_API_KEY, "Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers, timeout=5)
        response_data = response.json()

        # Check both HTTP status and response success field
        if response.status_code == 200 and response_data.get("success"):
            sms_sent = True
            sms_error = None
        else:
            sms_sent = False
            sms_error = response_data.get("message", f"HTTP {response.status_code}")

    except Exception as e:
        sms_sent = False
        sms_error = f"SMS failed: {str(e)}"

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
