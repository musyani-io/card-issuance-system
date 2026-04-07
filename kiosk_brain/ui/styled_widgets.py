"""
Styled Widgets Module — Reusable styled UI components for Card Issuance Kiosk

This module provides factory functions and pre-styled widget classes that apply
consistent styling across all screens. Styles are defined programmatically to ensure
they work whether or not the KV file is loaded.

BUTTON STYLES:
- PrimaryButton: Large blue action buttons
- SecondaryButton: Gray alternative buttons
- DangerButton: Red error/warning buttons
- NumPadButton: Numeric keypad buttons

LABEL STYLES:
- TitleLabel: Large bold blue titles
- SubtitleLabel: Medium descriptive text
- SuccessLabel: Green success messages
- ErrorLabel: Red error messages
- InfoLabel: Gray informational text

TEXTINPUT STYLES:
- StyledTextInput: Professional text inputs with blue borders
"""

from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle


def setup_screen_background(screen, bg_color=(0.97, 0.97, 0.98, 1)):
    """
    Add a background canvas to a screen.
    
    Args:
        screen: The Screen widget to add background to
        bg_color: RGBA tuple for background color (default light gray)
    """
    # Simple background - Kivy handles resizing automatically
    with screen.canvas.before:
        Color(*bg_color)
        Rectangle(size=screen.size, pos=screen.pos)


def create_primary_button(**kwargs):
    """
    Create a large blue button for primary actions.
    
    Args:
        **kwargs: Additional Button parameters (text, size_hint_y, etc.)
    
    Returns:
        Button: Styled primary action button
    """
    return Button(
        background_normal='',
        background_color=(0.15, 0.45, 0.8, 1),
        color=(1, 1, 1, 1),
        bold=True,
        font_size='20sp',
        **kwargs
    )


def create_secondary_button(**kwargs):
    """
    Create a gray button for secondary/alternative actions.
    
    Args:
        **kwargs: Additional Button parameters (text, size_hint_y, etc.)
    
    Returns:
        Button: Styled secondary button
    """
    return Button(
        background_normal='',
        background_color=(0.85, 0.85, 0.85, 1),
        color=(0.2, 0.2, 0.2, 1),
        bold=True,
        font_size='16sp',
        **kwargs
    )


def create_danger_button(**kwargs):
    """
    Create a red button for error/warning/retry actions.
    
    Args:
        **kwargs: Additional Button parameters (text, size_hint_y, etc.)
    
    Returns:
        Button: Styled danger/warning button
    """
    return Button(
        background_normal='',
        background_color=(0.9, 0.2, 0.2, 1),
        color=(1, 1, 1, 1),
        bold=True,
        font_size='18sp',
        **kwargs
    )


def create_numpad_button(**kwargs):
    """
    Create a numeric keypad button (slightly lighter blue).
    
    Args:
        **kwargs: Additional Button parameters (text, size_hint_y, etc.)
    
    Returns:
        Button: Styled numeric keypad button
    """
    return Button(
        background_normal='',
        background_color=(0.2, 0.5, 0.9, 1),
        color=(1, 1, 1, 1),
        bold=True,
        font_size='22sp',
        **kwargs
    )


def create_title_label(**kwargs):
    """
    Create a large bold blue title label.
    
    Args:
        **kwargs: Additional Label parameters (text, size_hint_y, etc.)
    
    Returns:
        Label: Styled title label
    """
    return Label(
        color=(0.15, 0.45, 0.8, 1),
        font_size='32sp',
        bold=True,
        text_size=(None, None),
        **kwargs
    )


def create_subtitle_label(**kwargs):
    """
    Create a medium descriptive subtitle label.
    
    Args:
        **kwargs: Additional Label parameters (text, size_hint_y, etc.)
    
    Returns:
        Label: Styled subtitle label
    """
    lbl = Label(
        color=(0.3, 0.3, 0.3, 1),
        font_size='20sp',
        **kwargs
    )
    lbl.text_size = (lbl.width, None)
    lbl.halign = 'center'
    return lbl


def create_success_label(**kwargs):
    """
    Create a green success message label.
    
    Args:
        **kwargs: Additional Label parameters (text, size_hint_y, etc.)
    
    Returns:
        Label: Styled success label (green text)
    """
    lbl = Label(
        color=(0.2, 0.7, 0.3, 1),
        font_size='28sp',
        bold=True,
        **kwargs
    )
    lbl.text_size = (lbl.width, None)
    lbl.halign = 'center'
    return lbl


def create_error_label(**kwargs):
    """
    Create a red error message label.
    
    Args:
        **kwargs: Additional Label parameters (text, size_hint_y, etc.)
    
    Returns:
        Label: Styled error label (red text)
    """
    lbl = Label(
        color=(0.9, 0.2, 0.2, 1),
        font_size='24sp',
        bold=True,
        **kwargs
    )
    lbl.text_size = (lbl.width, None)
    lbl.halign = 'center'
    return lbl


def create_info_label(**kwargs):
    """
    Create a gray informational label.
    
    Args:
        **kwargs: Additional Label parameters (text, size_hint_y, etc.)
    
    Returns:
        Label: Styled info label (gray text)
    """
    lbl = Label(
        color=(0.4, 0.4, 0.4, 1),
        font_size='18sp',
        **kwargs
    )
    lbl.text_size = (lbl.width, None)
    lbl.halign = 'center'
    return lbl


def create_standard_label(**kwargs):
    """
    Create a standard label with default styling (dark gray text).
    
    Args:
        **kwargs: Additional Label parameters (text, size_hint_y, etc.)
    
    Returns:
        Label: Standard label
    """
    return Label(
        color=(0.2, 0.2, 0.2, 1),
        font_size='16sp',
        **kwargs
    )


def create_styled_textinput(**kwargs):
    """
    Create a styled text input with professional appearance.
    
    Args:
        **kwargs: Additional TextInput parameters (multiline, input_filter, etc.)
    
    Returns:
        TextInput: Styled text input
    """
    return TextInput(
        multiline=False,
        font_size='18sp',
        background_color=(1, 1, 1, 1),
        foreground_color=(0.2, 0.2, 0.2, 1),
        hint_text_color=(0.8, 0.8, 0.8, 1),
        cursor_color=(0.15, 0.45, 0.8, 1),
        padding=(15, 15),
        **kwargs
    )
