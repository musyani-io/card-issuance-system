# Mock University Database API

A lightweight Flask REST API simulating the university student database. Runs on a development laptop during prototyping and enables full-workflow integration testing without requiring access to the actual university server. The Pi discovers this service via mDNS as `university-db.local`.

## Purpose

The mock API serves three critical functions during development:

1. **API Contract Definition**: Establishes the expected request/response format that the real university server must provide in production
2. **Network Testing**: Enables Pi network testing over WiFi or mobile hotspot without production infrastructure
3. **Integration Testing**: Provides stable, fixture-based student data for regression testing the full workflow (batch loading, OCR, authentication)

## Architecture

### Technology Stack

- **Framework**: Flask 2.x (Python web microframework)
- **Transport**: HTTPS via `ssl` module (self-signed certificate for development)
- **Discovery**: mDNS via avahi-daemon (advertises `university-db.local:5000`)
- **Data**: JSON fixtures (30 representative student records, no database backend needed)
- **Authentication**: Bearer token (configurable API key expected in request headers)

### Single Endpoint

```bash
GET /students/{reg_number}
```

**Headers**:

```bash
Authorization: Bearer your-api-key-here
Content-Type: application/json
```

**Path Parameters**:

- `reg_number`: University registration number (e.g., `2001-02-99999`)

**Response (200 OK)**:

```json
{
	"reg_number": "2001-02-99999",
	"name": "John Doe",
	"programme": "Computer Science",
	"phone": "+255123456789",
	"status": "active"
}
```

**Status Codes**:

- `200 OK`: Student found and active/inactive/suspended
- `401 Unauthorized`: Missing or invalid bearer token
- `404 Not Found`: Registration number does not exist
- `500 Internal Server Error`: Server-side exception (logged to stderr)

## Installation

### Prerequisites

```bash
# Python 3.11 or later
python3 --version

# pip package manager
pip3 --version

# System tools for mDNS
sudo apt install avahi-daemon
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon
```

### Virtual Environment & Dependencies

```bash
cd mock-db-api
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**Installed Packages**:

- `Flask==3.x.x` — Web framework
- `requests==2.33.0` — HTTP client (for testing)
- All standard library modules only: `ssl`, `logging`, `json`, `datetime`

## Configuration

### `config.py`

```python
# config.py — Edit before first run

import os

# API Authentication
API_KEY = os.getenv("UNIVERSITY_API_KEY", "default-dev-key-change-in-production")

# HTTPS Settings
USE_SSL = True  # Enable HTTPS (self-signed cert)
SSL_CERT_PATH = "./certs/cert.pem"
SSL_KEY_PATH = "./certs/key.pem"

# Server Binding
HOST = "0.0.0.0"     # Listen on all interfaces (mDNS-discoverable)
PORT = 5000
DEBUG = False  # Never enable in production

# mDNS Configuration
MDNS_SERVICE_NAME = "university-db"
MDNS_DOMAIN = "local"

# Latitude/timeout (for Pi integration testing)
API_RESPONSE_DELAY = 0.0  # Add artificial latency (0.5 = 500ms)
FAILURE_RATE = 0.0       # Random failure percentage (0.1 = 10% failures)
```

### Environment Variables

```bash
# Override config.py defaults
export UNIVERSITY_API_KEY="prod-api-key-xyz"
export FLASK_ENV="production"

python app.py
```

## Running the API

### Local (No mDNS)

```bash
python app.py
```

Output:

```bash
 * Running on http://0.0.0.0:5000 (Press CTRL+C to quit)
```

**Access from Pi**:

```bash
# On Pi console
curl -H "Authorization: Bearer default-dev-key-change-in-production" \
     http://your-laptop-ip:5000/students/T/UDSM/0001/2021
```

### With mDNS Advertising

```bash
# Start avahi-daemon on laptop (if not running)
sudo systemctl start avahi-daemon

# Start Flask app
python app.py --mdns

# On Pi or other machine on same network:
curl -H "Authorization: Bearer default-dev-key-change-in-production" \
     http://university-db.local:5000/students/T/UDSM/0001/2021
