"""
Session Manager — Lifecycle and Timeout Enforcement

This module manages student collection session state across UI screens:
- Tracks current student registration number, session ID, and authentication progress
- Enforces 60-second inactivity timeout to return kiosk to idle state
- Provides atomic teardown() method to reset all session state safely

**CRITICAL PATTERN: Dual-State Session Lifecycle**
============================================

SessionManager uses a two-phase architecture:

1. **INITIALIZED STATE** (start_time set, last_activity_time not None)
   - Student has entered reg number (RegEntryScreen)
   - Can receive OTP/PIN input without timeout
   - Activity tracking enforces 60-second inactivity reset

2. **IDLE STATE** (start_time and last_activity_time both None)
   - Kiosk displays welcome/instructions
   - No session active (timeout check returns False)
   - Next screen transition initializes new session

**CRITICAL DEVELOPER PATTERN:**

Every screen transition that LEAVES a session must call session_manager.teardown() first:

    def on_timeout():
        session_manager.teardown()      # ← ALWAYS clear session before returning to IDLE
        sm.current = SCREEN_WELCOME

Failure to call teardown() creates a GHOST SESSION where:
- Previous student's reg_number lingers in memory
- Card collection could be credited to wrong student
- Authentication attempts can hijack prior session state

**Examples of CORRECT usage:**

    # Error screen → need to reset before retry
    error_screen.retry_button.bind(
        on_press=lambda x: (
            session_manager.teardown(),
            sm.current = SCREEN_WELCOME
        )
    )

    # Confirmation → card dispensed, session over
    confirmation_screen.ok_button.bind(
        on_press=lambda x: (
            session_manager.teardown(),    # ← Mandatory cleanup
            sm.current = SCREEN_WELCOME
        )
    )

**Timeout Logic:**

max_idle_allowed = 60 seconds from last_activity_time
Activity = any UI interaction (button press, text entry)
"""

import time


class SessionManager:
    """
    Manages student collection session state and inactivity timeout.

    Attributes:
        reg_number: Current student's registration number (None if no session)
        session_id: Unique session identifier for audit trail (UUID)
        auth_step: Current authentication step ('OTP', 'PIN', 'CONFIRM', etc.)
        auth_status: Result of last auth attempt ('SUCCESS', 'INVALID', 'LOCKED', etc.)
        start_time: Unix timestamp when session started (first screen transition)
        last_activity_time: Unix timestamp of last button press / text entry

    **WARNING:** This class is NOT thread-safe. Use only in Kivy main thread.
    """

    def __init__(self):
        """
        Initialize empty SessionManager with all state set to None.

        Kivy sets session_manager = SessionManager() once at App startup.
        State is reused across multiple student collections (teardown resets it).
        """
        self.reg_number = None
        self.session_id = None
        self.auth_step = None
        self.auth_status = None
        self.start_time = None
        self.last_activity_time = None

    def teardown(self):
        """
        Atomically reset all session state to None (transition to IDLE).

        **CRITICAL:** Must be called before returning to WELCOME screen:
        - After collection confirmation (card dispensed)
        - After timeout triggers (inactivity reset)
        - After collection cancellation (error screen recovery)
        - On lockout expiry (manual admin reset)

        Side Effects:
            - Zeroes all instance variables
            - Writes audit log entry (via caller, not this function)
            - Prepares SessionManager for next student

        Idempotent: Safe to call multiple times (already-None values remain None)
        """
        self.reg_number = None
        self.session_id = None
        self.auth_step = None
        self.auth_status = None
        self.start_time = None
        self.last_activity_time = None

    def update_activity(self):
        """
        Record a touch event (button press, text entry, etc.) and initialize timers if needed.

        Called by: Every interactive UI element (button.bind(on_press), TextInput callbacks)

        Usage:
            # OTP entry button press resets inactivity counter
            otp_submit_button.bind(
                on_press=lambda x: session_manager.update_activity()
            )

        Side Effects:
            - Sets last_activity_time = current Unix timestamp
            - On first call: also sets start_time (session initialization)
            - Subsequent calls: only update last_activity_time (reset timeout countdown)

        **If-Then Logic:**
            - IF start_time is None (first touch): initialize both start_time and last_activity_time
            - ELSE (subsequent touches): update only last_activity_time (reset 60-second countdown)
        """
        if self.start_time is None:
            # First touch: initialize session timers
            self.start_time = time.time()  # Mark session birth
            self.last_activity_time = time.time()  # Reset timeout countdown
        else:
            # Subsequent touch: only reset timeout countdown, keep session start time
            self.last_activity_time = time.time()

    def is_timed_out(self, timeout_seconds=60):
        """
        Check if session has exceeded inactivity timeout threshold.

        Args:
            timeout_seconds: Inactivity threshold in seconds (default: 60)
                            Kivy timer calls this every 1 second via Clock.schedule_interval()

        Returns:
            bool: True if last_activity_time > timeout_seconds ago, False otherwise
                  False also if last_activity_time is None (no session active)

        Usage:
            # main.py KioskApp._check_timeout() runs every 1 second
            Clock.schedule_interval(lambda dt: self._check_timeout(), 1)

            # Inside _check_timeout():
            if session_manager.is_timed_out(timeout_seconds=60):
                session_manager.teardown()      # Reset session state
                self.sm.current = SCREEN_WELCOME  # Return to idle screen

        **State Transitions Triggered by Timeout:**
            - OTP entry (90s idle) → teardown, return to welcome (let 90s expire, not 60s)
            - PIN entry (90s idle) → teardown, return to welcome
            - Confirmation (immediate) → no timeout (terminal state)

        Security Logic:
            - Prevents card hijacking if student walks away mid-session
            - 60-second grace period allows input delays, network latency
            - Longer timeout (90s) on collection flows to account for large batch operations
        """
        # If no session active, timeout check returns False (not timed out)
        if self.last_activity_time is None:
            return False

        # Calculate elapsed time since last activity
        elapsed_time = time.time() - self.last_activity_time
        # Return True if inactivity exceeds threshold
        return elapsed_time > timeout_seconds
