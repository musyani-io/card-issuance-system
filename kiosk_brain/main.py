"""
Kiosk application entry point.
"""

from threading import Thread

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.uix.screenmanager import ScreenManager

from modules.auth import enforce_pin_setup, set_pin, verify_otp, verify_pin
from modules.database import (
    get_card_record_by_registration,
    get_student_from_db,
    mark_card_collected,
)
from modules.session_manager import SessionManager
from ui.constants import (
    CONFIRMATION_SCREEN_SECONDS,
    LOCKOUT_SCREEN_SECONDS,
    LOOKUP_MAX_TRIES,
    OTP_LENGTH,
    OTP_MAX_TRIES,
    PIN_LENGTH,
    PIN_MAX_TRIES,
    SCREEN_CONFIRMATION,
    SCREEN_ERROR,
    SCREEN_IDLE,
    SCREEN_LOCKED,
    SCREEN_OTP_ENTRY,
    SCREEN_PIN_ENTRY,
    SCREEN_PIN_SETUP,
    SCREEN_REG_ENTRY,
    SCREEN_WAIT,
    SESSION_TIMEOUT_SECONDS,
)
from ui.screens import (
    ConfirmationScreen,
    ErrorScreen,
    IdleScreen,
    LockedScreen,
    OTPEntryScreen,
    PINEntryScreen,
    PINSetupScreen,
    RegEntryScreen,
    WaitScreen,
)

Config.set("graphics", "width", "800")
Config.set("graphics", "height", "400")


session_manager = SessionManager()