```

### In Docker (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

```bash
docker build -t university-api .
docker run --network host -e UNIVERSITY_API_KEY=prod-key university-api
```

## API Client Usage (Pi Side)

### Within `kiosk_brain/modules/api_client.py`

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class UniversityAPIClient:
    def __init__(self, base_url: str = "http://university-db.local:5000",
                 api_key: str = "default-dev-key", timeout: float = 5.0):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

        # Enable retries with exponential backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # 1s, 2s, 4s delays
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get_student(self, reg_number: str) -> dict:
        """
        Fetch student data by registration number.

        Returns:
            {"reg_number": "...", "name": "...", "programme": "...",
             "phone": "...", "status": "active|inactive|suspended"}

        Raises:
            requests.Timeout: If exceeds 5-second timeout
            requests.ConnectionError: Network unavailable
            ValueError: API returned unexpected format
        """
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/students/{reg_number}"

        response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

# Usage in batch loading workflow:
api = UniversityAPIClient()
try:
    student = api.get_student("T/UDSM/0001/2021")
    print(f"Found: {student['name']} ({student['status']})")
except requests.Timeout:
    print("API timeout, queue for retry")
except requests.ConnectionError:
    print("Network unavailable")
except requests.HTTPError as e:
    if e.response.status_code == 404:
        print("Student not found")
    elif e.response.status_code == 401:
        print("Invalid API key")
```

## Sample Data (`fixtures`)

The API ships with 30 representative student records covering all scenarios:

```python
STUDENTS = {
    "T/UDSM/0001/2021": {
        "name": "Alice Mwangi",
        "programme": "Computer Science",
        "phone": "+255712345601",
        "status": "active"
    },
    "T/UDSM/0002/2021": {
        "name": "Bob Kipchoge",
        "programme": "Information Systems",
        "phone": "+255712345602",
        "status": "active"
    },
    # ... 28 more records
    "T/UDSM/0015/2021": {
        "name": "Student Inactive",
        "programme": "Business Studies",
        "phone": "+255712345615",
        "status": "inactive"  # Tests "hold" card status on Pi
    },
    "T/UDSM/0016/2021": {
        "name": "Student Suspended",
        "programme": "Engineering",
        "phone": "+255712345616",
        "status": "suspended"  # Tests administrative hold
    },
}
```

**Scenarios Covered**:

- ✅ Active students (immediate SMS dispatch)
- ✅ Inactive students (card held, no SMS)
- ✅ Suspended students (card held, no SMS)
- ✅ Mixed phone number formats
- ✅ First-year vs. returning students (simulated via registration year)

## HTTPS / SSL

### Self-Signed Certificate (Development Only)

Generate a self-signed certificate for testing:

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem \
    -out certs/cert.pem -days 365 -nodes \
    -subj "/CN=university-db.local"
```

### Pi Client Certificate Verification

By default, the Pi disables SSL verification during development (`verify=False`). For production:

```python
# Copy cert.pem to Pi
scp certs/cert.pem pi@raspberry.local:/etc/ssl/certs/university-db-ca.pem

# In api_client.py:
response = self.session.get(
    url,
    headers=headers,
    timeout=self.timeout,
    verify="/etc/ssl/certs/university-db-ca.pem"  # Enable verification
)
```

## Testing

### Unit Tests

```bash
cd mock-db-api
pytest tests/test_api.py -v
```

**Test Cases**:

- ✅ Valid student lookup (200 OK)
- ✅ Invalid registration number (404 Not Found)
- ✅ Missing API key (401 Unauthorized)
- ✅ All fixture students returnable
- ✅ Response JSON schema validation

### Integration Tests

```bash
# Terminal 1: Start the API
python app.py --mdns

# Terminal 2: Run integration tests
cd ../kiosk-brain
pytest tests/test_integration.py::test_batch_loading -v
```

**What It Tests**:

- Pi connects to mDNS-advertised service
- Pi sends HTTPS request with bearer token
- API returns student data in expected format
- Pi processes response and updates database

### Load Testing (Stress)

```bash
# Simulate 100 concurrent requests
ab -n 100 -c 10 -H "Authorization: Bearer default-dev-key-change-in-production" \
    http://localhost:5000/students/T/UDSM/0001/2021
