import re
from typing import Optional, Tuple, List


OCR_CORRECTIONS = {
    "O": "0",
    "I": "1",
    "L": "1",
    "S": "5",
    "B": "8",
}


def normalize_ocr_text(text: str) -> str:
    """
    Normalize OCR text by fixing common character confusions.
    """
    if not text:
        return ""

    normalized = []
    for ch in text:
        normalized.append(OCR_CORRECTIONS.get(ch, ch))
    return "".join(normalized)


def extract_registration_number(text: str, pattern: str) -> str:
    """
    Extract the first registration_number match from text using the provided regex pattern.
    """
    match = re.search(pattern, text)
    return match.group(0) if match else ""


def validate_registration_number(
    registration_number: str,
    pattern: str,
    valid_year_range: Tuple[int, int],
    total_length: int,
) -> bool:
    """
    Validate registration_number by pattern, length, and year range.
    """
    if not registration_number:
        return False

    if len(registration_number) != total_length:
        return False

    if re.fullmatch(pattern, registration_number) is None:
        return False

    year_str = registration_number.split("-")[0]
    if not year_str.isdigit():
        return False

    year = int(year_str)
    return valid_year_range[0] <= year <= valid_year_range[1]


def extract_and_validate_registration_number(
    text: str,
    pattern: str,
    valid_year_range: Tuple[int, int],
    total_length: int,
) -> Optional[str]:
    """
    Extract and validate registration_number. Returns the ID or None if invalid.
    """
    candidate = extract_registration_number(text, pattern)
    if validate_registration_number(candidate, pattern, valid_year_range, total_length):
        return candidate

    corrected_text = normalize_ocr_text(text)
    candidate = extract_registration_number(corrected_text, pattern)
    if validate_registration_number(candidate, pattern, valid_year_range, total_length):
        return candidate

    return None


def extract_registration_number_robust(
    texts: List[str],
    pattern: str,
    valid_year_range: Tuple[int, int],
    total_length: int,
) -> Optional[str]:
    """
    Try multiple OCR outputs and return the most frequent valid registration_number.
    """
    valid_ids: List[str] = []

    for text in texts:
        candidate = extract_and_validate_registration_number(
            text, pattern, valid_year_range, total_length
        )
        if candidate:
            valid_ids.append(candidate)

    if not valid_ids:
        return None

    counts: dict = {}
    for value in valid_ids:
        counts[value] = counts.get(value, 0) + 1

    return max(counts, key=counts.get)
