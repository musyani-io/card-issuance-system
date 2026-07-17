# Mock University Database API

A lightweight Flask REST API simulating the university student database backend. Runs on a local computer during development and enables integration testing of the card-ingestion and OCR workflow.

---

## Purpose

The mock API serves three critical functions during development:
1. **API Contract Definition** — Establishes the expected request/response format that the real university server must provide in production.
2. **Network Testing** — Enables local network testing over WiFi or direct connection without accessing the production server.
3. **Integration Testing** — Provides real MySQL-backed lookup data for testing the kiosk's database insertion, SMS dispatch, and card placement.

---

## Tech Stack

- **Framework**: Flask 3.x (Python web microframework)
- **Transport**: HTTP (default on port `5000`, can be run behind an HTTPS proxy in production)
- **Database**: MySQL (local instance storing student lookup records)
- **Authentication**: Custom API-Key authentication via header

---

## API Endpoints

### Student Lookup

```http
GET /students/<reg_number>
```

#### Headers
- `X-API-Key`: `test-key-12345` (must match `UNIVERSITY_API_KEY` in `kiosk_brain/config.py`)

#### Example Request
```bash
curl -H "X-API-Key: test-key-12345" http://localhost:5000/students/2022-04-09050
```

#### Example Response (200 OK)
```json
{
  "first_name": "Alice",
  "last_name": "Mwangi",
  "email": "alice.mwangi@udsm.ac.tz",
  "phone": "+255712345601",
  "programme": "Computer Science",
  "reg_number": "2022-04-09050",
  "registration_number": "2022-04-09050",
  "registration_status": "active",
  "status": "active",
  "surname": "Mwangi",
  "phone_number": "+255712345601"
}
```

> [!NOTE]
> The API automatically normalizes column names (`reg_number`/`registration_number`, `last_name`/`surname`, `phone`/`phone_number`, `status`/`registration_status`) so that the kiosk_brain can process them reliably even if the database columns are structured differently.

#### Status Codes
- `200 OK`: Student found and data returned.
- `401 Unauthorized`: Missing or incorrect `X-API-Key` header.
- `404 Not Found`: Registration number does not exist.
- `500 Internal Server Error`: Database connection error or server exception.

---

## Installation & Setup

### 1. Prerequisites
Ensure you have Python 3.11+ and MySQL server running:
```bash
# Verify Python
python3 --version

# Verify MySQL service status
sudo systemctl status mysql
```

### 2. Virtual Environment & Dependencies
From the `mock_db_api` directory:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Database Provisioning
Run the database schema script to create the `card_issuance` database, the `students` table, and seed it with test records:
```bash
mysql -u root -p < schema.sql
```

### 4. Local Configuration
Create a local configuration file named `config.py` in the `mock_db_api` directory. **Do not commit this file to git.**

```python
# mock_db_api/config.py

API_KEY = "test-key-12345"

DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "your-local-mysql-password"
DB_NAME = "card_issuance"
```

---

## Running the API

Start the Flask development server:
```bash
python3 app.py
```

The service will output:
```text
Starting Flask server on http://localhost:5000
API Key required: X-API-Key: test-key-12345
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://<your-ip>:5000
```
You can now run card-ingestion lookups from the kiosk application.
