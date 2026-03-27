"""
Smart ID Card Distribution Kiosk - Mock University Database API

PURPOSE:
  Lightweight Flask REST API simulating university student database during development.
  Replaces real university server during prototyping, enabling full workflow testing
  on WiFi/mobile hotspot without production infrastructure access.

CURRENT STATE:
  - Single endpoint: GET /students/<reg_number>
  - In-memory student fixtures (3 test records from UDSM)
  - mDNS service discovery (resolves as university-db.local:5000)
  - X-API-Key authentication (dev key: dev-api-key-12345)
  - No persistent storage (fixtures only)

SERVER ACCESS:
  - From Pi: http://university-db.local:5000/ (via mDNS)
  - Local testing: http://localhost:5000/
  - Laptop access: http://<laptop-ip>:5000/

AUTHENTICATION:
  All endpoints require X-API-Key header with valid API key.
  Example:
    curl -H "X-API-Key: dev-api-key-12345" http://university-db.local:5000/students/<reg_number>

RESPONSE SCHEMA (from kiosk-brain/api_client.py):
  {
    "registration_number": "xxxx-xx-xxxxx",
    "first_name": "$xxxx",
    "surname": "#xxxx",
    "email": "$xxxx.#xxxx_YY@student.udsm.ac.tz",
    "programme": "xxxxxxxxx",
    "phone_number": "xxxxxxxx",
    "registration_status": "active" | "inactive" | "suspended",
    "year_of_study": x
  }

FUTURE ENHANCEMENTS:
  - Database backend (PostgreSQL) instead of in-memory fixtures
  - Load testing endpoint (/metrics)
  - Health check endpoint (/health)
  - Production SSL certificate (currently self-signed for dev)
  - Real university authentication (OAuth2/SAML)
"""

from flask import Flask, jsonify, request
from functools import wraps
from datetime import datetime
import os

# Initialize Flask app instance (listens on 0.0.0.0:5000 by default)
app = Flask(__name__)

# API key for development (hardcoded for simplicity; use env var in production)
API_KEY = "dev-api-key-12345"


def generate_student_email(first_name, surname, registration_number):
    """
    Generate university email from student credentials.
    Format: firstname.surname_YY@student.udsm.ac.tz (YY = last 2 digits of reg year)
    """
    year_suffix = registration_number[:4][-2:]  # Extract year from reg number
    first_name_l = first_name.lower()
    surname_l = surname.lower()
    return f"{first_name_l}.{surname_l}_{year_suffix}@student.udsm.ac.tz"


def require_api_key(f):
    """
    Decorator: Enforce X-API-Key authentication on protected endpoints.
    Returns 401 Unauthorized if key missing or invalid.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get(
            "X-API-Key"
        )  # Extract API key from request header

        # Validate API key (must be present and match API_KEY constant)
        if not api_key or api_key != API_KEY:
            return jsonify({"error": "Invalid key"}), 401

        return f(*args, **kwargs)  # Proceed to wrapped endpoint if valid

    return decorated_function


# In-memory student fixtures (keyed by registration_number)
# Format mirrors university database schema. Used for integration testing.
# In production: Replace with real database query via ORM (SQLAlchemy)
STUDENTS = {
    "2022-04-09050": {
        "registration_number": "2022-04-09050",  # Unique ID (primary key in real DB)
        "first_name": "Samuel",
        "surname": "Musyani",
        "email": generate_student_email("Samuel", "Musyani", "2022-04-09050"),
        "date_of_birth": "14/04/2004",
        "nationality": "Tanzanian",
        "programme": "BSc. Electronics Engineering",
        "faculty": "College of Information and Communication Technologies",
        "phone_number": "+255773422381",
        "registration_status": "active",  # 'active'|'inactive'|'suspended' affects card issuance
        "year_of_study": 4,
    },
    "2022-04-12357": {
        "registration_number": "2022-04-12357",
        "first_name": "Godson",
        "surname": "Shirima",
        "email": generate_student_email("Godson", "Shirima", "2022-04-12357"),
        "date_of_birth": "10/03/2002",
        "nationality": "Tanzanian",
        "programme": "BSc. Telecommunications Engineering",
        "faculty": "College of Information and Communication Technologies",
        "phone_number": "+255755981777",
        "registration_status": "active",
        "year_of_study": 4,
    },
    "2022-04-05392": {
        "registration_number": "2022-04-05392",
        "first_name": "Devotha",
        "surname": "Lyakurwa",
        "email": generate_student_email("Devotha", "Lyakurwa", "2022-04-05392"),
        "date_of_birth": "30/07/2002",
        "nationality": "Tanzanian",
        "programme": "BSc. Telecommunications Engineering",
        "faculty": "College of Information and Communication Technologies",
        "phone_number": "+255783632556",
        "registration_status": "active",
        "year_of_study": 4,
    },
}


@app.route("/students/<reg_number>", methods=["GET"])
@require_api_key  # Decorator chain: Check auth first, then execute endpoint
def get_student(reg_number):
    """
    GET /students/{reg_number} - Fetch student data by registration number.

    Args:
        reg_number: University registration number (e.g., 'xxxx-xx-xxxxx')

    Returns:
        200 OK + JSON: Student record if found
        401 Unauthorized: Missing or invalid X-API-Key header
        404 Not Found: Registration number not in STUDENTS fixture

    Called by:
        kiosk-brain/modules/api_client.py during batch loading (once per card)
        Mock consumer tests for integration testing
    """
    student = STUDENTS.get(reg_number)  # Lookup in fixture dict

    if student is None:
        # Card OCR'd registration number not found in student database
        return jsonify({"error": "Student not found"}), 404
    else:
        # Return complete student record for auth and SMS dispatch
        return jsonify(student), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
