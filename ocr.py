"""Read a student ID number from a photo of a physical ID card."""

import re

try:
    from rapidocr import RapidOCR

    _engine = RapidOCR()
except Exception:  # OCR is optional; manual typing still works without it.
    _engine = None

ID_RE = re.compile(r"(\d{2})\s*[-\u2013\u2014]?\s*(\d{4})\s*[-\u2013\u2014]?\s*(\d{6})")


def read_id(image: bytes) -> str | None:
    """Return the first `00-0000-000000` ID found in the image, or None."""
    if _engine is None:
        return None

    try:
        result = _engine(image)
    except Exception:
        return None

    for text in result.txts or []:
        match = ID_RE.search(text)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    return None
