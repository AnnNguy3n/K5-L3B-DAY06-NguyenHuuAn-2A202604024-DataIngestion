"""Text preparation shared by manifest generation and corpus extraction."""
import re
import unicodedata


def normalize_page(raw: str, printed_page: int, section: str) -> str:
    if not raw.strip():
        raise ValueError("No extractable text; OCR or replacement required")
    lines = raw.splitlines()
    footer = lines[-1].strip()
    printed = str(printed_page)
    if footer not in {printed, f"{printed} 2nd Edition", f"{section} {printed}"}:
        raise ValueError(f"Unexpected footer: {footer!r}")
    body = "\n".join(lines[:-1])
    body = re.split(
        r"(?m)^(?:References|Text Attributions|Media Attributions)\s*$",
        body, maxsplit=1,
    )[0]
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFC", body)).strip()
    if not text:
        raise ValueError("No useful text after normalization")
    return text