```

## Production Considerations

### Before Deploying Real University API

**Requirements**:

1. Endpoint contract matches `/students/{reg_number}` format
2. Response schema includes `reg_number`, `name`, `programme`, `phone`, `status`
3. Status values are exactly: `active`, `inactive`, `suspended`
4. Bearer token authentication supported in Authorization header
5. Response time target: <5 seconds (timeout on Pi side)
6. Uptime: 99%+ (batch loading should not fail due to API)

**Configuration Changes**:

```python
# config.py → production
UNIVERSITY_API_KEY = os.getenv("UNIVERSITY_API_KEY")  # From secrets manager
USE_SSL = True
SSL_CERT_PATH = "/etc/ssl/certs/university-api.crt"
SSL_KEY_PATH = "/etc/ssl/private/university-api.key"
DEBUG = False
```

**On Pi**:

```python
# kiosk-brain/config.py → production
UNIVERSITY_BASE_URL = "https://api.university.ac.tz"  # Real server DNS
UNIVERSITY_API_TIMEOUT = 5.0
UNIVERSITY_API_RETRIES = 3
```

### Rollback Plan

If real university API is unreachable:

1. Pi retries 3 times (automatic exponential backoff)
2. Card queued in SQLite as `pending_lookup` status
3. Background thread retries every 2 minutes
4. Staff can manually approve collection after 15-minute window (with audit trail)

## Logging & Monitoring

### Application Logs

```bash
# Start with verbose logging
python app.py --debug
```

**Log Levels**: INFO (default), DEBUG (--debug flag)

### Monitoring Endpoints (Optional)

Add these for production deployment:

```python
@app.route("/health")
def health():
    """Kubernetes or Docker health check."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint (optional)."""
    return f"""
    # HELP api_requests_total Total API requests
    # TYPE api_requests_total counter
    api_requests_total{{endpoint="/students/{{id}}"}} {request_count}
    """
```

## Troubleshooting

| Issue                                   | Cause                   | Solution                                                                    |
| --------------------------------------- | ----------------------- | --------------------------------------------------------------------------- |
| **Pi cannot reach university-db.local** | mDNS not advertised     | Check avahi-daemon running on laptop                                        |
| **401 Unauthorized**                    | Invalid bearer token    | Verify API key in config.py matches Pi config.py                            |
| **504 Gateway Timeout**                 | API response > 5s       | Check network latency, add `API_RESPONSE_DELAY` in config.py for simulation |
| **SSL certificate error**               | Certificate not trusted | Use self-signed cert or disable verification (dev only)                     |
| **Port 5000 already in use**            | Another service bound   | Change PORT in config.py or `lsof -i :5000` to find process                 |

## Architecture Diagram

```bash
┌─────────────────────────┐
│   Development Laptop    │
│ (Mock University API)   │
│   ─ Flask app.py        │
│   ─ 30 student fixtures │
│   ─ mDNS advertiser     │
└────────────┬────────────┘
             │ HTTPS + mDNS
             │ localhost:5000
             │ university-db.local:5000
             │
    ┌────────▼─────────────────────────────┐
    │  WiFi / Shared Hotspot Network       │
    └────────┬─────────────────────────────┘
             │
    ┌────────▼────────────────────┐
    │    Raspberry Pi 5 (4GB)      │
    │    (Kiosk Brain)            │
    │ ─ Pi Camera (CSI)           │
    │ ─ Kivy UI                   │
    │ ─ OCR pipeline              │
    │ ─ api_client.py (consumer)  │
    └─────────────────────────────┘
```

## Future Enhancements

### Phase 2 (TBD)

- Load balancing (multiple API instances behind nginx)
- Database backend (PostgreSQL) instead of in-memory fixtures
- Caching layer (Redis) for frequently-accessed students
- GraphQL endpoint (in addition to REST)

### Phase 3 (Production)

- Real university authentication (OAuth2 / SAML)
- Audit logging (all API requests logged to permanent store)
- Rate limiting (prevent batch loading from hammering API)
- Geographic failover (backup API server)

## References

- **Flask Documentation**: <https://flask.palletsprojects.com/>
- **mDNS (Avahi)**: <https://en.wikipedia.org/wiki/Multicast_DNS>
- **Bearer Tokens (RFC 6750)**: <https://tools.ietf.org/html/rfc6750>
- **HTTP Status Codes**: <https://httpwg.org/specs/rfc7231.html#status.codes>
