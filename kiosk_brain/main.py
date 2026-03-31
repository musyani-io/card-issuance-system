from kivy.config import Config
from ui.screens import (
    WelcomeScreen,
    OTPEntryScreen,
    PINEntryScreen,
    ErrorScreen,
    ConfirmationScreen,
    RegEntryScreen
)
from ui.constants import *

Config.set("graphics", "width", "800")
Config.set("graphics", "height", "400")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager


class KioskApp(App):
    def build(self):
        sm = ScreenManager()
        welcome_screen = WelcomeScreen()
        otp_entry_screen = OTPEntryScreen()
        pin_entry_screen = PINEntryScreen()
        error_screen = ErrorScreen()
        confirmation_screen = ConfirmationScreen()
        reg_entry_screen = RegEntryScreen()

        sm.add_widget(welcome_screen)
        sm.add_widget(otp_entry_screen)
        sm.add_widget(pin_entry_screen)
        sm.add_widget(error_screen)
        sm.add_widget(confirmation_screen)
        sm.add_widget(reg_entry_screen)

        welcome_screen.ret_button.bind(
            on_press=lambda x: setattr(sm, "current", SCREEN_OTP_ENTRY)
        )
        welcome_screen.first_button.bind(
            on_press=lambda x: setattr(sm, 'current', SCREEN_REG_ENTRY)
        )
        reg_entry_screen.submit_button.bind(
            on_press=lambda x: setattr(sm, 'current', SCREEN_OTP_ENTRY)
        )
        otp_entry_screen.submit_button.bind(
            on_press=lambda x: setattr(sm, "current", SCREEN_PIN_ENTRY)
        )
        pin_entry_screen.submit_button.bind(
            on_press=lambda x: setattr(sm, "current", SCREEN_CONFIRMATION)
        )
        confirmation_screen.ok_button.bind(
            on_press=lambda x: setattr(sm, "current", SCREEN_WELCOME)
        )
        return sm


if __name__ == "__main__":
    KioskApp().run()
