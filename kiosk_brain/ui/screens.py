"""
Kivy screens for the kiosk student flow.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen

from ui.constants import (
    PIN_LENGTH,
    REG_NUMBER_FORMAT,
    SCREEN_CONFIRMATION,
    SCREEN_ERROR,
    SCREEN_IDLE,
    SCREEN_LOCKED,
    SCREEN_OTP_ENTRY,
    SCREEN_PIN_ENTRY,
    SCREEN_PIN_SETUP,
    SCREEN_REG_ENTRY,
    SCREEN_WAIT,
    OTP_LENGTH,
)
from ui.styled_widgets import (
    RegNumberInput,
    create_danger_button,
    create_error_label,
    create_glass_card,
    create_info_label,
    create_numpad_button,
    create_primary_button,
    create_styled_textinput,
    create_success_label,
    create_subtitle_label,
    create_title_label,
    setup_screen_background,
)


def create_number_keypad():
    keypad = GridLayout(cols=3, spacing=10, size_hint=(1, 1))
    for value in range(1, 10):
        keypad.add_widget(create_numpad_button(text=str(value)))
    keypad.add_widget(create_numpad_button(text="DEL"))
    keypad.add_widget(create_numpad_button(text="0"))
    keypad.add_widget(create_numpad_button(text="ENTER"))
    return keypad


def create_entry_split_shell():
    layout = BoxLayout(orientation="horizontal", padding=12, spacing=12)
    left = create_glass_card(padding=14, spacing=10, size_hint_x=0.4)
    right = create_glass_card(padding=14, spacing=10, size_hint_x=0.6)
    layout.add_widget(left)
    layout.add_widget(right)
    return layout, left, right


class IdleScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = SCREEN_IDLE
        setup_screen_background(self)

        layout = BoxLayout(orientation="vertical", padding=18, spacing=14)
        self.add_widget(layout)

        card = create_glass_card(padding=18, spacing=14)
        layout.add_widget(card)
        card.add_widget(create_title_label(text="Smart ID Card\nCollection"))
        card.add_widget(
            create_info_label(text="Tap to start your collection journey.")
        )

        self.collect_button = create_primary_button(
            text="Start Collection", size_hint_y=0.22
        )
        card.add_widget(self.collect_button)


class RegEntryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = SCREEN_REG_ENTRY
        setup_screen_background(self)

        layout, left, right = create_entry_split_shell()
        self.add_widget(layout)

        left.add_widget(create_title_label(text="Enter Registration Number"))
        left.add_widget(create_subtitle_label(text=f"Format: {REG_NUMBER_FORMAT}"))
        left.add_widget(
            create_info_label(text="Digits are auto-formatted as you type.")
        )

        self.reg_input = RegNumberInput(
            hint_text="2022-04-09050",
            size_hint_y=0.18,
        )
        left.add_widget(self.reg_input)

        self.submit_button = create_primary_button(text="Continue", size_hint_y=0.18)
        left.add_widget(self.submit_button)

        self.keypad = create_number_keypad()
        right.add_widget(self.keypad)

        for button in self.keypad.children:
            button.bind(on_press=self.on_keypad_press)

    def on_keypad_press(self, button):
        if button.text == "DEL":
            if self.reg_input.text:
                self.reg_input.text = self.reg_input.text[:-1]
        elif button.text == "ENTER":
            self.submit_button.trigger_action()
        else:
            self.reg_input.insert_text(button.text)

    def clear_inputs(self):
        self.reg_input.text = ""


class OTPEntryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = SCREEN_OTP_ENTRY
        setup_screen_background(self)

        layout, left, right = create_entry_split_shell()
        self.add_widget(layout)

        self.title_label = create_title_label(text="Enter OTP")
        self.info_label = create_subtitle_label(
            text="Enter the 6-digit OTP sent to your phone."
        )
        left.add_widget(self.title_label)
        left.add_widget(self.info_label)

        self.otp_input = create_styled_textinput(
            text="",
            numeric_only=True,
            max_length=OTP_LENGTH,
            size_hint_y=0.18,
        )
        self.submit_button = create_primary_button(
            text="Verify OTP", size_hint_y=0.18
        )
        left.add_widget(self.otp_input)
        left.add_widget(self.submit_button)

        self.keypad = create_number_keypad()
        right.add_widget(self.keypad)

        for button in self.keypad.children:
            button.bind(on_press=self.on_keypad_press)

    def on_keypad_press(self, button):
        if button.text == "DEL":
            if self.otp_input.text:
                self.otp_input.text = self.otp_input.text[:-1]
        elif button.text == "ENTER":
            self.submit_button.trigger_action()
        elif len(self.otp_input.text) < OTP_LENGTH:
            self.otp_input.insert_text(button.text)

    def clear_inputs(self):
        self.otp_input.text = ""


class PINEntryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = SCREEN_PIN_ENTRY
        setup_screen_background(self)

        layout, left, right = create_entry_split_shell()
        self.add_widget(layout)

        self.title_label = create_title_label(text="Enter PIN")
        self.info_label = create_subtitle_label(text="Enter your 4-digit PIN.")
        left.add_widget(self.title_label)
        left.add_widget(self.info_label)

        self.pin_input = create_styled_textinput(
            text="",
            numeric_only=True,
            max_length=PIN_LENGTH,
            password=True,
            size_hint_y=0.18,
        )
        self.submit_button = create_primary_button(
            text="Verify PIN", size_hint_y=0.18
        )
        left.add_widget(self.pin_input)
        left.add_widget(self.submit_button)

        self.keypad = create_number_keypad()
        right.add_widget(self.keypad)

        for button in self.keypad.children:
            button.bind(on_press=self.on_keypad_press)

    def configure_mode(self, mode):
        if mode == "temp":
            self.title_label.text = "Enter Temporary PIN"
            self.info_label.text = "Enter the 4-digit temporary PIN."
            self.submit_button.text = "Verify Temp PIN"
        else:
            self.title_label.text = "Enter PIN"
            self.info_label.text = "Enter your 4-digit PIN."
            self.submit_button.text = "Verify PIN"

    def on_keypad_press(self, button):
        if button.text == "DEL":
            if self.pin_input.text:
                self.pin_input.text = self.pin_input.text[:-1]
        elif button.text == "ENTER":
            self.submit_button.trigger_action()
        elif len(self.pin_input.text) < PIN_LENGTH:
            self.pin_input.insert_text(button.text)

    def clear_inputs(self):
        self.pin_input.text = ""


class PINSetupScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = SCREEN_PIN_SETUP
        setup_screen_background(self)

        layout = BoxLayout(orientation="vertical", padding=18, spacing=12)
        self.add_widget(layout)

        card = create_glass_card(padding=18, spacing=12)
        layout.add_widget(card)

        card.add_widget(create_title_label(text="Set Permanent PIN"))
        card.add_widget(
            create_info_label(text="Choose a new 4-digit PIN and confirm it.")
        )

        self.pin_input = create_styled_textinput(
            text="",
            numeric_only=True,
            max_length=PIN_LENGTH,
            password=True,
            hint_text="New PIN",
            size_hint_y=0.14,
        )
        self.confirm_input = create_styled_textinput(
            text="",
            numeric_only=True,
            max_length=PIN_LENGTH,
            password=True,
            hint_text="Confirm PIN",
            size_hint_y=0.14,
        )
        self.submit_button = create_primary_button(text="Set PIN", size_hint_y=0.16)

        card.add_widget(self.pin_input)
        card.add_widget(self.confirm_input)
        card.add_widget(self.submit_button)

    def clear_inputs(self):
        self.pin_input.text = ""
        self.confirm_input.text = ""


class WaitScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = SCREEN_WAIT
        setup_screen_background(self)

        layout = BoxLayout(orientation="vertical", padding=18, spacing=12)
        self.add_widget(layout)

        card = create_glass_card(padding=18, spacing=12)
        layout.add_widget(card)

        card.add_widget(create_title_label(text="Dispensing Card"))
        self.status_label = create_success_label(
            text="Please wait while the kiosk prepares your card."
        )
        self.detail_label = create_info_label(
            text="Keep clear of the dispenser until the next screen appears."
        )
        card.add_widget(self.status_label)
        card.add_widget(self.detail_label)

    def set_status(self, text):
        self.status_label.text = text

    def set_detail(self, text):
        self.detail_label.text = text


class ConfirmationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = SCREEN_CONFIRMATION
        setup_screen_background(self)

        layout = BoxLayout(orientation="vertical", padding=18, spacing=12)
        self.add_widget(layout)

        card = create_glass_card(padding=18, spacing=12)
        layout.add_widget(card)

        card.add_widget(
            create_success_label(text="Card dispensed successfully.")
        )
        self.detail_label = create_info_label(
            text="Please collect your card and tap Finish."
        )
        card.add_widget(self.detail_label)

        self.finish_button = create_primary_button(text="Finish", size_hint_y=0.16)
        card.add_widget(self.finish_button)

    def set_detail(self, text):
        self.detail_label.text = text


class ErrorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = SCREEN_ERROR
        setup_screen_background(self)

        layout = BoxLayout(orientation="vertical", padding=18, spacing=12)
        self.add_widget(layout)

        card = create_glass_card(padding=18, spacing=12)
        layout.add_widget(card)

        self.error_label = create_error_label(text="Something went wrong.")
        self.info_label = create_info_label(
            text="Tap Try Again to return to the previous step."
        )
        self.retry_button = create_danger_button(text="Try Again", size_hint_y=0.16)

        card.add_widget(self.error_label)
        card.add_widget(self.info_label)
        card.add_widget(self.retry_button)

        self.retry_screen = SCREEN_IDLE

    def set_error(self, message, retry_screen=SCREEN_IDLE):
        self.error_label.text = message
        self.retry_screen = retry_screen


class LockedScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = SCREEN_LOCKED
        setup_screen_background(self)

        layout = BoxLayout(orientation="vertical", padding=18, spacing=12)
        self.add_widget(layout)

        card = create_glass_card(padding=18, spacing=12)
        layout.add_widget(card)

        self.locked_label = create_error_label(text="Too many failed attempts.")
        self.info_label = create_info_label(
            text="Please wait for the lockout to clear and then try again."
        )
        card.add_widget(self.locked_label)
        card.add_widget(self.info_label)

    def set_message(self, message, detail=None):
        self.locked_label.text = message
        if detail is not None:
            self.info_label.text = detail
