"""
Kiosk Application Entry Point — Kivy UI Framework Integration

This is the main entry point for the Smart ID Card Distribution Kiosk. It initializes
the Kivy application, sets up the ScreenManager for UI navigation, and wires all UI
screen transitions to SessionManager state updates.

**Architecture Overview:**
==========================

SINGLE INSTANCE PATTERN:
- One KioskApp instance runs for the entire kiosk lifetime (until poweroff)
- One ScreenManager manages all 6 UI screens
- One SessionManager shared globally tracks student session state
- Timeout timer (Clock.schedule_interval) runs every 1 second

SCREEN MANAGER GRAPH:
    WELCOME → REG_ENTRY → OTP_ENTRY → PIN_ENTRY → CONFIRMATION → WELCOME
           ↑                                             ↓
           └─ ERROR (on lockout, network failure) ──────┘

SESSION LIFECYCLE:
    1. Student at kiosk (WELCOME screen, no session)
    2. Student enters reg number (REG_ENTRY screen, session initializes)
    3. Student enters OTP (OTP_ENTRY screen, session active)
    4. Student enters PIN (PIN_ENTRY screen, session active)
    5. Student collects card (CONFIRMATION screen, card dispensed)
    6. Session teardown (WELCOME screen, session reset)

TIMEOUT ENFORCEMENT:
    - Clock.schedule_interval() calls _check_timeout() every 1 second
    - Inactivity > 60 seconds triggers automatic session teardown + return to WELCOME
    - Prevents card hijacking if student walks away mid-session

**CRITICAL DEVELOPER PATTERN:**

SessionManager MUST be explicitly torn down before leaving a session:

    ✓ CORRECT:
        confirmation_screen.ok_button.bind(
            on_press=lambda x: (
                session_manager.teardown(),        # ← Mandatory cleanup
                setattr(sm, "current", SCREEN_WELCOME)
            )
        )

    ✗ WRONG:
        confirmation_screen.ok_button.bind(
            on_press=lambda x: setattr(sm, "current", SCREEN_WELCOME)
        )  # ← Ghost session!  Previous student's reg_number persists in memory

**Configuration:**
    - Display: 800x400 pixels (hardcoded via Kivy Config)
    - Window mode: Fullscreen on Raspberry Pi (/dev/fb0)
    - Orientation: Landscape (fixed)
"""

from kivy.config import Config
from ui.screens import *
from ui.constants import *
from modules.session_manager import SessionManager

# Configure Kivy display before App initialization
Config.set("graphics", "width", "800")
Config.set("graphics", "height", "400")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.clock import Clock

# Global session manager instance (shared across all screens)
session_manager = SessionManager()


