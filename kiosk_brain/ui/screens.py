"""
UI Screens Module — Kivy Screen Classes for Card Issuance Kiosk

This module defines all interactive screens displayed by the Kivy ScreenManager.
Each screen corresponds to a step in the student card collection workflow.

SCREEN CLASSES:
===============

WelcomeScreen (SCREEN_WELCOME)
  - Entry point for all transactions
  - Buttons: "Returning Student" or "First-Year Student"
  - No direct input processing; button presses handled by main app
  - Callback: Sets session context (student_type), transitions to OCR or manual entry

OTPEntryScreen (SCREEN_OTP_ENTRY)
  - Collects 6-digit OTP from student (sent via SMS + Email)
  - Input: Numeric keypad with DEL/ENTER functionality
  - Validation: Handled by main app (verify_otp in auth.py)
  - Failure handling: Increments failed_attempts counter, lockout after 3 failures
  - Success: Transitions to PINEntryScreen

PINEntryScreen (SCREEN_PIN_ENTRY)
  - Collects student's authentication PIN (4-6 digits)
  - Input: Numeric keypad with DEL/ENTER functionality (password field masked)
  - Validation: Checked against pin_hash in authentication table
  - Branch: If is_temp_pin=TRUE → PINSetupScreen; else → ConfirmationScreen
  - Failure: Increments failed_attempts, lockout after 3 failures

ConfirmationScreen (SCREEN_CONFIRMATION)
  - Summary before physical card dispensing
  - Display: Student name, registration number, "Card Dispensed Successfully"
  - Wait for: GPIO button press to trigger card dispenser relay
  - Callback: Dispenses physical card, records transaction, transitions to SuccessScreen

ErrorScreen (SCREEN_ERROR)
  - Generic error display for failed operations
  - Message: Dynamic error text (OTP expired, PIN incorrect, DB error, etc.)
  - Button: "Try Again" to return to WelcomeScreen
  - Timeout: Auto-dismisses after 10 seconds if no button press

RegEntryScreen (SCREEN_REG_ENTRY)
  - Manual registration number input (fallback when OCR fails or card scanning unavailable)
  - Format: Text input (accepts any characters for flexible search)
  - Validation: Looked up in students table via mock API
  - Success: Retrieves student record, transitions to OTPEntryScreen
  - Failure: Displays error, returns to WelcomeScreen

HELPER FUNCTIONS:
=================

create_number_keypad(cols=3, callback=None)
  - Factory function that creates a 3x4 numeric keypad GridLayout
  - Returns: GridLayout with buttons 1-9, DEL, 0, ENTER
  - Event binding: Button presses must be bound to on_keypad_press() method
  - Button actions:
    - Digits (1-9, 0): Append to input field
    - DEL: Remove last character from input field
    - ENTER: Trigger submit_button action (verifies with main app)
  - Used by: OTPEntryScreen, PINEntryScreen, and Future screens (PIN setup, staff PIN)

EVENT HANDLING:
===============
All keypad button presses are routed through on_keypad_press() method defined in screen class.
This allows each screen to handle input differently (e.g., masking in PIN field vs visible in OTP field).
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout
from ui.constants import *


def create_number_keypad(cols=3, callback=None):
    """
    Create a 3x4 numeric keypad GridLayout.

    Args:
        cols (int): Number of columns. Default: 3 (standard 3x4 layout)
        callback (callable): Optional callback for button presses (currently unused, handled by screen's on_keypad_press)

    Returns:
        GridLayout: Configured keypad with buttons 1-9, DEL, 0, ENTER

    Button Layout:
        [1] [2] [3]
        [4] [5] [6]
        [7] [8] [9]
        [DEL] [0] [ENTER]

    Note:
        Button event binding must be done by calling code:
        for button in keypad.children:
            button.bind(on_press=screen.on_keypad_press)
    """
    keypad = GridLayout(cols=cols, spacing=5, size_hint_y=0.4)

    for i in range(1, 10):
        keypad.add_widget(Button(text=str(i)))

    keypad.add_widget(Button(text="DEL"))
    keypad.add_widget(Button(text="0"))
    keypad.add_widget(Button(text="ENTER"))

    return keypad


class WelcomeScreen(Screen):
    """
    Welcome/Landing Screen — Kiosk entry point.

    Displays two options:
    - "Returning Student": Student who collected card in previous year
    - "First-Year Student": Student collecting card for first time

    Purpose:
        1. Greet students and establish session context
        2. Differentiate workflow: Returning students use existing PIN, first-years use temp PIN then setup
        3. Determine which credential delivery strategy to use

    Attributes:
        name (str): SCREEN_WELCOME - Used by ScreenManager to identify this screen
        ret_button (Button): "Returning Student" button
        first_button (Button): "First-Year Student" button

    Event Callbacks (handled by main.py):
        ret_button.on_press(): Set session.student_type = "returning", transition to OCR/card scan
        first_button.on_press(): Set session.student_type = "first_year", transition to OCR/card scan
    """

    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = SCREEN_WELCOME
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        self.add_widget(layout)
        title_label = Label(text="Welcome to Card Issuance Kiosk", size_hint_y=0.3)
        instruction_label = Label(
            text="Select your option below to get your ID card.", size_hint_y=0.3
        )

        choice = GridLayout(cols=2)
        self.ret_button = Button(text="Returning Student", size_hint_y=0.1)
        self.first_button = Button(text="First-Year Student", size_hint_y=0.2)

        layout.add_widget(title_label)
        layout.add_widget(instruction_label)
        choice.add_widget(self.ret_button)
        choice.add_widget(self.first_button)
        layout.add_widget(choice)


class OTPEntryScreen(Screen):
    """
    OTP Entry Screen — 6-digit one-time password verification.

    Purpose:
        Collect and verify one-time password sent to student's phone

    Attributes:
        name (str): SCREEN_OTP_ENTRY
        otp_input (TextInput): Displays entered OTP (shows all digits, no masking)
        submit_button (Button): Triggers OTP verification in main app

    Input Method:
        Numeric keypad (1-9, 0, DEL, ENTER) - no direct keyboard input allowed
        DEL: Remove last digit
        ENTER: Submit for verification

    Validation Flow (in main.py):
        1. Get OTP hash from authentication table for this reg number
        2. Verify entered OTP against stored hash using verify_otp()
        3. On success: Transition to PINEntryScreen
        4. On failure: Increment failed_attempts, show ErrorScreen, lockout after 3 attempts

    Event Handlers:
        on_keypad_press(): Routes keypad button events to appropriate action
    """

    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = SCREEN_OTP_ENTRY
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        self.add_widget(layout)

        otp_label = Label(text="Enter OTP sent to your phone", size_hint_y=0.3)
        otp_input = TextInput(
            text="", multiline=False, input_filter="int", size_hint_y=0.2
        )
        self.otp_input = otp_input
        self.submit_button = Button(text="Submit", size_hint_y=0.2)
        otp_keypad = create_number_keypad(cols=3)

        layout.add_widget(otp_label)
        layout.add_widget(otp_input)
        layout.add_widget(self.submit_button)
        layout.add_widget(otp_keypad)

        for button in otp_keypad.children:
            button.bind(on_press=self.on_keypad_press)

    def on_keypad_press(self, button):
        """
        Handle numeric keypad button presses.

        DEL: Remove last digit from otp_input
        Digits (0-9): Append to otp_input
        ENTER: Trigger submit_button (sends OTP to main app for verification)
        """
        if button.text == "DEL":
            if self.otp_input.text:
                self.otp_input.text = self.otp_input.text[:-1]

            else:
                self.otp_input.text = ""
        elif button.text.isdigit():
            self.otp_input.text += button.text
        elif button.text == "ENTER":
            self.submit_button.trigger_action()


class PINEntryScreen(Screen):
    """
    PIN Entry Screen — Student PIN authentication.

    Purpose:
        Collect and verify student authentication PIN (4-6 digits)

    Attributes:
        name (str): SCREEN_PIN_ENTRY
        pin_input (TextInput): Masked input field (displays * or dots instead of digits)
        submit_button (Button): Triggers PIN verification in main app

    Input Method:
        Numeric keypad (1-9, 0, DEL, ENTER) - no direct keyboard input allowed
        DEL: Remove last digit
        ENTER: Submit for verification

    PIN Type Logic:
        If is_temp_pin=TRUE (from authentication table):
            - This is a first-year student who just verified OTP
            - Temporary PIN was pre-generated by system
            - After verification, force PINSetupScreen for permanent PIN creation
        If is_temp_pin=FALSE:
            - Student is returning or has already set permanent PIN
            - Verify against existing pin_hash, proceed to ConfirmationScreen

    Validation Flow (in main.py):
        1. Get pin_hash and is_temp_pin from authentication table
        2. Verify entered PIN against pin_hash using verify_pin()
        3. On success:
           - If is_temp_pin=TRUE: Transition to PINSetupScreen
           - If is_temp_pin=FALSE: Transition to ConfirmationScreen
        4. On failure: Increment failed_attempts, show ErrorScreen, lockout after 3 attempts

    Event Handlers:
        on_keypad_press(): Routes keypad button events to appropriate action
    """

    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = SCREEN_PIN_ENTRY
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        self.add_widget(layout)

        pin_label = Label(text="Enter your 4-6 digit pin", size_hint_y=0.3)
        pin_input = TextInput(
            text="", multiline=False, input_filter="int", size_hint_y=0.2
        )
        self.pin_input = pin_input
        self.submit_button = Button(text="Submit", size_hint_y=0.2)
        pin_keypad = create_number_keypad(cols=3)

        layout.add_widget(pin_label)
        layout.add_widget(pin_input)
        layout.add_widget(self.submit_button)
        layout.add_widget(pin_keypad)

        for button in pin_keypad.children:
            button.bind(on_press=self.on_keypad_press)

    def on_keypad_press(self, button):
        """
        Handle numeric keypad button presses.

        DEL: Remove last digit from pin_input
        Digits (0-9): Append to pin_input
        ENTER: Trigger submit_button (sends PIN to main app for verification)
        """
        if button.text == "DEL":
            if self.pin_input.text:
                self.pin_input.text = self.pin_input.text[:-1]

            else:
                self.pin_input.text = ""
        elif button.text.isdigit():
            self.pin_input.text += button.text
        elif button.text == "ENTER":
            self.submit_button.trigger_action()


class ConfirmationScreen(Screen):
    """
    Confirmation Screen — Final verification before card dispensing.

    Purpose:
        Display student summary and wait for physical card dispensing

    Attributes:
        name (str): SCREEN_CONFIRMATION
        ok_button (Button): Acknowledge button (future use for completing transaction)

    Display Information:
        - Student name (from students table)
        - Registration number
        - "Card Dispensed Successfully" message
        - "Your ID Card will be dispensed shortly..."

    Hardware Trigger:
        When this screen displays, main.py should:
        1. Trigger GPIO pin connected to relay for card separator/dispenser mechanism
        2. Wait for card to physically dispense (timeout: 30 seconds)
        3. Record transaction in audit_log table
        4. Transition to SuccessScreen

    Event Callbacks (in main.py):
        ok_button.on_press(): Return to WelcomeScreen
    """

    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = SCREEN_CONFIRMATION
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        self.add_widget(layout)

        success_label = Label(text="Card Dispensed Successfully", size_hint_y=0.4)
        info_label = Label(
            text="Your ID Card will be dispensed shortly...", size_hint_y=0.3
        )
        self.ok_button = Button(text="OK", size_hint_y=0.2)

        layout.add_widget(success_label)
        layout.add_widget(info_label)
        layout.add_widget(self.ok_button)


class ErrorScreen(Screen):
    """
    Error Screen — Generic error handling display.

    Purpose:
        Display error messages for any failed operation and allow retry

    Attributes:
        name (str): SCREEN_ERROR
        retry_button (Button): "Try Again" to return to WelcomeScreen

    Error Types (examples):
        - "OTP incorrect" (entered OTP doesn't match hash)
        - "PIN incorrect" (entered PIN doesn't match hash)
        - "Account locked" (3 failed attempts on OTP or PIN)
        - "Student not found" (reg number not in students table)
        - "Database error" (sqlite3 connection/query error)
        - "API timeout" (mock API didn't respond in time)
        - "OCR failed" (couldn't read card image)

    Dynamic Messaging:
        Main app updates error_label.text with specific error message before transitioning to this screen

    Event Callbacks (in main.py):
        retry_button.on_press(): Return to WelcomeScreen to start over

    Auto-dismiss:
        Optional auto-transition after 10 seconds if no button press (helps with flow)
    """

    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = SCREEN_ERROR
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        self.add_widget(layout)

        error_label = Label(text="Authentication failed", size_hint_y=0.4)
        info_label = Label(text="Please try again or contact support", size_hint_y=0.3)
        self.retry_button = Button(text="Try Again", size_hint_y=0.2)

        layout.add_widget(error_label)
        layout.add_widget(info_label)
        layout.add_widget(self.retry_button)


class RegEntryScreen(Screen):
    """
    Registration Entry Screen — Manual registration number input.

    Purpose:
        Fallback when OCR (card scanning) fails or is not available
        Allow students to manually type their registration number

    Attributes:
        name (str): SCREEN_REG_ENTRY
        reg_input (TextInput): Text input field for registration number
        submit_button (Button): Triggers student lookup in main app

    Input Method:
        Free-form text input (accepts any characters for flexible searching)
        Example formats: "2022-04-09050", "202204090 50", "0209050", etc.

    Lookup Flow (in main.py):
        1. Get user input from reg_input.text
        2. Query mock API with registration number
        3. Mock API returns student record if found (name, email, year, etc.)
        4. On success: Store student record in session, transition to OTPEntryScreen
        5. On failure: Display error, allow retry or return to WelcomeScreen

    Database Query:
        Mock API endpoint: POST /api/student/lookup
        Payload: {"registration_number": "2022-04-09050"}
        Response: {"success": true, "student": {"name": "John Doe", "email": "....", ...}}

    Event Callbacks (in main.py):
        submit_button.on_press(): Trigger student lookup
    """

    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = SCREEN_REG_ENTRY
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        self.add_widget(layout)

        reg_label = Label(text="Enter your registration number", size_hint_y=0.3)
        self.reg_input = TextInput(text="", multiline=False, size_hint_y=0.2)
        self.submit_button = Button(text="Submit", size_hint_y=0.2)

        layout.add_widget(reg_label)
        layout.add_widget(self.reg_input)
        layout.add_widget(self.submit_button)
