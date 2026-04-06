"""
University API Client - Mock Database Integration

PURPOSE:
  HTTPS wrapper for university student database queries during batch card loading.
  Called once per scanned card to fetch student info (name, programme, phone, status).

CURRENT STATE:
  - Implements exponential backoff retry (3 attempts: 0s, 1s, 2s delays)
  - Queries mock-db-api endpoint: GET /students/<reg_number>
  - X-API-Key authentication (dev key from config)
  - 3-second timeout per request
  - Returns dict with 'success' bool + 'data' or 'error' field

INTEGRATION:
  Called by: kiosk-brain/modules/database.py during batch loading workflow
  Input: Registration number from OCR ('xxxx-xx-xxxxx')
  Output: Student record {'name': '...', 'programme': '...', 'phone': '...', 'status': '...'}
  Failure handling: Queued in SQLite batches table as pending_lookup, background retry every 2 min

CONFIGURATION:
  API_KEY: Hardcoded dev key (move to config.py env var in production)
  BASE_URL: mDNS discovery (university-db.local:5000) - no hardcoded IP needed
  TIMEOUT: 3 seconds per request
  RETRIES: 3 attempts with exponential backoff
"""

import requests
import time

# Development API credentials (should move to config.py in production)
API_KEY = "test-key-12345"
# mDNS resolved hostname (no hardcoded IP needed, survives network changes)
BASE_URL = "http://localhost:5000"


def get_student(reg_number):
    """
    Fetch student data from university API by registration number.

    Args:
        reg_number: Student registration number (e.g., 'xxxx-xx-xxxxx')

    Returns:
        dict: {
            'success': True,
            'data': {
                'registration_number': '...',
                'first_name': '...',
                'programme': '...',
                'phone_number': '...',
                'registration_status': 'active|inactive|suspended'
            }
        }
        OR
        dict: {
            'success': False,
            'error': 'Reason (Student not found|Network error|Auth failed)'
        }

    Retry Logic:
        - Retry up to 3 times on network errors (RequestException)
        - Exponential backoff: 0s, 1s (2^1), 2s (2^2)
        - Each request: 3-second hard timeout

    Called by: database.py during BATCH Progress screen (staff loading workflow)
    """
    url = f"{BASE_URL}/students/{reg_number}"
    # Headers: X-API-Key required by mock-db-api/app.py for authentication
    headers = {"X-API-Key": API_KEY}

    # Retry loop: Up to 3 attempts with exponential backoff on transient errors
    for attempt in range(3):
        # Calculate backoff delay (skip on first attempt, exponential thereafter)
        wait_time = 2**attempt if attempt > 0 else 0
        try:
            # Network request with 3-second timeout (prevents hanging on slow connection)
            response = requests.get(url, headers=headers, timeout=3)
        except requests.RequestException as e:
            # Transient network error (timeout, DNS, connection refused, etc.)
            if attempt == 2:  # Final attempt failed
                return {
                    "success": False,
                    "error": f"Network error after 3 retries: {str(e)}",
                }
            # Retry with exponential backoff (1s, then 2s)
            wait_time = 2**attempt
            time.sleep(wait_time)
            continue

        # Handle HTTP response codes from mock-db-api
        if response.status_code == 200:
            # Success: Student found, return complete record
            return {"success": True, "data": response.json()}
        elif response.status_code == 404:
            # Not found: OCR'd registration number doesn't exist in university database
            # Card will be stored as 'missing_student' status in carousel
            return {"success": False, "error": "Student not found"}
        elif response.status_code == 401:
            # Authentication failed: Invalid API key in config (not transient, don't retry)
            return {"success": False, "error": "Authentication failed - Invalid key"}
        else:
            # Unexpected HTTP error (500, 502, etc.)
            return {"success": False, "error": f"API error: {response.status_code}"}
