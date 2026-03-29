"""
Configuration Template for Kiosk Brain

IMPORTANT: Copy this file to config.py and fill in YOUR credentials.
NEVER commit config.py to git - it contains sensitive API keys and passwords.

    cp config.example.py config.py
    # Edit config.py with your actual credentials
    # Add config.py to .gitignore (already done)

"""

# =============================================================================
# Africa's Talking SMS Service
# =============================================================================
# Get credentials at: https://africastalking.com/
# For development, use the sandbox credentials provided in your account

AFRICA_TALKING_API_KEY = "atsk_YOUR_API_KEY_HERE"
# This is your unique API key - never share it publicly

AFRICA_TALKING_USERNAME = "sandbox"
# Use "sandbox" for development/testing
# Use your production username for production deployments


# =============================================================================
# Gmail SMTP for Email Delivery
# =============================================================================
# Email address that will send credentials (OTP, temp PIN) to students

SMTP_EMAIL = "smartcard.kiosk@gmail.com"
# Replace with your actual Gmail address

SMTP_PASSWORD = "xxxx xxxx xxxx xxxx"
# DEPRECATED: Use APP_PASSWORD instead for Gmail
# Keep for backwards compatibility only

APP_PASSWORD = "xxxx xxxx xxxx xxxx"
# Gmail App-Specific Password (16 characters with spaces)
# 
# IMPORTANT: This is NOT your Gmail password!
# Generation steps:
# 1. Enable 2-Step Verification on your Google Account
# 2. Go to https://myaccount.google.com/apppasswords
# 3. Select "Mail" and "Windows Computer" (or your device)
# 4. Google generates a 16-character password
# 5. Copy that password here (spaces included or removed - both work)
#
# Why app password instead of regular password?
# - Gmail doesn't allow regular passwords for SMTP with 2-Step enabled
# - App passwords are more secure and limited to specific services
# - Can be revoked independently from main account password
