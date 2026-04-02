"""
UI Package — Kivy User Interface

This package contains all UI components and screen definitions for the kiosk interface.

MODULES:
========

constants.py
  - Screen identifiers for ScreenManager (SCREEN_*)
  - UI configuration constants (colors, layouts, sizes)
  - Screen names: welcome, otp_entry, pin_entry, pin_setup, confirmation, error, locked, idle, etc.

screens.py
  - Kivy Screen classes for all UI screens
  - WelcomeScreen: Entry point with student type selection
  - OTPEntryScreen: OTP verification (numeric keypad)
  - PINEntryScreen: PIN authentication (masked numeric keypad)
  - PINSetupScreen: First-time PIN creation (Phase 3.5)
  - ConfirmationScreen: Summary before card dispensing
  - ErrorScreen: Error messages and retry
  - RegEntryScreen: Manual registration number entry (fallback)
  - create_number_keypad(): Factory function for numeric keypads

styles.kv
  - Kivy layout and styling definitions (.kv files)
  - Colors, fonts, spacing, responsive layouts
  - Touch event declarations

assets/
  - Images, icons, logos for UI display
  - Background/splash screens

PACKAGE STRUCTURE:
==================
ui/
  __init__.py (this file)
  constants.py
  screens.py
  styles.kv
  assets/
    logo.png
    background.png
    (other images)

ARCHITECTURE:
==============
The UI follows the Kivy ScreenManager pattern:
  - Main app (main.py) creates ScreenManager
  - Screens added to ScreenManager with unique names (from constants.py)
  - main.py handles transitions between screens based on auth state
  - Each screen emits callbacks that main.py handles

EVENT FLOW:
===========
1. WelcomeScreen: User selects student type
2. RegEntryScreen (manual) or OCR (camera) → Get registration number
3. API lookup → Retrieve student record
4. Generate OTP + temp PIN
5. Send via SMS/Email
6. OTPEntryScreen: User enters OTP
7. PINEntryScreen: User enters PIN
8. Branch: If temp PIN → PINSetupScreen; else → ConfirmationScreen
9. ConfirmationScreen: Wait for dispenser trigger
10. SuccessScreen: "Card dispensed"
11. Return to WelcomeScreen

SCREEN MAPPINGS:
================
SCREEN_WELCOME = "welcome" (WelcomeScreen)
SCREEN_REG_ENTRY = "reg_entry" (RegEntryScreen)
SCREEN_OTP_ENTRY = "otp_entry" (OTPEntryScreen)
SCREEN_PIN_ENTRY = "pin_entry" (PINEntryScreen)
SCREEN_PIN_SETUP = "pin_setup" (PINSetupScreen - Phase 3.5)
SCREEN_CONFIRMATION = "confirmation" (ConfirmationScreen)
SCREEN_SUCCESS = "success" (SuccessScreen - Phase 3.3)
SCREEN_ERROR = "error" (ErrorScreen)
SCREEN_LOCKED = "locked" (LockedScreen - Phase 3.6)
SCREEN_IDLE = "idle" (IdleScreen - Future)

IMPORT EXAMPLES:
================
from ui.constants import SCREEN_WELCOME, SCREEN_OTP_ENTRY, SCREEN_PIN_ENTRY
from ui.screens import WelcomeScreen, OTPEntryScreen, PINEntryScreen, create_number_keypad
"""
