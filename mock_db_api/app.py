"""
Mock University Database API Server

This Flask application simulates the UDSM student database backend for development and testing.
It provides a REST API endpoint for the Raspberry Pi kiosk to look up student records by registration number.

**PURPOSE:**
===========
Acts as a mock database server for the Smart ID Card Distribution Kiosk. The Raspberry Pi calls this
API during batch card loading and real-time transactions to fetch student information (name, programme,
phone, email, etc.) from the university database.

**DEPLOYMENT ARCHITECTURE:**
===========================

DEVELOPMENT:
  - Server runs on developer's computer (Linux/Mac/Windows)
  - Pi connects via local IP (e.g., 192.168.1.100:5000)
  - Connected via USB or ethernet

PRODUCTION:
  - Server runs on university network (separate server)
  - Pi connects via university LAN or mDNS discovery
  - Real MySQL/PostgreSQL database backend

**API ENDPOINTS:**
=================

GET /students/<reg_number>
  - Fetch student record by registration number
  - Headers: X-API-Key: test-key-12345 (required for authentication)
  - Response on success (200): JSON object with student fields
    {
        "student_id": 123,
        "registration_number": "T2MM24-001",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@udsm.ac.tz",
        "phone": "+255765123456",
        "programme": "Computer Science",
        "year": 1,
        "status": "active"
    }
  - Response on not found (404): {"error": "Student not found"}
  - Response on auth failure (401): {"error": "Unauthorized"}
  - Response on DB error (500): {"error": "database error message"}

**CONFIGURATION:**
=================
Database credentials from config.py:
  - DB_HOST: MySQL server hostname (default: localhost)
  - DB_USER: MySQL username (default: root)
  - DB_PASSWORD: MySQL password (loaded from env variable)
  - API_KEY: Authentication key (must match kiosk_brain/config.py)

Database schema expected: card_issuance database with students table

**SECURITY:**
=============
- API Key authentication via X-API-Key header (simple Bearer token)
- Production: Replace with OAuth 2.0 or JWT tokens
- Production: Use environment variables for all credentials
- Production: Enable HTTPS/SSL for network encryption

**DEVELOPMENT SETUP:**
=====================
1. Install dependencies: pip install -r requirements.txt
2. Configure MySQL credentials in config.py
3. Ensure MySQL server running: sudo systemctl start mysql
4. Create database: mysql -u root -p < schema.sql
5. Start Flask server: python3 app.py
6. Test endpoint: curl -H "X-API-Key: test-key-12345" http://localhost:5000/students/T2MM24-001

**ERROR HANDLING:**
==================
- Database connection errors: Returns 500 with error message
- Invalid registration number: Returns 404 (not found)
- Missing API key: Returns 401 (unauthorized)
- All responses in JSON format for easy parsing by Pi client
"""

from flask import Flask, jsonify, request
from mysql.connector import connect, Error
from config import DB_HOST, DB_PASSWORD, DB_USER
import subprocess

app = Flask(__name__)
API_KEY = "test-key-12345"


def get_db_connection():
    """
    Establish MySQL database connection using credentials from config.py.

    Returns:
        mysql.connector.MySQLConnection: Active database connection

    Raises:
        mysql.connector.Error: If connection fails
    """
    return connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database="card_issuance"
    )


def require_api_key(f):
    """
    Decorator function to enforce API key authentication on routes.

    Checks for X-API-Key header in request and validates against API_KEY constant.
    Returns 401 Unauthorized if key is missing or incorrect.

    Args:
        f: Flask route function to decorate

    Returns:
        Decorated function that enforces API key check
    """

    def decoreate_function(*args, **kwargs):
        if request.headers.get("X-API-Key") != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)

    return decoreate_function


@app.route("/students/<reg_number>", methods=["GET"])
@require_api_key
def get_student(reg_number):
    """
    Retrieve student record by registration number.

    This endpoint is called by the Raspberry Pi kiosk during:
    - Batch card loading (Phase 3: student info retrieval)
    - Real-time transaction lookup (Phase 4: student verification)

    Args:
        reg_number: Student registration number (e.g., 'T2MM24-001')

    Returns:
        tuple: (JSON response, HTTP status code)
            Success (200): Complete student record
            Not found (404): {"error": "Student not found"}
            Auth failure (401): {"error": "Unauthorized"}
            DB error (500): {"error": "database error message"}
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE reg_number = %s", (reg_number,))
        student = cursor.fetchone()
        cursor.close()
        conn.close()

        if student:
            return jsonify(student), 200
        return jsonify({"error": "Student not found"}), 404
    except Error as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("Starting Flask server on http://localhost:5000")
    print("API Key required: X-API-Key: test-key-12345")
    app.run(debug=True, host="0.0.0.0", port=5000)
