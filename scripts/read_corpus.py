"""Read selected PDF pages from a manifest and save raw/normalized text locally."""
import argparse
import hashlib
import importlib.metadata
import json
import logging
from pathlib import Path
import sys
import time

from pypdf import PdfReader

from corpus_text import normalize_page
from figure_extraction import FigureExtractor, merge_figures

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("corpus.extract")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, records: list[dict]) -> None:
    # Replace each run's output rather than appending duplicate pages.
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records),
        encoding="utf-8",
    )
    temporary.replace(path)


def read_corpus(manifest_path: Path, output_dir: Path, *,
                model="mimo-v2.6:9b-mxfp8", ollama_url="http://127.0.0.1:11434",
                timeout=300) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    handlers = [logging.StreamHandler(sys.stdout),
                logging.FileHandler(output_dir / "extract.log", encoding="utf-8")]
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s",
                                  datefmt="%Y-%m-%d %H:%M:%S")
    old_handlers, old_level, old_propagate = LOGGER.handlers[:], LOGGER.level, LOGGER.propagate
    LOGGER.handlers = handlers
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    for handler in handlers:
        handler.setFormatter(formatter)
    started = time.monotonic()
    LOGGER.info("START | manifest=%s | model=%s | output=%s", manifest_path, model, output_dir)
    try:
        return _read_corpus(manifest_path, output_dir, model=model,
                            ollama_url=ollama_url, timeout=timeout)
    except Exception:
        LOGGER.exception("FAILED | extraction stopped unexpectedly")
        raise
    finally:
        LOGGER.info("END | elapsed=%.2fs", time.monotonic() - started)
        for handler in handlers:
            handler.close()
        LOGGER.handlers, LOGGER.level, LOGGER.propagate = old_handlers, old_level, old_propagate