class KioskApp(App):
    def build(self):
        self.sm = ScreenManager()
        self.session_timeout_seconds = SESSION_TIMEOUT_SECONDS
        self.confirmation_timeout_seconds = CONFIRMATION_SCREEN_SECONDS
        self.lockout_screen_seconds = LOCKOUT_SCREEN_SECONDS
        self.flow_token = 0
        self.pin_mode = "permanent"
        self.reg_attempts = 0
        self.otp_attempts = 0
        self.pin_attempts = 0
        self.dispense_in_progress = False
        self.hardware_enabled = False
        self.confirmation_event = None
        self.lockout_event = None

        self.idle_screen = IdleScreen()
        self.reg_entry_screen = RegEntryScreen()
        self.otp_entry_screen = OTPEntryScreen()
        self.pin_entry_screen = PINEntryScreen()
        self.pin_setup_screen = PINSetupScreen()
        self.wait_screen = WaitScreen()
        self.confirmation_screen = ConfirmationScreen()
        self.error_screen = ErrorScreen()
        self.locked_screen = LockedScreen()

        for screen in (
            self.idle_screen,
            self.reg_entry_screen,
            self.otp_entry_screen,
            self.pin_entry_screen,
            self.pin_setup_screen,
            self.wait_screen,
            self.confirmation_screen,
            self.error_screen,
            self.locked_screen,
        ):
            self.sm.add_widget(screen)

        self.idle_screen.collect_button.bind(on_press=self.start_collection)
        self.reg_entry_screen.submit_button.bind(on_press=self.handle_reg_submit)
        self.otp_entry_screen.submit_button.bind(on_press=self.handle_otp_submit)
        self.pin_entry_screen.submit_button.bind(on_press=self.handle_pin_submit)
        self.pin_setup_screen.submit_button.bind(on_press=self.handle_pin_setup_submit)
        self.confirmation_screen.finish_button.bind(on_press=self.finish_collection)
        self.error_screen.retry_button.bind(on_press=self.retry_from_error)

        self.reg_entry_screen.reg_input.bind(text=lambda *_: self.note_activity())
        self.otp_entry_screen.otp_input.bind(text=lambda *_: self.note_activity())
        self.pin_entry_screen.pin_input.bind(text=lambda *_: self.note_activity())
        self.pin_setup_screen.pin_input.bind(text=lambda *_: self.note_activity())
        self.pin_setup_screen.confirm_input.bind(text=lambda *_: self.note_activity())

        self.wait_screen.bind(on_enter=lambda *_: self.begin_dispense())
        self.confirmation_screen.bind(on_enter=lambda *_: self.schedule_confirmation_timeout())
        self.locked_screen.bind(on_enter=lambda *_: self.schedule_locked_return())

        self.sm.current = SCREEN_IDLE
        Clock.schedule_interval(self._check_timeout, 1)
        return self.sm

    def note_activity(self):
        session_manager.update_activity()

    def _reset_flow_state(self):
        self.reg_attempts = 0
        self.otp_attempts = 0
        self.pin_attempts = 0
        self.pin_mode = "permanent"
        self.dispense_in_progress = False
        self._cancel_events()
        self._clear_inputs()

    def _clear_inputs(self):
        self.reg_entry_screen.clear_inputs()
        self.otp_entry_screen.clear_inputs()
        self.pin_entry_screen.clear_inputs()
        self.pin_setup_screen.clear_inputs()

    def _secure_dispenser(self):
        return None

    def _cancel_events(self):
        if self.confirmation_event is not None:
            self.confirmation_event.cancel()
            self.confirmation_event = None
        if self.lockout_event is not None:
            self.lockout_event.cancel()
            self.lockout_event = None

    def _schedule_idle_return(self, delay_seconds, token):
        def _return_if_current(_dt):
            if token == self.flow_token:
                self._go_idle()

        Clock.schedule_once(_return_if_current, delay_seconds)

    def _run_async(self, task_fn, callback_fn):
        def worker():
            try:
                result = task_fn()
            except Exception as exc:
                result = {"success": False, "error": str(exc)}
            Clock.schedule_once(lambda dt, value=result: callback_fn(value), 0)

        Thread(target=worker, daemon=True).start()

    def _set_error(self, message, retry_screen=SCREEN_IDLE, detail=None):
        self.error_screen.set_error(message, retry_screen=retry_screen)
        self.error_screen.info_label.text = (
            detail if detail is not None else "Tap Try Again to return to the previous step."
        )
        self.sm.current = SCREEN_ERROR

    def _set_locked(self, message, detail=None):
        self.locked_screen.set_message(message, detail)
        self.sm.current = SCREEN_LOCKED

    def _go_idle(self):
        self._cancel_events()
        self.dispense_in_progress = False
        self._secure_dispenser()
        session_manager.teardown()
        self._reset_flow_state()
        self.sm.current = SCREEN_IDLE

    def _terminate_active_flow(self):
        self.dispense_in_progress = False
        self._secure_dispenser()
        session_manager.teardown()
        self._clear_inputs()
        self.reg_attempts = 0
        self.otp_attempts = 0
        self.pin_attempts = 0
        self.pin_mode = "permanent"

    def start_collection(self, *_):
        self._go_idle()
        self.flow_token += 1
        self.note_activity()
        self.sm.current = SCREEN_REG_ENTRY

    def handle_reg_submit(self, *_):
        reg_number = self.reg_entry_screen.reg_input.text.strip()
        if not reg_number:
            self.reg_attempts += 1
            if self.reg_attempts >= LOOKUP_MAX_TRIES:
                self._terminate_active_flow()
                self._set_locked(
                    "Registration number not found.",
                    "Too many failed registration lookups. Returning to idle.",
                )
                return
            self._set_error(
                f"Registration number is required. Attempt {self.reg_attempts} of {LOOKUP_MAX_TRIES}.",
                retry_screen=SCREEN_REG_ENTRY,
            )
            return

        if len(reg_number) != 13:
            self.reg_attempts += 1
            if self.reg_attempts >= LOOKUP_MAX_TRIES:
                self._terminate_active_flow()
                self._set_locked(
                    "Registration number not found.",
                    "Too many failed registration lookups. Returning to idle.",
                )
                return
            self._set_error(
                f"Registration number must be 13 characters. Attempt {self.reg_attempts} of {LOOKUP_MAX_TRIES}.",
                retry_screen=SCREEN_REG_ENTRY,
            )
            return

        card_result = get_card_record_by_registration(reg_number)
        if card_result.get("success"):
            card_data = card_result.get("data", {})
            if card_data.get("card_status") == "collected":
                token = self.flow_token
                self._terminate_active_flow()
                self._set_error(
                    "Card already collected.",
                    retry_screen=SCREEN_IDLE,
                    detail="This card has already been collected. Returning to idle shortly.",
                )
                self._schedule_idle_return(10, token)
                return

        token = self.flow_token
        self.note_activity()

        def task():
            return get_student_from_db(reg_number)

        def callback(result):
            if token != self.flow_token:
                return
            if result.get("success"):
                student = result.get("data", {})
                session_manager.reg_number = reg_number
                session_manager.student_name = f"{student.get('first_name', '')} {student.get('surname', '')}".strip()
                self.reg_attempts = 0
                self.reg_entry_screen.clear_inputs()
                self.note_activity()
                self.sm.current = SCREEN_OTP_ENTRY
            else:
                self.reg_attempts += 1
                if self.reg_attempts >= LOOKUP_MAX_TRIES:
                    self._terminate_active_flow()
                    self._set_locked(
                        "Registration number not found.",
                        "Too many failed registration lookups. Returning to idle.",
                    )
                    return
                self._set_error(
                    f"Student not found. Attempt {self.reg_attempts} of {LOOKUP_MAX_TRIES}.",
                    retry_screen=SCREEN_REG_ENTRY,
                )

        self._run_async(task, callback)

    def handle_otp_submit(self, *_):
        otp = self.otp_entry_screen.otp_input.text.strip()
        if len(otp) != OTP_LENGTH:
            self._set_error(
                f"OTP must be exactly {OTP_LENGTH} digits.",
                retry_screen=SCREEN_OTP_ENTRY,
            )
            return

        token = self.flow_token
        self.note_activity()

        def task():
            otp_result = verify_otp(session_manager.reg_number, otp)
            if not otp_result.get("success"):
                return {"success": False, "phase": "otp", "result": otp_result}
            pin_result = enforce_pin_setup(session_manager.reg_number)
            if not pin_result.get("success"):
                return {"success": False, "phase": "pin_check", "result": pin_result}
            return {"success": True, "requires_pin_setup": bool(pin_result.get("requires_pin_setup"))}

        def callback(result):
            if token != self.flow_token:
                return
            if result.get("success"):
                requires_pin_setup = result.get("requires_pin_setup", False)
                session_manager.student_type = "first_year" if requires_pin_setup else "returning"
                self.otp_attempts = 0
                self.otp_entry_screen.clear_inputs()
                self.note_activity()
                if requires_pin_setup:
                    self.pin_mode = "temp"
                    self.pin_entry_screen.configure_mode("temp")
                    self.pin_entry_screen.clear_inputs()
                    self.sm.current = SCREEN_PIN_ENTRY
                else:
                    self.pin_mode = "permanent"
                    self._load_slot_and_wait()
                return

            otp_result = result.get("result", {})
            if result.get("phase") == "pin_check":
                self._set_error(
                    otp_result.get("message", "Unable to determine PIN status."),
                    retry_screen=SCREEN_OTP_ENTRY,
                )
                return
            message = otp_result.get("message", "OTP verification failed")
            error_code = otp_result.get("error")
            if error_code == "LOCKED":
                self._terminate_active_flow()
                self._set_locked(
                    "OTP verification locked.",
                    "Too many failed OTP attempts. Please wait and try again later.",
                )
                return
            self.otp_attempts += 1
            self._set_error(
                f"{message} Attempt {self.otp_attempts} of {OTP_MAX_TRIES}.",
                retry_screen=SCREEN_OTP_ENTRY,
            )

        self._run_async(task, callback)

    def handle_pin_submit(self, *_):
        pin = self.pin_entry_screen.pin_input.text.strip()
        if len(pin) != PIN_LENGTH:
            self._set_error(
                f"PIN must be exactly {PIN_LENGTH} digits.",
                retry_screen=SCREEN_PIN_ENTRY,
            )
            return

        token = self.flow_token
        self.note_activity()

        def task():
            return verify_pin(session_manager.reg_number, pin)

        def callback(result):
            if token != self.flow_token:
                return
            if result.get("success"):
                self.pin_attempts = 0
                self.pin_entry_screen.clear_inputs()
                self.note_activity()
                if self.pin_mode == "temp":
                    self.sm.current = SCREEN_PIN_SETUP
                else:
                    self._load_slot_and_wait()
                return

            error_code = result.get("error")
            message = result.get("message", "PIN verification failed")
            if error_code == "LOCKED":
                self._terminate_active_flow()
                self._set_locked(
                    "PIN verification locked.",
                    "Too many failed PIN attempts. Please wait and try again later.",
                )
                return
            self.pin_attempts += 1
            self._set_error(
                f"{message} Attempt {self.pin_attempts} of {PIN_MAX_TRIES}.",
                retry_screen=SCREEN_PIN_ENTRY,
            )

        self._run_async(task, callback)

    def handle_pin_setup_submit(self, *_):
        first_pin = self.pin_setup_screen.pin_input.text.strip()
        confirm_pin = self.pin_setup_screen.confirm_input.text.strip()

        if len(first_pin) != PIN_LENGTH or len(confirm_pin) != PIN_LENGTH:
            self._set_error(
                f"PIN setup requires exactly {PIN_LENGTH} digits in both fields.",
                retry_screen=SCREEN_PIN_SETUP,
            )
            return

        if first_pin != confirm_pin:
            self._set_error(
                "PINs do not match.",
                retry_screen=SCREEN_PIN_SETUP,
            )
            return

        token = self.flow_token
        self.note_activity()

        def task():
            return set_pin(session_manager.reg_number, first_pin)

        def callback(result):
            if token != self.flow_token:
                return
            if result.get("success"):
                self.pin_setup_screen.clear_inputs()
                self.note_activity()
                self._load_slot_and_wait()
            else:
                self._set_error(
                    result.get("message", "Could not set PIN."),
                    retry_screen=SCREEN_PIN_SETUP,
                )

        self._run_async(task, callback)

    def _load_slot_and_wait(self):
        token = self.flow_token

        def task():
            card_result = get_card_record_by_registration(session_manager.reg_number)
            if not card_result.get("success"):
                return {"success": False, "error": card_result.get("error", "No active card slot found")}

            card = card_result.get("data", {})
            if card.get("card_status") == "collected":
                return {"success": False, "error": "Card already collected."}

            update_result = mark_card_collected(session_manager.reg_number)
            if not update_result.get("success") or update_result.get("rows_updated", 0) == 0:
                return {"success": False, "error": "Unable to update card status."}

            return {
                "success": True,
                "slot_index": card.get("slot_index"),
                "batch_id": card.get("batch_id"),
            }

        def callback(result):
            if token != self.flow_token:
                return
            if result.get("success"):
                session_manager.slot_index = result.get("slot_index")
                session_manager.batch_id = result.get("batch_id")
                self.wait_screen.set_status("Dispensing card...")
                self.wait_screen.set_detail(
                    "Please wait while the kiosk moves your card into position."
                )
                self.note_activity()
                self.sm.current = SCREEN_WAIT
            else:
                self._terminate_active_flow()
                self._set_error(
                    result.get("error", "Unable to find card slot."),
                    retry_screen=SCREEN_IDLE,
                )

        self._run_async(task, callback)

    def begin_dispense(self, *_):
        if self.dispense_in_progress:
            return
        if session_manager.slot_index is None:
            self._set_error(
                "No card slot is available for this session.",
                retry_screen=SCREEN_IDLE,
            )
            return

        self.dispense_in_progress = True
        token = self.flow_token
        self.wait_screen.set_status("Preparing card dispense...")
        self.wait_screen.set_detail(
            "Hardware is not enabled yet, so this step is simulated for now."
        )

        def _complete_simulation(_dt):
            if token != self.flow_token:
                return
            self.dispense_in_progress = False
            session_manager.update_activity()
            self.sm.current = SCREEN_CONFIRMATION

        Clock.schedule_once(_complete_simulation, 1.5)

    def schedule_confirmation_timeout(self):
        self._cancel_events()
        self.confirmation_event = Clock.schedule_once(
            lambda dt: self.finish_collection(), self.confirmation_timeout_seconds
        )

    def schedule_locked_return(self):
        self._cancel_events()
        self.lockout_event = Clock.schedule_once(
            lambda dt: self._go_idle(), self.lockout_screen_seconds
        )

    def finish_collection(self, *_):
        self._cancel_events()
        self._secure_dispenser()
        session_manager.teardown()
        self._reset_flow_state()
        self.sm.current = SCREEN_IDLE

    def retry_from_error(self, *_):
        retry_screen = self.error_screen.retry_screen
        if retry_screen == SCREEN_IDLE:
            self._go_idle()
            return
        self._clear_inputs()
        self.sm.current = retry_screen

    def _check_timeout(self, *_):
        if self.sm.current in (SCREEN_IDLE, SCREEN_WAIT):
            return
        if session_manager.is_timed_out(self.session_timeout_seconds):
            self._go_idle()

    def on_stop(self):
        self._secure_dispenser()
        session_manager.teardown()


if __name__ == "__main__":
    KioskApp().run()
