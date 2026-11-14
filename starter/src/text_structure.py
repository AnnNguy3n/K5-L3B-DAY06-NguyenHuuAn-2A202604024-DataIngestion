"""Conservative heading recognition for extracted plain text (no PDF font data)."""
import re

_CONNECTORS = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of",
               "on", "or", "the", "to", "with", "và", "của", "trong", "cho"}


def is_heading(line: str) -> bool:
    """Recognize Markdown, numbered, ALL CAPS and short Title Case headings.

    Plain text has no font/size information, so unmarked sentence-case headings
    may be missed. Avoid treating bullets or complete sentences as headings.
    """
    line = line.strip()
    if re.fullmatch(r"#{1,6}\s+\S.*", line):
        return True
    if not line or len(line) > 120 or line.endswith((".", "?", "!", ";", ",")):
        return False
    if re.match(r"(?:Figure|Table)\s+\d|(?:Labels|Visible structure|Uncertainties):", line):
        return False
    if re.match(r"[-*•]\s", line):
        return False
    numbered = re.match(r"\d+(?:\.\d+)*(?:[.)])?\s+(.+)", line)
    title = numbered.group(1) if numbered else line
    words = re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)?", title, re.UNICODE)
    if not words or len(words) > 12 or not words[0][0].isupper():
        return False
    if numbered or title.isupper():
        return True
    return all((word[0].isupper() and (word[1:].islower() or word.isupper() or len(word) == 1))
               or word.casefold() in _CONNECTORS for word in words)
