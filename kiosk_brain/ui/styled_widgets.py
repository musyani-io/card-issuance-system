"""
Styled widgets for the kiosk UI.
"""

from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

from ui.constants import REG_NUMBER_DIGITS, REG_NUMBER_LENGTH


def setup_screen_background(screen, bg_color=(0.04, 0.07, 0.12, 1)):
    with screen.canvas.before:
        Color(*bg_color)
        Rectangle(size=screen.size, pos=screen.pos)


def create_glass_card(orientation="vertical", padding=16, spacing=12, **kwargs):
    card = BoxLayout(
        orientation=orientation,
        padding=padding,
        spacing=spacing,
        **kwargs,
    )
    with card.canvas.before:
        Color(0.08, 0.13, 0.2, 0.72)
        card._bg = RoundedRectangle(radius=[22], pos=card.pos, size=card.size)
        Color(0.25, 0.9, 0.95, 0.25)
        card._border = Line(rounded_rectangle=[card.x, card.y, card.width, card.height, 22], width=1.2)

    def _update(*_):
        card._bg.pos = card.pos
        card._bg.size = card.size
        card._border.rounded_rectangle = [card.x, card.y, card.width, card.height, 22]

    card.bind(pos=_update, size=_update)
    return card


def create_primary_button(**kwargs):
    return Button(
        background_normal="",
        background_color=(0.1, 0.8, 0.9, 1),
        color=(0.02, 0.05, 0.09, 1),
        bold=True,
        font_size="20sp",
        **kwargs,
    )


def create_secondary_button(**kwargs):
    return Button(
        background_normal="",
        background_color=(0.12, 0.18, 0.28, 1),
        color=(0.9, 0.97, 1, 1),
        bold=True,
        font_size="18sp",
        **kwargs,
    )


def create_danger_button(**kwargs):
    return Button(
        background_normal="",
        background_color=(0.92, 0.18, 0.22, 1),
        color=(1, 1, 1, 1),
        bold=True,
        font_size="18sp",
        **kwargs,
    )


def create_numpad_button(**kwargs):
    return Button(
        background_normal="",
        background_color=(0.12, 0.2, 0.34, 1),
        color=(0.9, 0.98, 1, 1),
        bold=True,
        font_size="22sp",
        **kwargs,
    )


def create_title_label(**kwargs):
    return Label(
        color=(0.95, 0.99, 1, 1),
        font_size="32sp",
        bold=True,
        **kwargs,
    )


def create_subtitle_label(**kwargs):
    lbl = Label(
        color=(0.72, 0.87, 0.92, 1),
        font_size="20sp",
        **kwargs,
    )
    lbl.halign = "center"
    lbl.valign = "middle"
    lbl.bind(size=lambda instance, value: setattr(instance, "text_size", value))
    return lbl


def create_success_label(**kwargs):
    lbl = Label(
        color=(0.18, 0.92, 0.6, 1),
        font_size="28sp",
        bold=True,
        **kwargs,
    )
    lbl.halign = "center"
    lbl.valign = "middle"
    lbl.bind(size=lambda instance, value: setattr(instance, "text_size", value))
    return lbl


def create_error_label(**kwargs):
    lbl = Label(
        color=(0.98, 0.34, 0.38, 1),
        font_size="24sp",
        bold=True,
        **kwargs,
    )
    lbl.halign = "center"
    lbl.valign = "middle"
    lbl.bind(size=lambda instance, value: setattr(instance, "text_size", value))
    return lbl


def create_info_label(**kwargs):
    lbl = Label(
        color=(0.76, 0.86, 0.92, 1),
        font_size="18sp",
        **kwargs,
    )
    lbl.halign = "center"
    lbl.valign = "middle"
    lbl.bind(size=lambda instance, value: setattr(instance, "text_size", value))
    return lbl


class LimitedTextInput(TextInput):
    def __init__(self, max_length=None, numeric_only=False, **kwargs):
        self.max_length = max_length
        self.numeric_only = numeric_only
        super().__init__(**kwargs)

    def insert_text(self, substring, from_undo=False):
        if self.numeric_only:
            substring = "".join(ch for ch in substring if ch.isdigit())
        if not substring:
            return
        if self.max_length is not None:
            remaining = self.max_length - len(self.text)
            if remaining <= 0:
                return
            substring = substring[:remaining]
        super().insert_text(substring, from_undo=from_undo)


class RegNumberInput(LimitedTextInput):
    def __init__(self, **kwargs):
        self._normalizing = False
        super().__init__(max_length=REG_NUMBER_LENGTH, numeric_only=True, **kwargs)
        self.bind(text=self._normalize_text)

    @staticmethod
    def _format_digits(digits):
        parts = []
        if digits:
            parts.append(digits[:4])
        if len(digits) > 4:
            parts.append(digits[4:6])
        if len(digits) > 6:
            parts.append(digits[6:11])
        return "-".join(parts)

    def _normalize_text(self, instance, value):
        if self._normalizing:
            return
        digits = "".join(ch for ch in value if ch.isdigit())[:REG_NUMBER_DIGITS]
        formatted = self._format_digits(digits)
        if value != formatted:
            self._normalizing = True
            self.text = formatted
            self.cursor = (len(self.text), 0)
            self._normalizing = False

    def insert_text(self, substring, from_undo=False):
        digits = "".join(ch for ch in substring if ch.isdigit())
        if not digits:
            return
        current_digits = "".join(ch for ch in self.text if ch.isdigit())
        digits = (current_digits + digits)[:REG_NUMBER_DIGITS]
        self.text = self._format_digits(digits)
        self.cursor = (len(self.text), 0)


def create_styled_textinput(**kwargs):
    return LimitedTextInput(
        multiline=False,
        font_size="18sp",
        background_color=(0.08, 0.12, 0.18, 1),
        foreground_color=(0.95, 0.99, 1, 1),
        hint_text_color=(0.45, 0.62, 0.72, 1),
        cursor_color=(0.1, 0.8, 0.9, 1),
        padding=(15, 15),
        **kwargs,
    )
