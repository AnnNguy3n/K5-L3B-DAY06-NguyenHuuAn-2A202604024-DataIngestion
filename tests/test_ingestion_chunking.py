"""Traceability, coverage, Unicode and failure contracts for ingestion/chunking."""
from dataclasses import asdict
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from pypdf import PdfWriter

from starter.src.chunking import by_paragraph, fixed_size
from starter.src.ingestion import load_pdf, normalize_text
from starter.src.models import DocumentPage
from starter.src.prepare import prepare

ROOT = Path(__file__).resolve().parents[1]


class ChunkTests(unittest.TestCase):
    def page(self, text):
        return DocumentPage("doc", "source.pdf", 7, text,
                            {"section": "Scope", "nested": {"value": 1}})

    def test_normalization_preserves_paragraphs_and_is_idempotent(self):
        raw = "  Tiếng\u00a0Việt\t test\r\nwrapped  line\r\n \t\r\n\r\nNext\u2029Last\ufeff\u200b "
        text = normalize_text(raw)
        self.assertEqual(text, "Tiếng Việt test wrapped line\n\nNext\n\nLast")
        self.assertEqual(normalize_text(text), text)
        self.assertEqual(normalize_text(" \t\n\r"), "")

    def test_fixed_overlap_exact_end_and_validation(self):
        page = self.page("0123456789AB")
        chunks = fixed_size(page, 5, 2)
        self.assertEqual([c.text for c in chunks], ["01234", "34567", "6789A", "9AB"])
        self.assertEqual(len(fixed_size(self.page("12345"), 5, 4)), 1)
        for size, overlap in ((0, 0), (-1, 0), (5, -1), (5, 5), (5, 6), (2.5, 0), (5, True)):
            with self.assertRaises(ValueError):
                fixed_size(page, size, overlap)
        self.assertEqual(fixed_size(self.page(""), 5, 0), [])

    def test_paragraph_grouping_and_long_paragraphs_preserve_coverage(self):
        page = self.page("alpha\n\nbeta\n\nlong paragraph with words\n\n" + "x" * 29)
        chunks = by_paragraph(page, 12, long_overlap=0)
        self.assertEqual(chunks[0].text, "alpha\n\nbeta")
        self.assertTrue(all(0 < len(c.text) <= 12 for c in chunks))
        self.assertEqual(re.sub(r"\s", "", "".join(c.text for c in chunks)),
                         re.sub(r"\s", "", page.text))
        self.assertEqual(by_paragraph(self.page(" \n\n"), 12, long_overlap=0), [])
        for value in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                by_paragraph(page, value, long_overlap=0)

    def test_heading_boundaries_with_and_without_blank_lines(self):
        for separator in ("\n", "\n\n"):
            first_body, second_body, last_body = "first body " * 35, "second body " * 35, "last body " * 35
            text = separator.join(["intro text", "# First", first_body,
                                   "2. Second heading", second_body,
                                   "FINAL SECTION", last_body])
            chunks = by_paragraph(self.page(text), 1000)
            self.assertEqual(len(chunks), 4)
            self.assertEqual([c.metadata.get("heading") for c in chunks],
                             [None, "# First", "2. Second heading", "FINAL SECTION"])
            self.assertEqual(chunks[1].text, "# First" + separator + first_body)
            self.assertEqual(chunks[2].text, "2. Second heading" + separator + second_body)
            self.assertTrue(all(c.metadata["section"] == "Scope" for c in chunks))

    def test_title_case_headings_survive_normalization_and_long_sections(self):
        text = normalize_text("Initiation Phase\nfirst wrapped\nbody line\nPlanning Phase\n"
                              + "long body " * 15)
        self.assertTrue(text.startswith("Initiation Phase\n\nfirst wrapped body line\n\nPlanning Phase\n\n"))
        page = self.page(text)
        chunks = by_paragraph(page, 45, long_overlap=0)
        self.assertTrue(chunks[0].text.startswith("Initiation Phase"))
        self.assertTrue(chunks[1].text.startswith("Planning Phase\n\nlong body"))
        self.assertTrue(all(c.metadata["heading"] == "Planning Phase" for c in chunks[1:]))
        self.assertTrue(all(len(c.text) <= 45 for c in chunks))
        self.assertEqual(re.sub(r"\s", "", "".join(c.text for c in chunks)), re.sub(r"\s", "", text))
        for c in chunks:
            self.assertEqual(c.text, text[c.metadata["char_start"]:c.metadata["char_end"]])

    def test_prose_and_bullets_do_not_start_headings(self):
        text = "This is a sentence.\n\n- Bullet Item\n\nordinary body"
        self.assertEqual(len(by_paragraph(self.page(text), 1000)), 1)
        # Oversized heading and unbroken content still obey the size limit.
        chunks = by_paragraph(self.page("# " + "X" * 50 + "\nbody"), 10, long_overlap=0)
        self.assertTrue(all(0 < len(c.text) <= 10 for c in chunks))
        self.assertTrue(all(c.metadata["heading"].startswith("# ") for c in chunks))

    def test_long_paragraph_uses_exact_fixed_windows(self):
        page = self.page("# Overview\n\n" + "useful words " * 80)
        chunks = by_paragraph(page, 1000)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].text, page.text[:1000])
        self.assertEqual(chunks[1].text, page.text[900:])
        self.assertEqual(chunks[0].text[-100:], chunks[1].text[:100])
        self.assertEqual([c.metadata["overlap_char_count"] for c in chunks], [0, 100])
        self.assertEqual(chunks[0].text + chunks[1].text[100:], page.text)

    def test_overlap_stays_inside_each_long_paragraph(self):
        first, second = "a" * 1901, "b" * 1100
        page = self.page("short intro\n\n" + first + "\n\n" + second + "\n\nshort ending")
        chunks = by_paragraph(page, 1000)
        self.assertEqual([len(c.text) for c in chunks], [11, 1000, 1000, 101, 1000, 200, 12])
        self.assertEqual([c.metadata["overlap_char_count"] for c in chunks], [0, 0, 100, 100, 0, 100, 0])
        for c in chunks[1:4]:
            self.assertEqual(set(c.text), {"a"})
        for c in chunks[4:6]:
            self.assertEqual(set(c.text), {"b"})
        reconstructed = "".join(c.text[c.metadata["overlap_char_count"]:] for c in chunks)
        self.assertEqual(re.sub(r"\s", "", reconstructed), re.sub(r"\s", "", page.text))
        for c in chunks:
            m = c.metadata
            self.assertEqual(c.text, page.text[m["char_start"]:m["char_end"]])

    def test_short_paragraphs_pack_without_overlap_or_crossing_heading(self):
        text = "a" * 600 + "\n\n" + "b" * 600 + "\n\n# Next\n\n" + "c" * 1100
        chunks = by_paragraph(self.page(text), 1000)
        self.assertEqual([len(c.text) for c in chunks], [600, 600, 1000, 208])
        self.assertTrue(all(c.metadata["overlap_char_count"] == 0 for c in chunks[:3]))
        self.assertEqual(chunks[3].metadata["overlap_char_count"], 100)
        self.assertEqual(chunks[2].metadata["heading"], "# Next")
        for value in (-1, 1000, 1001, 1.5, True):
            with self.assertRaises(ValueError):
                by_paragraph(self.page(text), 1000, long_overlap=value)
        # Exact-size paragraphs do not emit redundant overlap-only tails.
        self.assertEqual(len(by_paragraph(self.page("a" * 1000), 1000)), 1)

    def test_figure_labels_and_table_cells_are_not_headings(self):
        text = ("[Figure image: Figure 1.1]\nLabels: Government\n\n"
                "Top Management\n\nExternal Customers\n[End figure image]\n\n"
                "Table 1.1 Register\n\nProject\n\nScope\n\nManagement")
        chunks = by_paragraph(self.page(text), 1000)
        self.assertEqual(len(chunks), 1)
        self.assertNotIn("heading", chunks[0].metadata)
        normalized = normalize_text("[Figure image: Figure 1.1]\nLabels: Government\n"
                                    "Top Management\nExternal Customers\n[End figure image]")
        self.assertNotIn("\n\nTop Management", normalized)
        table = normalize_text("introductory sentence.\nTable 1.1 Register\n"
                               "Stakeholder\nNames and\nRoles\nimportant?\n"
                               "(Low – Med –\nHigh)")
        table_chunks = by_paragraph(self.page(table), 1000)
        self.assertEqual(len(table_chunks), 1)
        self.assertNotIn("heading", table_chunks[0].metadata)

    def test_small_sections_merge_and_keep_all_headings(self):
        page = self.page("# First\n\nshort body\n\n# Second\n\nanother short body")
        chunks = by_paragraph(page, 1000)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, page.text)
        self.assertEqual(chunks[0].metadata["headings"], ["# First", "# Second"])
        self.assertEqual(chunks[0].metadata["section"], "Scope")

    def test_consecutive_headings_stay_with_body(self):
        page = self.page("# Parent\n\n## Child\n\n" + "body text " * 45)
        chunks = by_paragraph(page, 1000)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].metadata["headings"], ["# Parent", "## Child"])
        self.assertEqual(chunks[0].text, page.text)

    def test_ids_offsets_metadata_and_reload(self):
        page = self.page("hello world\n\nnext paragraph")
        for split in (lambda p: fixed_size(p, 10, 2), lambda p: by_paragraph(p, 10, long_overlap=0)):
            chunks = split(page)
            self.assertEqual([asdict(c) for c in chunks], [asdict(c) for c in split(page)])
            self.assertEqual(len({c.chunk_id for c in chunks}), len(chunks))
            for c in chunks:
                self.assertEqual((c.document_id, c.source, c.page), ("doc", "source.pdf", 7))
                self.assertEqual(c.metadata["section"], "Scope")
                self.assertEqual(c.text, page.text[c.metadata["char_start"]:c.metadata["char_end"]])
            chunks[0].metadata["nested"]["value"] = 9
            self.assertEqual(page.metadata["nested"]["value"], 1)
        self.assertNotEqual(fixed_size(page, 10, 2)[0].chunk_id,
                            fixed_size(page, 10, 3)[0].chunk_id)
        other = self.page(page.text)
        other.source = "other.pdf"
        self.assertNotEqual(by_paragraph(page, 10, long_overlap=0)[0].chunk_id, by_paragraph(other, 10, long_overlap=0)[0].chunk_id)


