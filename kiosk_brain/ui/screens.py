from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout
from ui.constants import *


def create_number_keypad(cols=3, callback=None):
    keypad = GridLayout(cols=cols, spacing=5, size_hint_y=0.4)

    for i in range(1, 10):
        keypad.add_widget(Button(text=str(i)))

    keypad.add_widget(Button(text="DEL"))
    keypad.add_widget(Button(text="0"))
    keypad.add_widget(Button(text="ENTER"))

    return keypad


class WelcomeScreen(Screen):
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
