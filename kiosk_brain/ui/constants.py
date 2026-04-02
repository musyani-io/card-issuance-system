"""
UI Constants Module — Screen Names and Configuration

This module defines constants for all screen identifiers used by the Kivy ScreenManager.
Each constant maps to a corresponding screen class in screens.py.

STUDENT WORKFLOW SCREENS:
=========================
SCREEN_WELCOME (welcome)
  - Entry point for all transactions
  - Prompts: "Scan your card or enter registration number"
  - Next: SCREEN_REG_ENTRY or OCR processing

SCREEN_REG_ENTRY (reg_entry)
  - Manual registration number input fallback
  - Displays 3x4 numeric keypad for manual entry
  - Next: Card lookup in student database (mock API)

SCREEN_OTP_ENTRY (otp_entry)
  - 6-digit OTP code entry (sent via SMS + Email)
  - Displays 3x4 numeric keypad
  - Validation: Must match hash in authentication table
  - Next: SCREEN_PIN_ENTRY on success, SCREEN_LOCKED on 3 failures

SCREEN_PIN_ENTRY (pin_entry)
  - Student PIN entry for authentication
  - Displays 3x4 numeric keypad (PIN field masked)
  - Validation: Compares against pin_hash in authentication table
  - Next: SCREEN_PIN_SETUP if is_temp_pin=TRUE, SCREEN_CONFIRMATION if is_temp_pin=FALSE

SCREEN_PIN_SETUP (pin_setup)
  - First-time PIN setup for new students (after temp PIN verification)
  - Two-step entry: "Enter new PIN" then "Confirm new PIN"
  - Validation: Both entries must match before storing
  - Updates: pin_hash = hash(new_pin), is_temp_pin = FALSE in DB
  - Next: SCREEN_CONFIRMATION on success

SCREEN_CONFIRMATION (confirmation)
  - Summary screen before card dispensing
  - Displays: Student name, registration number, timestamp
  - Action: Wait for physical button press to dispense card
  - Triggers: GPIO relay to dispense physical card
  - Next: SCREEN_SUCCESS

SCREEN_SUCCESS (success)
  - Confirmation after card dispensed
  - Displays: "Card dispensed successfully"
  - Auto-timeout: Returns to SCREEN_WELCOME after 3 seconds

SCREEN_ERROR (error)
  - Error message display for any failed operation
  - Errors: Invalid OTP, Invalid PIN, Database errors, API timeouts, etc.
  - Displays: Error code and brief description
  - Action: "Try again" button or auto-return to SCREEN_WELCOME

SCREEN_LOCKED (locked)
  - Account lockout screen (3 failed PIN or OTP attempts)
  - Displays: "Your account is temporarily locked"
  - Duration: 15-minute lockout period
  - Next: Return to SCREEN_WELCOME after timeout or manual reset by staff

STAFF ADMINISTRATION SCREENS:
=============================
SCREEN_STAFF_PIN (staff_pin)
  - Authentication for staff operations
  - Displays 3x4 numeric keypad for PIN entry
  - Validation: Compares against staff PIN in DB (separate from student PINs)
  - Next: SCREEN_STAFF_CHECKLIST on success

SCREEN_STAFF_CHECKLIST (staff_checklist)
  - Staff menu for batch loading operations
  - Options: Load cards, View batch status, Download logs, Exit
  - Next: SCREEN_BATCH_PROGRESS (if load cards selected)

SCREEN_BATCH_PROGRESS (batch_progress)
  - Live progress during batch loading from mock API
  - Displays: Cards loaded, Cards remaining, Current card status
  - Shows: One card at a time being processed
  - Updates: Real-time as students collect cards

SCREEN_BATCH_SUMMARY (batch_summary)
  - Summary after batch loading completes
  - Displays: Total cards loaded, Success count, Failure count
  - Export option: Download logs and error report
  - Next: Return to SCREEN_STAFF_CHECKLIST or exit

SCREEN_IDLE (idle)
  - Timeout screen when no activity for configured duration (default 5 min)
  - Displays: "Kiosk returning to idle state..." with countdown
  - Next: SCREEN_WELCOME after timeout
"""

# Screens
SCREEN_PIN_ENTRY = "pin_entry"
SCREEN_OTP_ENTRY = "otp_entry"
SCREEN_CONFIRMATION = "confirmation"
SCREEN_WELCOME = "welcome"
SCREEN_ERROR = "error"
SCREEN_IDLE = "idle"
SCREEN_SUCCESS = "success"
SCREEN_STAFF_PIN = "staff_pin"
SCREEN_STAFF_CHECKLIST = "staff_checklist"
SCREEN_BATCH_SUMMARY = "batch_summary"
SCREEN_BATCH_PROGRESS = "batch_progress"
SCREEN_PIN_SETUP = "pin_setup"
SCREEN_LOCKED = "locked"
SCREEN_REG_ENTRY = "reg_entry"
