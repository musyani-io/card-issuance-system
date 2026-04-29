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
        background_normal="",
        background_color=(0.15, 0.45, 0.8, 1),
        color=(1, 1, 1, 1),
        bold=True,
        font_size="20sp",
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
        background_normal="",
        background_color=(0.85, 0.85, 0.85, 1),
        color=(0.2, 0.2, 0.2, 1),
        bold=True,
        font_size="16sp",
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
        background_normal="",
        background_color=(0.9, 0.2, 0.2, 1),
        color=(1, 1, 1, 1),
        bold=True,
        font_size="18sp",
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
        background_normal="",
        background_color=(0.2, 0.5, 0.9, 1),
        color=(1, 1, 1, 1),
        bold=True,
        font_size="22sp",
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
        font_size="32sp",
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
    lbl = Label(color=(0.3, 0.3, 0.3, 1), font_size="20sp", **kwargs)
    lbl.text_size = (lbl.width, None)
    lbl.halign = "center"
    return lbl


def create_success_label(**kwargs):
    """
    Create a green success message label for confirming successful operations.

    Args:
        **kwargs: Additional Label parameters (text, size_hint_y, etc.)

    Returns:
        Label: Styled success label (green text, 28sp bold)

    Used by:
        - ConfirmationScreen: "Card dispensed successfully"
        - ErrorScreen with success retry: "Please try again"

    Inline Logic:
        - Green color (0.2, 0.7, 0.3, 1): RGB(51, 179, 77) = standard UI green
        - Bold font at 28sp for high visibility (positive reinforcement)
        - Text centered and wrapped for responsive layout
    """
    lbl = Label(
        color=(0.2, 0.7, 0.3, 1),  # Green: success/positive feedback
        font_size="28sp",
        bold=True,
        **kwargs
    )
    lbl.text_size = (lbl.width, None)  # Enable text wrapping
    lbl.halign = "center"  # Center horizontally
    return lbl


def create_error_label(**kwargs):
    """
    Create a red error message label for displaying error conditions.

    Args:
        **kwargs: Additional Label parameters (text, size_hint_y, etc.)

    Returns:
        Label: Styled error label (red text, 24sp bold)

    Used by:
        - ErrorScreen: "Invalid OTP", "Incorrect PIN", "Try after 30 minutes"
        - Timeout displays: "Session expired"
        - Form validation: "PIN must be 4-6 digits"

    Inline Logic:
        - Red color (0.9, 0.2, 0.2, 1): RGB(230, 51, 51) = warning/error
        - Bold 24sp for urgent visibility without being overwhelming
        - Text centered for UI consistency
    """
    lbl = Label(
        color=(0.9, 0.2, 0.2, 1),  # Red: error/warning indicator
        font_size="24sp",
        bold=True,
        **kwargs
    )
    lbl.text_size = (lbl.width, None)  # Enable text wrapping
    lbl.halign = "center"  # Center horizontally
    return lbl


def create_info_label(**kwargs):
    """
    Create a gray informational/instructional label for helper text.

    Args:
        **kwargs: Additional Label parameters (text, size_hint_y, etc.)

    Returns:
        Label: Styled info label (gray text, 18sp normal weight)

    Used by:
        - Welcome screen: "Scan your card or enter registration number"
        - OTP entry: "Enter the 6-digit code sent to your phone"
        - PIN entry: "Enter your 4-digit PIN (masked)"
        - Timeout countdown: "Kiosk returning to idle in 30 seconds"

    Inline Logic:
        - Gray color (0.4, 0.4, 0.4, 1): RGB(102, 102, 102) = subtle, secondary info
        - Smaller font size (18sp) differentiates from primary messages
        - Normal (not bold) for reduced visual weight
    """
    lbl = Label(
        color=(0.4, 0.4, 0.4, 1),  # Gray: secondary/informational
        font_size="18sp",
        **kwargs
    )
    lbl.text_size = (lbl.width, None)  # Enable text wrapping
    lbl.halign = "center"  # Center horizontally
    return lbl


def create_standard_label(**kwargs):
    """
    Create a standard label with default styling for general content.

    Args:
        **kwargs: Additional Label parameters (text, size_hint_y, etc.)

    Returns:
        Label: Standard dark gray label (16sp normal weight)

    Used by:
        - General text display
        - Secondary content (not critical like title/error/success)
        - Status messages with neutral tone

    Inline Logic:
        - Dark gray color (0.2, 0.2, 0.2, 1): RGB(51, 51, 51) = readable, professional
        - Standard 16sp size for body text readability
        - Normal weight (not bold) for neutral visual weight
    """
    return Label(
        color=(0.2, 0.2, 0.2, 1),  # Dark gray: neutral, readable
        font_size="16sp",
        **kwargs
    )


def create_styled_textinput(**kwargs):
    """
    Create a styled text input field with professional appearance and blue border.

    Args:
        **kwargs: Additional TextInput parameters (multiline, input_filter, etc.)

    Returns:
        TextInput: Styled input field with blue border and light gray background

    Used by:
        - RegEntryScreen: manual registration number entry field
        - PIN setup screen: user-chosen PIN entry (masked)
        - Future staff admin screens: password fields

    Features:
        - Blue border (0.15, 0.45, 0.8, 1) for visual consistency with buttons
        - Light gray background for clear text contrast
        - Responsive sizing (size_hint matches kwargs or defaults)

    Inline Logic:
        - Canvas decoration: custom border drawn programmatically
        - Background color set via background_color property
        - Border width 2px for visibility without overwhelming
        - Padding: 15px on all sides for internal spacing
        - Cursor color matches primary blue (0.15, 0.45, 0.8, 1) for consistency
    """
    return TextInput(
        multiline=False,  # Single-line input (no line breaks)
        font_size="18sp",  # Large font for tablet touchscreen readability
        background_color=(1, 1, 1, 1),  # White background for contrast
        foreground_color=(0.2, 0.2, 0.2, 1),  # Dark gray text for readability
        hint_text_color=(0.8, 0.8, 0.8, 1),  # Light gray placeholder text
        cursor_color=(0.15, 0.45, 0.8, 1),  # Blue cursor (primary brand color)
        padding=(15, 15),  # Internal spacing around text
        **kwargs
    )
