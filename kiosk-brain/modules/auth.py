"""
Authentication Module — OTP, PIN, and Two-Factor Authentication

This module implements secure two-factor authentication for the kiosk:
- One-Time Password (OTP) generation, hashing, and verification
- PIN hashing and verification with support for temporary and permanent PINs
- Lockout enforcement and audit logging

Key Design Pattern: is_temp_pin Column
======================================
The `is_temp_pin` column in the `authentication` table distinguishes between:

1. TEMPORARY PINs (is_temp_pin = TRUE)
   - System-generated 4-digit codes for FIRST-YEAR STUDENTS
   - Sent via SMS during batch loading alongside their OTP
   - Verified on first collection, then forces PIN SETUP screen
   - After student sets permanent PIN: is_temp_pin set to FALSE

2. PERMANENT PINs (is_temp_pin = FALSE)
   - User-chosen PINs set on first collection (first-years)
   - Existing PINs for returning students from prior years
   - Verified without forcing PIN setup screen

Workflow Examples:
==================

FIRST-YEAR STUDENT (First Collection):
  1. Card loaded → OCR reads reg number
  2. Credentials sent via SMS + EMAIL with OTP + temp PIN (hashed in DB, is_temp_pin=TRUE)
  3. Student enters OTP → Success
  4. Student enters temp PIN → Success
  5. Check is_temp_pin=TRUE → Force PIN setup screen
  6. Student creates new permanent PIN twice (confirm match)
  7. DB update: pin_hash = hash(new_pin), is_temp_pin = FALSE
  8. Confirm screen → Card dispensed

RETURNING STUDENT (Has Prior Year PIN):
  1. Old card scanned → OCR reads reg number
  2. OTP sent via SMS + EMAIL (existing PIN in DB unchanged, is_temp_pin=FALSE)
  3. Student enters OTP → Success
  4. Student enters their existing PIN → Success
  5. Check is_temp_pin=FALSE → Skip PIN setup, proceed to confirm
  6. Confirm screen → Card dispensed

CREDENTIAL DELIVERY STRATEGY:
=============================
Credentials (OTP + optional temp PIN) are sent via TWO channels:
- SMS via Africa's Talking API (phone_number)
- Email via SMTP (email)

If one channel fails, the kiosk continues (does not crash batch).
Both channels are attempted independently.

Function Stubs (Implement in Phase 3):
=====================================
"""