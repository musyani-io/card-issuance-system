"""
Modules Package — Core Business Logic

This package contains all core modules for the Smart ID Card Distribution Kiosk:

MODULES:
========

auth.py
  - Authentication logic: OTP generation, verification, PIN management
  - OTP hashing and verification with time-based expiry
  - PIN hashing (bcrypt) and temporary vs permanent PIN logic
  - Lockout enforcement after 3 failed attempts
  - Two-factor authentication workflow

sms_client.py
  - SMS delivery via BRIQ Solutions API (https://briq.tz)
  - Phone number formatting for BRIQ system
  - Graceful error handling with email fallback
  - Credential dispatch (OTP + temp PIN) to students

api_client.py
  - HTTP client for mock API requests (student lookup, card data)
  - UDSM mock API integration at http://localhost:5000
  - Student registration number lookup and validation
  - Batch card loading endpoints

session_manager.py
  - Session lifecycle management for kiosk transactions
  - Session state: student data, credentials, timestamps
  - Automatic session teardown after 5 minutes inactivity
  - CRITICAL: Must call teardown() to prevent stale locks

database.py
  - SQLite database abstraction layer (Phase 4)
  - Student queries, authentication data persistence
  - Audit logging for compliance and debugging

ocr.py
  - OCR (Optical Character Recognition) pipeline (Phase 1)
  - Three-stage processing: Image capture → Document detection → Text extraction
  - ID card scanning and registration number extraction

spi_master.py
  - Raspberry Pi SPI bus master control (Phase 5)
  - STM32 microcontroller communication
  - Card reader module and dispenser relay control
  - Command protocol with CRC error detection

PACKAGE STRUCTURE:
==================
modules/
  __init__.py (this file)
  auth.py
  sms_client.py
  api_client.py
  session_manager.py
  database.py (stub, Phase 4)
  ocr.py (stub, Phase 1)
  spi_master.py (stub, Phase 5)

IMPORT EXAMPLES:
================
from modules.auth import verify_otp, verify_pin, generate_otp
from modules.sms_client import send_credentials
from modules.session_manager import SessionManager
from modules.api_client import lookup_student
"""
