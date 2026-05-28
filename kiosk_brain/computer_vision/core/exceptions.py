"""
Custom exceptions for card detection and OCR system.
"""


class CardNotFoundError(Exception):
    """
    Raised when no card is detected in the image
    """

    def __init__(self, message="No ID card detected in image."):
        self.message = message
        super().__init__(self.message)


class CardDetectionAmbiguousError(Exception):
    """
    Raised when multiple cards are detected in the image
    """

    def __init__(self, message="Multiple cards detected in image."):
        self.message = message
        super().__init__(self.message)


class OCRExtractionError(Exception):
    """
    Raised when OCR fails to extract registration_number
    """

    def __init__(self, message="Failed to extract registration_number from card."):
        self.message = message
        super().__init__(self.message)


class PerspectiveCorrectionError(Exception):
    """
    Raised when perspective correction fails or produces invalid output
    """

    def __init__(self, message="Failed to correct card perspective."):
        self.message = message
        super().__init__(self.message)


class InvalidStudentIDError(Exception):
    """
    Raised when extracted registration_number fails validation
    """

    def __init__(self, message="Extracted registration_number is invalid."):
        self.message = message
        super().__init__(self.message)
