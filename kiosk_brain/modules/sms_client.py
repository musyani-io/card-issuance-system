from config import (
    AFRICA_TALKING_API_KEY,
    AFRICA_TALKING_USERNAME,
    SMTP_EMAIL,
    APP_PASSWORD,
)
from email.mime.text import MIMEText
import africastalking
import smtplib
import sqlite3


def send_credentials(reg_num, otp, temp_pin=None, db_path="data/kiosk.db"):
    """Send OTP + PIN (temp) via SMS + Email to student"""

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
    first_name = first_name.upper()
    surname = surname.upper()
    sms_message = f"""Dear {surname}, your card is available at the kiosk.
    Your SMARTCARD One-Time Password (OTP) is {otp}."""

    if temp_pin:
        sms_message += f" Temporary PIN: {temp_pin}."

    sms_message += " Valid for 24 hours"

    africastalking.initialize(AFRICA_TALKING_USERNAME, AFRICA_TALKING_API_KEY)
    sms = africastalking.SMS
    response = sms.send(sms_message, [phone_number])

    # Handle Africa's Talking SMS response
    sms_sent = False
    sms_error = None
    try:
        if "SMSMessageData" in response:
            sms_data = response["SMSMessageData"]
            # Recipients is a list of recipient objects
            if isinstance(sms_data, dict) and "Recipients" in sms_data:
                recipients = sms_data["Recipients"]
                if isinstance(recipients, list) and len(recipients) > 0:
                    # Check first recipient status (lowercase 'status', statusCode 101 = Success)
                    first_recipient = recipients[0]
                    sms_sent = (
                        first_recipient.get("status") == "Success"
                        or first_recipient.get("statusCode") == 101
                    )
                    if not sms_sent:
                        sms_error = (
                            f"SMS failed: {first_recipient.get('status', 'Unknown')}"
                        )
                else:
                    sms_error = f"SMS failed: No recipients in response"
            # Fallback for list format
            elif isinstance(sms_data, list) and len(sms_data) > 0:
                sms_sent = sms_data[0].get("Status") == "Success"
                if not sms_sent:
                    sms_error = f"SMS failed: {sms_data[0].get('ErrorMessage', 'Unknown error')}"
            else:
                sms_error = f"SMS failed: Unexpected response format"
        else:
            sms_error = f"SMS failed: No SMSMessageData in response"
    except Exception as e:
        sms_sent = False
        sms_error = f"SMS error: {str(e)}"

    email_subject = "SMARTCARD OTP KIOSK"
    email_body = f"""<html><body>Dear <b>{first_name} {surname}</b>,<br><p>Your ID Card is available at the kiosk.<br>
    Your SMARTCARD One-Time Password (OTP) is <b>{otp}</b></p>"""

    if temp_pin:
        email_body += f"<p>Your temporary PIN is: <b>{temp_pin}</b>. You will set a permanent PIN on collection.</p>"

    email_body += (
        f"<p>Please go fetch your ID Card within 24 hours.</b></p></body></html>"
    )
    msg = MIMEText(email_body, "html")
    msg["Subject"] = email_subject
    msg["From"] = "smartcard.kiosk@gmail.com"
    msg["To"] = email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        # Use APP_PASSWORD (Gmail app-specific password) instead of regular password
        app_password_clean = APP_PASSWORD.replace(
            " ", ""
        )  # Remove spaces from "xxxx xxxx xxxx xxxx" format
        server.login(SMTP_EMAIL, app_password_clean)
        server.sendmail(msg["From"], msg["To"], msg.as_string())
        server.quit()
        email_sent = True
        email_error = None

    except Exception as e:
        email_sent = False
        email_error = f"Email failed: {str(e)}"

    conn.close()

    return {
        "success": sms_sent or email_sent,
        "sms_sent": sms_sent,
        "email_sent": email_sent,
        "sms_error": sms_error,
        "email_error": email_error,
    }