class IngestionTests(unittest.TestCase):
    def pdf_page(self, text="", images=()):
        return SimpleNamespace(extract_text=Mock(return_value=text), images=images)

    def test_mixed_and_image_only_pages_keep_physical_numbers(self):
        image = SimpleNamespace(name="scan.png")
        figure = {"caption_anchor": "", "transcription": "OCR words",
                  "description": "", "uncertainties": ""}
        extractor = Mock()
        extractor.extract.return_value = figure
        reader = SimpleNamespace(pages=[self.pdf_page("skip"),
            self.pdf_page("PDF words\n\nparagraph", [image]), self.pdf_page("", [image])])
        errors, stats = [], {}
        with patch("starter.src.ingestion.PdfReader", return_value=reader):
            pages = load_pdf(Path("fake.pdf"), "doc", "fake.pdf", page_numbers=[2, 3],
                             page_metadata={2: {"section": "Scope"}},
                             errors=errors, stats=stats, extractor=extractor)
        self.assertEqual([p.page for p in pages], [2, 3])
        self.assertIn("PDF words\n\nparagraph", pages[0].text)
        self.assertTrue(all("OCR words" in p.text for p in pages))
        self.assertEqual(pages[0].metadata["section"], "Scope")
        self.assertEqual(errors, [])
        self.assertEqual((stats["total_pages"], stats["error_count"], stats["saved_figures"]), (2, 0, 2))

    def test_empty_failed_page_and_failed_image_are_logged(self):
        broken = self.pdf_page()
        broken.extract_text.side_effect = ValueError("broken text")
        reader = SimpleNamespace(pages=[self.pdf_page(), broken,
            self.pdf_page("keep text", [SimpleNamespace(name="bad.png")])])
        extractor = Mock()
        extractor.extract.side_effect = RuntimeError("vision offline")
        errors, stats = [], {}
        with patch("starter.src.ingestion.PdfReader", return_value=reader):
            pages = load_pdf(Path("fake.pdf"), "doc", "fake.pdf", errors=errors,
                             stats=stats, extractor=extractor)
        self.assertEqual([p.page for p in pages], [3])
        self.assertEqual(pages[0].text, "keep text")
        self.assertEqual(pages[0].metadata["image_extraction_status"], "incomplete")
        self.assertEqual([e["stage"] for e in errors], ["empty_page", "text", "empty_page", "figure"])
        self.assertEqual(stats["error_count"], 4)
        self.assertEqual(stats["empty_pages"], 2)

    def test_real_blank_pdf_and_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blank.pdf"
            writer = PdfWriter()
            for _ in range(2):
                writer.add_blank_page(width=72, height=72)
            writer.write(path)
            errors, stats = [], {}
            self.assertEqual(load_pdf(path, "doc", str(path), errors=errors, stats=stats), [])
            self.assertEqual([e["page"] for e in errors], [1, 2])
            self.assertEqual(stats["total_pages"], 2)
            with self.assertRaises(ValueError):
                load_pdf(path, "doc", str(path), page_numbers=[1, 1])
            errors = []
            load_pdf(path.with_name("missing.pdf"), "doc", "missing.pdf", errors=errors)
            self.assertEqual(errors[0]["stage"], "source")

    def test_export_and_reload_without_errors(self):
        # Real PDF parsing and corpus selection; mock only external vision calls.
        extractor_result = {"caption_anchor": "", "transcription": "test only",
                            "description": "", "uncertainties": ""}
        with tempfile.TemporaryDirectory() as directory, patch(
            "starter.src.ingestion.FigureExtractor.extract", side_effect=lambda *args: dict(extractor_result)
        ):
            output = Path(directory)
            first = prepare(ROOT / "data/manifest.json", output)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            second = prepare(ROOT / "data/manifest.json", output)
            self.assertEqual(first, second)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
            self.assertEqual((first["total_pages"], first["saved_pages"], first["error_count"]), (32, 32, 0))
            self.assertEqual((output / "ingestion_errors.jsonl").read_text(), "")
            for name, limit in (("A", 500), ("B", 1000)):
                rows = [json.loads(line) for line in (output / f"chunks_{name}.jsonl").read_text().splitlines()]
                self.assertTrue(all(0 < len(c["text"]) <= limit and c["metadata"]["section"] for c in rows))


if __name__ == "__main__":
    unittest.main()
