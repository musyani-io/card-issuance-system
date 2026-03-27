import requests
import time

API_KEY = 'dev-api-key-12345'
BASE_URL = 'http://university-db.local:5000'

def get_student(reg_number):
    "Fetch student data from the mock university data"
    url = f"{BASE_URL}/students/{reg_number}"
    headers = {'X-API-Key': API_KEY}

    for attempt in range(3):
        wait_time = 2 ** attempt if attempt > 0 else 0
        try:
            response = requests.get(url, headers=headers, timeout=3)
        except requests.RequestException as e:
            if attempt == 2: 
                raise
            wait_time = 2 ** attempt
            time.sleep(wait_time)
            continue

        if response.status_code == 200:
            return {'success': True, 'data': response.json()}
        elif response.status_code == 404:
            return {'success': False, 'error': 'Student not found'}
        elif response.status_code == 401:
            return {'success': False, 'error': "Authentication failed - Invalid key"}
        else:
            return {'success': False, 'error': f'API error: {response.status_code}'}