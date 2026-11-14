"""Shared data contracts; keep traceability from chunk back to source."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentPage:
    """One normalized physical PDF page (1-based), including image evidence.

    Metadata stores section/language/type filters and extraction diagnostics.
    """

    document_id: str
    source: str
    page: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """A page-local span with a deterministic source/configuration/position ID.

    Metadata carries page filters, chunk configuration and [char_start, char_end)
    offsets into DocumentPage.text; large figure audit records stay on the page.
    """

    chunk_id: str
    document_id: str
    source: str
    page: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