def _read_corpus(manifest_path: Path, output_dir: Path, *,
                 model: str, ollama_url: str, timeout: float) -> int:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("path_base") != "repository_root":
        raise ValueError("Manifest path_base must be repository_root")
    records, errors, seen = [], [], set()
    extractor = FigureExtractor(model, ollama_url, timeout)
    previous = {}
    previous_path = output_dir / "pages.jsonl"
    if previous_path.exists():
        for line in previous_path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            previous[record["page_id"]] = record.get("figures", [])
    expected_pages = sum(len(s["selected_pdf_pages"]) for s in manifest["sources"])
    LOGGER.info("Corpus %s | selected pages=%d", manifest["corpus_id"], expected_pages)
    progress = 0
    for source in manifest["sources"]:
        source_id = source["source_id"]
        LOGGER.info("Source %s | validating PDF snapshot", source_id)
        try:
            pdf_path = ROOT / source["source_path_or_url"]
            actual_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
            if actual_hash != source["snapshot"]["sha256"]:
                raise ValueError("PDF SHA-256 differs from manifest; review snapshot before extraction")
            reader = PdfReader(pdf_path)
            if len(reader.pages) != source["physical_page_count"]:
                raise ValueError("Physical page count differs from manifest")
            selected = source["selected_pdf_pages"]
            if len(set(selected)) != len(selected):
                raise ValueError("Duplicate selected PDF pages")
            page_map = {p["page"]: p for p in source["pages"]}
            if len(page_map) != len(source["pages"]) or set(page_map) != set(selected):
                raise ValueError("Page metadata must match selected_pdf_pages exactly")
        except Exception as exc:
            LOGGER.error("Source %s | FAILED | %s", source_id, exc)
            errors.append({"document_id": source_id, "page": None,
                           "stage": "source", "error": str(exc)})
            continue
        for number in selected:
            progress += 1
            page_started = time.monotonic()
            label = f"[{progress}/{expected_pages}] {source_id} | PDF page {number}"
            LOGGER.info("%s | START", label)
            raw = None
            try:
                page = page_map[number]
                if not page["counted_as_useful"]:
                    raise ValueError("Selected page is not marked useful")
                if page["page_id"] in seen:
                    raise ValueError("Duplicate page_id")
                seen.add(page["page_id"])
                if not 1 <= number <= len(reader.pages):
                    raise ValueError("Page outside PDF bounds")
                raw = reader.pages[number - 1].extract_text() or ""
                text = normalize_page(raw, page["printed_page"], page["section"])
                if len(raw) != page["raw_char_count"] or len(text) != page["char_count"]:
                    raise ValueError("Character count differs from manifest")
                if digest(text) != page["normalized_text_sha256"]:
                    raise ValueError("Normalized text SHA-256 differs from manifest")
                LOGGER.info("%s | text OK | normalized characters=%d", label, len(text))
                record = {
                    "document_id": source_id,
                    "source": source["source_path_or_url"],
                    "page_id": page["page_id"],
                    "page": number,
                    "printed_page": page["printed_page"],
                    "section": page["section"],
                    "raw_text": raw,
                    "text": text,
                    "raw_char_count": len(raw),
                    "char_count": len(text),
                    "normalized_text_sha256": digest(text),
                }
                # Validate text-only manifest hashes before adding generated content.
                record["text_only"] = text
                record["text_only_char_count"] = len(text)
                record["text_only_sha256"] = digest(text)
                record["figures"] = []
                record["image_extraction_status"] = "complete"
                try:
                    images = list(reader.pages[number - 1].images)
                    record["image_count"] = len(images)
                    LOGGER.info("%s | images detected=%d", label, len(images))
                    for image_index, image in enumerate(images, 1):
                        image_started = time.monotonic()
                        LOGGER.info("%s | image [%d/%d] %s | START", label,
                                    image_index, len(images), image.name)
                        try:
                            figure = extractor.extract(image, raw, previous.get(page["page_id"], []))
                            record["figures"].append(figure)
                            LOGGER.info("%s | image %s | OK | elapsed=%.2fs", label,
                                        image.name, time.monotonic() - image_started)
                        except Exception as exc:
                            LOGGER.error("%s | image %s | FAILED | %s", label, image.name, exc)
                            record["image_extraction_status"] = "incomplete"
                            errors.append({"document_id": source_id, "page": number,
                                           "stage": "figure", "image_name": image.name,
                                           "error": str(exc)})
                except Exception as exc:
                    LOGGER.error("%s | image detection FAILED | %s", label, exc)
                    record["image_count"] = None
                    record["image_extraction_status"] = "incomplete"
                    errors.append({"document_id": source_id, "page": number,
                                   "stage": "image_detection", "error": str(exc)})
                record["blocks"], record["text"] = merge_figures(text, record["figures"])
                record["char_count"] = len(record["text"])
                record["normalized_text_sha256"] = digest(record["text"])
                records.append(record)
                # Checkpoint successful responses in the same file for resuming slow runs.
                output_dir.mkdir(parents=True, exist_ok=True)
                write_jsonl(output_dir / "pages.jsonl", records)
                LOGGER.info("%s | %s | saved | figures=%d | elapsed=%.2fs", label,
                            "OK" if record["image_extraction_status"] == "complete" else "INCOMPLETE",
                            len(record["figures"]), time.monotonic() - page_started)
            except Exception as exc:
                LOGGER.error("%s | FAILED | elapsed=%.2fs | %s", label,
                             time.monotonic() - page_started, exc)
                errors.append({"document_id": source_id, "page": number,
                               "stage": "page", "error": str(exc), "raw_text": raw})
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "pages.jsonl", records)
    write_jsonl(output_dir / "errors.jsonl", errors)
    summary = {
        "corpus_id": manifest["corpus_id"],
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "extractor": "pypdf",
        "extractor_version": importlib.metadata.version("pypdf"),
        "expected_pages": expected_pages,
        "saved_pages": len(records),
        "error_count": len(errors),
        "total_normalized_char_count": sum(row["char_count"] for row in records),
        "status": "complete" if not errors and len(records) == expected_pages else "incomplete",
        "ocr_used": False,
        "vision_model": model,
        "figure_extraction_method": "local_vlm_on_embedded_images",
        "image_count": sum(row.get("image_count") or 0 for row in records),
        "saved_figures": sum(len(row["figures"]) for row in records),
        "total_text_only_char_count": sum(row["text_only_char_count"] for row in records),
        "note": "Manifest text counts/hashes apply to text_only; merged text has separate counts/hashes in pages.jsonl.",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    LOGGER.info("RESULT | status=%s | saved pages=%d/%d | images=%d | saved figures=%d | errors=%d",
                summary["status"], len(records), expected_pages, summary["image_count"],
                summary["saved_figures"], len(errors))
    return 0 if summary["status"] == "complete" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--model", default="mimo-v2.6:9b-mxfp8")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=300, help="Timeout per Ollama request, seconds")
    args = parser.parse_args()
    raise SystemExit(read_corpus(args.manifest, args.output_dir, model=args.model,
                                ollama_url=args.ollama_url, timeout=args.timeout))


if __name__ == "__main__":
    main()
