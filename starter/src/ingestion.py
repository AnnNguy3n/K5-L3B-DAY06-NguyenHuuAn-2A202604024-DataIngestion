"""Read PDF text and embedded-image text with the corpus local vision extractor."""
from collections.abc import Iterable, Mapping
from copy import deepcopy
import logging
from pathlib import Path
import re
import unicodedata
from typing import Any

from pypdf import PdfReader

from scripts.figure_extraction import FigureExtractor, merge_figures
from .models import DocumentPage
from .text_structure import is_heading

LOGGER = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Use NFC, join wrapped lines, and preserve paragraphs and heading lines."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u2029", "\n\n").replace("\u2028", "\n")
    text = text.replace("\u200b", "").replace("\ufeff", "")
    lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in text.split("\n")]
    paragraphs, current = [], []
    in_figure = False
    for line in lines:
        if line.startswith("[Figure image:"):
            in_figure = True
        if not in_figure and (is_heading(line) or re.match(r"^(?:Figure|Table)\s+\d", line)):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            paragraphs.append(line)
        elif line:
            current.append(line)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
        if "[End figure image]" in line:
            in_figure = False
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def load_pdf(path: Path, document_id: str, source: str, *,
             page_numbers: Iterable[int] | None = None,
             metadata: Mapping[str, Any] | None = None,
             page_metadata: Mapping[int, Mapping[str, Any]] | None = None,
             errors: list[dict] | None = None,
             stats: dict | None = None,
             extractor: FigureExtractor | None = None,
             previous_figures: Mapping[int, list[dict]] | None = None,
             model: str = "mimo-v2.6:9b-mxfp8",
             ollama_url: str = "http://127.0.0.1:11434",
             timeout: float = 300) -> list[DocumentPage]:
    """Read all physical pages (1-based), or an explicit physical-page selection.

    Pass mutable ``errors``/``stats`` to collect diagnostics. Image failures keep
    available PDF text and mark the page incomplete; empty pages are not chunked.
    Uses the same image extraction and cache validation as scripts/read_corpus.py.
    With printed_page/section metadata, remove known corpus footers/attributions.
    """
    errors = errors if errors is not None else []
    stats = stats if stats is not None else {}
    stats.update(total_pages=0, attempted_pages=0, saved_pages=0, empty_pages=0,
                 error_count=0, image_count=0, saved_figures=0)
    error_start = len(errors)

    def record_error(number, stage, exc, **extra):
        error = dict(document_id=document_id, source=source, page=number,
                     stage=stage, error=str(exc), **extra)
        errors.append(error)
        stats["error_count"] = len(errors) - error_start
        LOGGER.warning("%s page=%s stage=%s: %s", source, number, stage, exc)

    numbers = list(page_numbers) if page_numbers is not None else None
    if numbers is not None:
        stats["total_pages"] = len(numbers)
    try:
        reader = PdfReader(Path(path))
        stats["physical_page_count"] = len(reader.pages)
    except Exception as exc:
        record_error(None, "source", exc)
        stats["status"] = "incomplete"
        return []
    if numbers is None:
        numbers = list(range(1, len(reader.pages) + 1))
    if (any(not isinstance(n, int) or isinstance(n, bool)
            or not 1 <= n <= len(reader.pages) for n in numbers)
            or len(numbers) != len(set(numbers))):
        raise ValueError("page_numbers must contain unique physical pages within PDF bounds")
    stats["total_pages"] = len(numbers)
    pages = []
    for number in numbers:
        LOGGER.info("Reading %s | physical page %d", source, number)
        stats["attempted_pages"] += 1
        details = deepcopy(dict(metadata or {}))
        details.update(deepcopy(dict((page_metadata or {}).get(number, {}))))
        details.setdefault("document_type", "pdf")
        details.setdefault("page_id", f"{document_id}:p{number:03d}")
        details["image_extraction_status"] = "complete"
        raw = ""
        try:
            pdf_page = reader.pages[number - 1]
        except Exception as exc:
            record_error(number, "page", exc)
            continue
        try:
            raw = pdf_page.extract_text() or ""
        except Exception as exc:
            record_error(number, "text", exc)
            details["text_extraction_status"] = "incomplete"
        else:
            details["text_extraction_status"] = "complete"
        body = raw
        if "printed_page" in details:
            lines = body.splitlines()
            printed = str(details["printed_page"])
            section = details.get("section", "")
            if lines and lines[-1].strip() in {printed, f"{printed} 2nd Edition", f"{section} {printed}"}:
                body = "\n".join(lines[:-1])
            body = re.split(r"(?m)^(?:References|Text Attributions|Media Attributions)\s*$",
                            body, maxsplit=1)[0]
        text_only = normalize_text(body)
        figures = []
        details["image_count"] = 0
        try:
            # Iterate rather than materialize so already extracted images survive
            # an error resolving a subsequent PDF image.
            for image in pdf_page.images:
                details["image_count"] += 1
                stats["image_count"] += 1
                try:
                    if extractor is None:
                        extractor = FigureExtractor(model, ollama_url, timeout)
                    figures.append(extractor.extract(
                        image, raw, (previous_figures or {}).get(number, [])))
                    stats["saved_figures"] += 1
                except Exception as exc:
                    details["image_extraction_status"] = "incomplete"
                    record_error(number, "figure", exc, image_name=image.name)
        except Exception as exc:
            details["image_extraction_status"] = "incomplete"
            record_error(number, "image_detection", exc)
        blocks, text = merge_figures(text_only, figures)
        text = normalize_text(text)
        if not text:
            stats["empty_pages"] += 1
            record_error(number, "empty_page", "No text after PDF and image extraction")
            continue
        details.update(char_count=len(text), text_only=text_only,
                       figures=figures, blocks=blocks)
        pages.append(DocumentPage(document_id, source, number, text, details))
        stats["saved_pages"] += 1
    stats["status"] = "complete" if stats["error_count"] == 0 else "incomplete"
    return pages
