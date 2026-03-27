from config import (
    AFRICA_TALKING_API_KEY,
    AFRICA_TALKING_USERNAME,
    SMTP_EMAIL,
    SMTP_PASSWORD,
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
        "SELECT surname, email, phone_number FROM students WHERE registration_number = ?",
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

    surname, email, phone_number = student
    sms_message = f"Your SMARTCARD One-Time Password (OTP) is {otp}."

    if temp_pin:
        sms_message += f" Temporary PIN: {temp_pin}."

    sms_message += " Valid for 24 hours"

    africastalking.initialize(AFRICA_TALKING_USERNAME, AFRICA_TALKING_API_KEY)
    sms = africastalking.SMS
    response = sms.send(sms_message, [phone_number])

    sms_sent = response["SMSMessageData"][0]["Status"] == "Success"
    sms_error = (
        None
        if sms_sent
        else f"SMS failed: {response['SMSMessageData'][0]['ErrorMessage']}"
    )

    email_subject = "SMARTCARD OTP KIOSK"
    email_body = f"""<html><body><h2>Hello {surname},</h2><p>Your SMARTCARD One-Time Password (OTP) is <b>{otp}</b></p>"""

    if temp_pin:
        email_body += f"<p>Your temporary PIN is: <b>{temp_pin}</b>. You will set a permanent PIN on collection.</p>"

    email_body += f"<p>Valid for 24 hours</p></body></html>"
    msg = MIMEText(email_body, "html")
    msg["Subject"] = email_subject
    msg["From"] = "smartcard.kiosk@gmail.com"
    msg["To"] = email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
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
