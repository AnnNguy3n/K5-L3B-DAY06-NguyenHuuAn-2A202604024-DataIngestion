"""Contract/error/cache tests; mocked responses never enter corpus artifacts."""
import json
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from figure_extraction import FigureExtractor, merge_figures
from read_corpus import read_corpus


class FigureTests(unittest.TestCase):
    def setUp(self):
        self.extractor = FigureExtractor("test:local", "http://127.0.0.1:11434", 1)
        self.image = SimpleNamespace(name="test.png", image=Image.new("RGB", (12, 12)))

    def responses(self, content):
        return [
            {"capabilities": ["vision"]},
            {"models": [{"name": "test:local", "digest": "test-digest"}]},
            {"done": True, "message": {"content": json.dumps(content)}},
        ]

    def test_cache_uses_same_image_model_and_context(self):
        content = {"caption_anchor": "Figure 4.1", "transcription": "time",
                   "description": "A circle", "uncertainties": ""}
        with patch("figure_extraction.request_json", side_effect=self.responses(content)) as request:
            first = self.extractor.extract(self.image, "Figure 4.1: caption")
            self.assertNotIn("review_status", first)
            self.assertEqual(request.call_args.args[1], "chat")
            self.assertTrue(request.call_args.args[2]["messages"][0]["images"])
            self.assertEqual(self.extractor.extract(self.image, "Figure 4.1: caption", [first]), first)
            self.assertEqual(request.call_count, 3)
            legacy = {**first, "review_status": "pending"}
            self.assertNotIn("review_status", self.extractor.extract(
                self.image, "Figure 4.1: caption", [legacy]))
        with patch("figure_extraction.request_json", side_effect=RuntimeError("timeout")):
            with self.assertRaisesRegex(RuntimeError, "timeout"):
                self.extractor.extract(self.image, "changed context", [first])

    def test_reject_invalid_response_and_nonvision_model(self):
        with patch("figure_extraction.request_json", side_effect=self.responses({"description": "only"})):
            with self.assertRaisesRegex(ValueError, "four string fields"):
                self.extractor.extract(self.image, "caption")
        self.extractor.model_digest = None
        with patch("figure_extraction.request_json", return_value={"capabilities": ["completion"]}):
            with self.assertRaisesRegex(ValueError, "vision support"):
                self.extractor.extract(self.image, "caption")

    def test_anchor_does_not_match_earlier_prose_reference(self):
        figures = [{"caption_anchor": "Figure 4.1", "transcription": "time",
                    "description": "A circle", "uncertainties": "", "review_status": "pending"}]
        blocks, text = merge_figures("See Figure 4.1. Before. Figure 4.1: Caption. After.", figures)
        self.assertEqual([b["type"] for b in blocks], ["text", "figure", "text"])
        self.assertTrue(blocks[0]["text"].endswith("Before."))
        self.assertEqual(text.count("Figure 4.1: Caption"), 1)
        self.assertNotIn("unverified", text)
        self.assertNotIn("review_status", blocks[1])
        self.assertNotIn("pending", json.dumps(blocks))
        figures[0]["caption_anchor"] = ""
        blocks, _ = merge_figures("Original text", figures)
        self.assertEqual(blocks[-1]["placement"], "page_end_unresolved")

    def test_vision_failure_preserves_all_text_and_logs_each_image(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            terminal = io.StringIO()
            with redirect_stdout(terminal), patch(
                "figure_extraction.FigureExtractor.extract", side_effect=RuntimeError("test timeout")
            ):
                code = read_corpus(root / "data/manifest.json", output)
            log = (output / "extract.log").read_text()
            for message in ("[1/32]", "PDF page 40", "images detected=1",
                            "test timeout", "INCOMPLETE", "[32/32]", "RESULT", "END"):
                self.assertIn(message, log)
                self.assertIn(message, terminal.getvalue())
            rows = [json.loads(line) for line in (output / "pages.jsonl").read_text().splitlines()]
            errors = [json.loads(line) for line in (output / "errors.jsonl").read_text().splitlines()]
            self.assertEqual(code, 1)
            self.assertEqual(len(rows), 32)
            self.assertEqual({row["page"] for row in errors}, {40, 54, 63})
            self.assertTrue(all(row["text"] == row["text_only"] for row in rows))
            self.assertEqual(sum(row["char_count"] for row in rows), 85519)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["status"], "incomplete")
            self.assertNotIn("figures_pending_review", summary)
            self.assertTrue(all("requires_figure_review" not in row for row in rows))

    def test_success_progress_and_log_append_across_runs(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            terminal = io.StringIO()
            def figure(*args):
                return {"caption_anchor": "", "transcription": "test label",
                        "description": "test description", "uncertainties": ""}
            with redirect_stdout(terminal), patch(
                "figure_extraction.FigureExtractor.extract", side_effect=figure
            ):
                for _ in range(2):
                    self.assertEqual(read_corpus(root / "data/manifest.json", output), 0)
            log = (output / "extract.log").read_text()
            self.assertEqual(log.count("START | manifest="), 2)
            self.assertEqual(log.count("RESULT | status=complete"), 2)
            self.assertEqual(log.count("image I13.jpg | OK"), 2)
            self.assertIn("images detected=0", log)
            self.assertIn("saved figures=3 | errors=0", log)


if __name__ == "__main__":
    unittest.main()
