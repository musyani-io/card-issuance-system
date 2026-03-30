from kivy.config import Config
from ui.screens import (
    WelcomeScreen,
    OTPEntryScreen,
    PINEntryScreen,
    ErrorScreen,
    ConfirmationScreen,
)

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

        sm.add_widget(welcome_screen)
        sm.add_widget(otp_entry_screen)
        sm.add_widget(pin_entry_screen)
        sm.add_widget(error_screen)
        sm.add_widget(confirmation_screen)

        welcome_screen.next_button.bind(
            on_press=lambda x: setattr(sm, "current", "otp_entry")
        )
        otp_entry_screen.submit_button.bind(
            on_press=lambda x: setattr(sm, "current", "pin_entry")
        )
        pin_entry_screen.submit_button.bind(
            on_press=lambda x: setattr(sm, "current", "confirmation")
        )
        confirmation_screen.ok_button.bind(
            on_press=lambda x: setattr(sm, "current", "welcome")
        )
        return sm


if __name__ == "__main__":
    KioskApp().run()