class KioskApp(App):
    """
    Main Kivy application for the Smart ID Card Distribution Kiosk.

    Responsibilities:
        - Initialize Kivy ScreenManager with all 14 UI screens (9 student + 4 staff + error)
        - Wire screen transitions to SessionManager state updates
        - Schedule inactivity timeout checks every 1 second
        - Handle graceful shutdown (teardown, cleanup)

    Attributes:
        sm: Kivy ScreenManager instance (self.sm = sm in build())

    Lifecycle:
        - app.build() called on App().run() startup (creates screens + bindings)
        - app._check_timeout() called every 1 second via Clock.schedule_interval()
        - app.on_stop() called on window close or SIGTERM

    **Thread Safety:** All Kivy operations are single-threaded (main thread only)
    """

    def build(self):
        """
        Initialize UI screens and wire all transitions to SessionManager.

        Returns:
            sm (ScreenManager): Root widget for Kivy app (displays current screen)

        Side Effects:
            - Creates 14 screen instances (9 student: Idle/Welcome/RegEntry/OTP/PIN/PINSetup/Confirmation/Success/Locked + 4 staff: StaffPIN/PreScan/BatchProgress/BatchSummary + Error)
            - Adds all screens to ScreenManager
            - Binds all button callbacks to screen transitions
            - Schedules _check_timeout() on 1-second interval
            - Stores sm reference as self.sm (for timeout handler)

        **Screen Transition Graph Wiring:**
            STUDENT WORKFLOW:
            idle.collect_button → WELCOME (start session)
            idle.swipe_down → STAFF_PIN (staff access)
            welcome.ret_button → OTP_ENTRY (returning student flow)
            welcome.first_button → REG_ENTRY (first-year student flow)
            reg_entry.submit_button → OTP_ENTRY (reg number captured)
            otp_entry.submit_button → PIN_ENTRY (OTP verified)
            pin_entry.submit_button → CONFIRMATION (PIN verified)
            pin_setup.submit_button → CONFIRMATION (first-year PIN set)
            confirmation.ok_button → SUCCESS (card dispensed)
            success → IDLE (auto-return after 8 seconds)
            locked → IDLE (auto-return when countdown reaches 0:00)

            STAFF WORKFLOW:
            idle.swipe_down → STAFF_PIN (staff login via 6-digit PIN)
            staff_pin.submit_button → STAFF_CHECKLIST (pre-scan checks)
            staff_checklist.start_button → BATCH_PROGRESS (live scan feed)
            batch_progress.stop_button → BATCH_SUMMARY (final counts)
            batch_summary.logout_button → IDLE (return to student standby)

        **Timeout Handler Scheduling:**
            Clock.schedule_interval(lambda dt: self._check_timeout(), 1)
            - Calls _check_timeout() every 1000ms
            - Receives dt (delta time since last call) but unused
        """
        # Create ScreenManager to hold all 10 screens
        sm = ScreenManager()

        # Instantiate all screen objects
        welcome_screen = WelcomeScreen()
        otp_entry_screen = OTPEntryScreen()
        pin_entry_screen = PINEntryScreen()
        error_screen = ErrorScreen()
        confirmation_screen = ConfirmationScreen()
        reg_entry_screen = RegEntryScreen()
        pin_setup_screen = PINSetupScreen()
        locked_screen = LockedScreen()
        success_screen = SuccessScreen()
        idle_screen = IdleScreen()
        staff_pin_screen = StaffPINScreen()
        pre_scan_screen = PreScanChecklistScreen()
        batch_progress_screen = BatchProgressScreen()
        batch_summary_screen = BatchSummaryScreen()

        # Register all screens with name identifiers
        sm.add_widget(welcome_screen)
        sm.add_widget(otp_entry_screen)
        sm.add_widget(pin_entry_screen)
        sm.add_widget(error_screen)
        sm.add_widget(confirmation_screen)
        sm.add_widget(reg_entry_screen)
        sm.add_widget(pin_setup_screen)
        sm.add_widget(locked_screen)
        sm.add_widget(success_screen)
        sm.add_widget(idle_screen)
        sm.add_widget(staff_pin_screen)
        sm.add_widget(pre_scan_screen)
        sm.add_widget(batch_progress_screen)
        sm.add_widget(batch_summary_screen)

        # Wire idle screen button → welcome (start new session)
        idle_screen.collect_button.bind(
            on_press=lambda x: setattr(sm, "current", SCREEN_WELCOME)
        )

        # Wire welcome screen buttons → next screens
        welcome_screen.ret_button.bind(
            on_press=lambda x: (
                session_manager.update_activity(),  # Initialize session on button press
                setattr(
                    session_manager, "student_type", "returning"
                ),  # Returning student path
                setattr(sm, "current", SCREEN_OTP_ENTRY),
            )
        )
        welcome_screen.first_button.bind(
            on_press=lambda x: (
                session_manager.update_activity(),  # Initialize session on button press
                setattr(
                    session_manager, "student_type", "first_year"
                ),  # First-year student path
                setattr(sm, "current", SCREEN_REG_ENTRY),
            )
        )

        # Wire reg entry → OTP entry
        reg_entry_screen.submit_button.bind(
            on_press=lambda x: setattr(sm, "current", SCREEN_OTP_ENTRY)
        )

        # Wire OTP entry → PIN entry (update activity timestamp on transition)
        otp_entry_screen.submit_button.bind(
            on_press=lambda x: (
                session_manager.update_activity(),  # Reset inactivity timeout
                setattr(sm, "current", SCREEN_PIN_ENTRY),
            )
        )

        # Wire PIN entry → PIN setup (first-year) or Confirmation (returning)
        def on_pin_entry_submit(x):
            session_manager.update_activity()  # Reset inactivity timeout
            if session_manager.student_type == "first_year":
                setattr(
                    sm, "current", SCREEN_PIN_SETUP
                )  # First-year: setup permanent PIN
            else:
                setattr(sm, "current", SCREEN_CONFIRMATION)  # Returning: dispense card

        pin_entry_screen.submit_button.bind(on_press=on_pin_entry_submit)

        # Wire PIN setup (first-year) → Confirmation (first-time PIN set)
        pin_setup_screen.submit_button.bind(
            on_press=lambda x: (
                session_manager.update_activity(),  # Reset inactivity timeout
                setattr(sm, "current", SCREEN_CONFIRMATION),
            )
        )

        # Wire confirmation → success (card dispensed, ready for collection)
        confirmation_screen.ok_button.bind(
            on_press=lambda x: setattr(sm, "current", SCREEN_SUCCESS)
        )

        # Wire success → idle (auto-return after 8 seconds)
        # Schedule a callback 8000ms (8 seconds) after SuccessScreen appears
        def schedule_success_return():
            Clock.schedule_once(
                lambda dt: (
                    session_manager.teardown(),  # CRITICAL: cleanup before idle
                    setattr(sm, "current", SCREEN_IDLE),
                ),
                8,  # 8-second delay
            )

        # Bind to success screen's on_enter event
        success_screen.bind(on_enter=lambda screen: schedule_success_return())

        # Wire pre-scan checklist → batch progress (Start Scan button)
        pre_scan_screen.start_button.bind(
            on_press=lambda x: setattr(sm, "current", SCREEN_BATCH_PROGRESS)
        )

        # Wire batch progress → batch summary (Stop Scan button)
        batch_progress_screen.stop_button.bind(
            on_press=lambda x: setattr(sm, "current", SCREEN_BATCH_SUMMARY)
        )

        # Wire batch summary → idle (Logout button, return to student standby)
        batch_summary_screen.logout_button.bind(
            on_press=lambda x: setattr(sm, "current", SCREEN_IDLE)
        )

        # Store ScreenManager reference for timeout handler access
        self.sm = sm

        # Set initial screen to IDLE (kiosk ready for new session)
        sm.current = SCREEN_IDLE

        # Schedule inactivity timeout check every 1 second
        Clock.schedule_interval(lambda dt: self._check_timeout(), 1)

        return sm

    def _check_timeout(self):
        """
        Check for inactivity timeout and return to welcome screen if exceeded.

        Called by: Clock.schedule_interval() every 1 second

        Timeout Logic:
            - If last_activity_time > 60 seconds ago → timeout triggered
            - Call session_manager.teardown() to reset session state
            - Transition to SCREEN_WELCOME (return to idle)
            - Next student sees blank welcome screen (no lingering data)

        **Security Critical:**
            This function prevents card hijacking if student walks away mid-session.
            Failure to teardown() before returning to WELCOME allows ghost sessions.

        Side Effects:
            - Calls session_manager.is_timed_out() every 1 second
            - On timeout: calls session_manager.teardown() and sm.current = WELCOME
            - Otherwise: no side effects
        """
        # Check if inactivity exceeded timeout (60-second grace period)
        if session_manager.is_timed_out(timeout_seconds=60):
            # Inactivity timeout triggered
            session_manager.teardown()  # Reset all session state
            setattr(self.sm, "current", SCREEN_WELCOME)  # Return to idle screen


if __name__ == "__main__":
    # Application entry point - start Kivy main loop
    KioskApp().run()
