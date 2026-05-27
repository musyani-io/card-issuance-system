"""
Configuration Template for Kiosk Brain

SETUP INSTRUCTIONS:
===================
1. Copy this file to config.py:
       cp config.example.py config.py

2. Edit config.py with YOUR actual credentials (NEVER commit sensitive data)

CREDENTIAL SOURCES:
===================
- BRIQ SMS Gateway: https://briq.tz (Tanzanian SMS provider)
- Gmail App Password: https://myaccount.google.com/apppasswords
"""

# ============================================================================
# SMS GATEWAY (BRIQ Solutions)
# ============================================================================

BRIQ_API_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Bearer token from BRIQ dashboard
BRIQ_SENDER_ID = "CARD KIOSK"  # Message sender identifier
BRIQ_BASE_URL = "https://karibu.briq.tz"  # SMS API endpoint

# ============================================================================
# EMAIL GATEWAY (Gmail SMTP)
# ============================================================================

SMTP_EMAIL = "smartcard.kiosk@gmail.com"  # Gmail account for sending credentials

APP_PASSWORD = "xxxx xxxx xxxx xxxx"  # Gmail 16-character app-specific password
# SETUP: Go to https://myaccount.google.com/apppasswords
# (Requires 2-Step Verification enabled)

# ============================================================================
# UNIVERSITY DATABASE API
# ============================================================================

UNIVERSITY_API_BASE_URL = "http://localhost:5000"  # Mock server (localhost for testing)
UNIVERSITY_API_KEY = "test-key-12345"  # Must match mock_db_api/config.py
