"""Page-local chunking with deterministic IDs and character offsets."""
from copy import deepcopy
import hashlib
import json
import re

from .models import Chunk, DocumentPage
from .text_structure import is_heading


def _chunk(page: DocumentPage, start: int, end: int, index: int,
           config: dict) -> Chunk:
    identity = [page.document_id, page.source, page.page, config, index, start, end]
    chunk_id = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    metadata = deepcopy({key: value for key, value in page.metadata.items()
                         if key not in {"text_only", "figures", "blocks"}})
    # Even callers without a manifest get a usable document-level filter.
    metadata.setdefault("document_type", "pdf")
    metadata.update(chunking=config.copy(), chunk_index=index,
                    char_start=start, char_end=end, char_count=end - start)
    return Chunk(chunk_id, page.document_id, page.source, page.page,
                 page.text[start:end], metadata)


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Split into character windows; offsets refer to the normalized page text."""
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ValueError("size must be a positive integer")
    if (not isinstance(overlap, int) or isinstance(overlap, bool)
            or not 0 <= overlap < size):
        raise ValueError("overlap must be an integer with 0 <= overlap < size")
    chunks = []
    config = {"method": "fixed_size", "version": 1, "size": size, "overlap": overlap}
    for start in range(0, len(page.text), size - overlap):
        end = min(start + size, len(page.text))
        if page.text[start:end].strip():
            chunks.append(_chunk(page, start, end, len(chunks), config))
        if end == len(page.text):
            break
    return chunks


def _paragraph_spans(text: str):
    """Yield paragraphs/headings, excluding figure labels and table cells.

    A table caption starts table context; substantive prose ends it. This is a
    text heuristic, not a reconstruction of PDF table geometry.
    """
    start = end = None
    offset = 0
    in_figure = in_table = False
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        stripped = content.strip()
        if stripped.startswith("[Figure image:"):
            in_figure = True
        if re.match(r"Table\s+\d+(?:\.\d+)*\b", stripped):
            in_table = True
        elif len(stripped) > 120 and not in_figure:
            in_table = False
        heading = not in_figure and not in_table and is_heading(content)
        if not stripped or heading:
            if start is not None:
                yield start, end, False
                start = end = None
            if heading:
                yield offset, offset + len(content), True
        else:
            if start is None:
                start = offset
            end = offset + len(content)
        offset += len(line)
        if "[End figure image]" in stripped:
            in_figure = False
    if start is not None:
        yield start, end, False


def by_paragraph(page: DocumentPage, max_size: int, long_overlap: int = 100) -> list[Chunk]:
    """Pack paragraphs; use fixed windows only for an oversized paragraph.

    Long-paragraph windows overlap by exactly long_overlap characters. Heading
    prefixes stay with the first paragraph. Overlap never crosses that paragraph
    unit, a page boundary or a heading boundary. Short neighboring sections can
    still share one chunk, with all recognized headings retained in metadata.
    """
    if not isinstance(max_size, int) or isinstance(max_size, bool) or max_size <= 0:
        raise ValueError("max_size must be a positive integer")
    if (not isinstance(long_overlap, int) or isinstance(long_overlap, bool)
            or not 0 <= long_overlap < max_size):
        raise ValueError("long_overlap must be an integer with 0 <= long_overlap < max_size")
    config = {"method": "by_paragraph", "version": 4, "max_size": max_size,
              "heading_detection": "contextual_headings_v2",
              "target_min_size": max(1, max_size // 3),
              "split": "fixed_size_long_paragraph", "long_overlap": long_overlap}
    sections = []
    start = end = None
    headings = []
    paragraphs = []
    has_body = False
    for span_start, span_end, heading in _paragraph_spans(page.text):
        if heading and has_body:
            sections.append((start, end, headings, paragraphs))
            start = end = None
            headings = []
            paragraphs = []
            has_body = False
        if start is None:
            start = span_start
        end = span_end
        if heading:
            headings.append(page.text[span_start:span_end].strip())
        else:
            # Include heading prefixes in the first paragraph unit so headings
            # do not become standalone tiny chunks before a long paragraph.
            paragraphs.append((start if not has_body else span_start, span_end))
            has_body = True
    if start is not None:
        sections.append((start, end, headings, paragraphs))
    # Short adjacent blocks (often table cells or labels with no body) are
    # more useful together. Preserve every recognized heading in metadata.
    grouped = []
    minimum = config["target_min_size"]
    for start, end, headings, paragraphs in sections:
        if (grouped and end - start < minimum
                and grouped[-1][1] - grouped[-1][0] < minimum
                and end - grouped[-1][0] <= max_size):
            previous_start, _, previous_headings, _ = grouped.pop()
            grouped.append((previous_start, end, previous_headings + headings, [(previous_start, end)]))
        else:
            grouped.append((start, end, headings, paragraphs))
    chunks = []

    def emit(start, end, headings, *, overlap=0, scope=None):
        if not page.text[start:end].strip():
            return
        chunk = _chunk(page, start, end, len(chunks), config)
        if headings:
            chunk.metadata["heading"] = headings[-1]
            chunk.metadata["headings"] = headings.copy()
        chunk.metadata["overlap_char_count"] = overlap
        if scope is not None:
            chunk.metadata.update(split_scope_start=scope[0], split_scope_end=scope[1])
        chunks.append(chunk)

    for start, end, headings, paragraphs in grouped:
        pending = None
        # A heading-only section is still retained.
        for para_start, para_end in paragraphs or [(start, end)]:
            if para_end - para_start > max_size:
                if pending is not None:
                    emit(*pending, headings)
                    pending = None
                previous_end = None
                for window_start in range(para_start, para_end, max_size - long_overlap):
                    window_end = min(window_start + max_size, para_end)
                    emit(window_start, window_end, headings,
                         overlap=0 if previous_end is None else previous_end - window_start,
                         scope=(para_start, para_end))
                    previous_end = window_end
                    if window_end == para_end:
                        break
            elif pending is not None and para_end - pending[0] <= max_size:
                pending = (pending[0], para_end)
            else:
                if pending is not None:
                    emit(*pending, headings)
                pending = (para_start, para_end)
        if pending is not None:
            emit(*pending, headings)
    return chunks
