"""Export ingestion and initial A/B chunks, without running retrieval evaluation.

Run from the repository root: python -m starter.src.prepare
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import logging
import statistics
from pathlib import Path

from .chunking import by_paragraph, fixed_size
from .ingestion import load_pdf

ROOT = Path(__file__).resolve().parents[2]


def write_jsonl(path: Path, records) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    temporary.replace(path)


def prepare(manifest_path: Path, output_dir: Path, *, cache_path: Path | None = None,
            size: int = 500, overlap: int = 50, max_size: int = 1000, long_overlap: int = 100,
            model: str = "mimo-v2.6:9b-mxfp8",
            ollama_url: str = "http://127.0.0.1:11434", timeout: float = 300) -> dict:
    # Validate configuration before performing any PDF/vision work.
    from .models import DocumentPage
    empty = DocumentPage("", "", 1, "")
    fixed_size(empty, size, overlap)
    by_paragraph(empty, max_size, long_overlap)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("path_base") != "repository_root":
        raise ValueError("Manifest path_base must be repository_root")
    cache = {}
    if cache_path is not None and cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            cache[(row["document_id"], row["source"], row["page"])] = row.get(
                "figures", row.get("metadata", {}).get("figures", []))
    output_dir.mkdir(parents=True, exist_ok=True)
    pages, errors, source_stats = [], [], []
    for source in manifest["sources"]:
        document_id = source["source_id"]
        source_path = source["source_path_or_url"]
        selected = source["selected_pdf_pages"]
        stats = {"document_id": document_id, "total_pages": len(selected),
                 "attempted_pages": 0, "saved_pages": 0, "error_count": 0,
                 "empty_pages": 0, "image_count": 0, "saved_figures": 0}
        try:
            pdf_path = ROOT / source_path
            if hashlib.sha256(pdf_path.read_bytes()).hexdigest() != source["snapshot"]["sha256"]:
                raise ValueError("PDF SHA-256 differs from manifest")
            page_map = {p["page"]: {key: p[key] for key in
                        ("page_id", "section", "printed_page") if key in p}
                        for p in source["pages"]}
            if len(page_map) != len(source["pages"]) or set(page_map) != set(selected):
                raise ValueError("Page metadata must match selected_pdf_pages exactly")
            if any(not p["counted_as_useful"] for p in source["pages"]):
                raise ValueError("Selected pages must be marked useful")
            pages.extend(load_pdf(
                pdf_path, document_id, source_path, page_numbers=selected,
                metadata={key: source[key] for key in
                          ("title", "language", "document_type") if key in source},
                page_metadata=page_map, errors=errors, stats=stats,
                previous_figures={number: cache.get((document_id, source_path, number), [])
                                  for number in selected},
                model=model, ollama_url=ollama_url, timeout=timeout))
        except Exception as exc:
            errors.append(dict(document_id=document_id, source=source_path,
                               page=None, stage="source", error=str(exc)))
            stats["error_count"] += 1
            stats["status"] = "incomplete"
        source_stats.append(stats)
    chunks_a = [chunk for page in pages for chunk in fixed_size(page, size, overlap)]
    chunks_b = [chunk for page in pages for chunk in by_paragraph(page, max_size, long_overlap)]
    write_jsonl(output_dir / "pages.jsonl", (asdict(page) for page in pages))
    write_jsonl(output_dir / "ingestion_errors.jsonl", errors)
    write_jsonl(output_dir / "chunks_A.jsonl", (asdict(chunk) for chunk in chunks_a))
    write_jsonl(output_dir / "chunks_B.jsonl", (asdict(chunk) for chunk in chunks_b))
    summary = {
        "corpus_id": manifest["corpus_id"],
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "total_pages": sum(len(s["selected_pdf_pages"]) for s in manifest["sources"]),
        "saved_pages": len(pages), "error_count": len(errors),
        "empty_pages": sum(s["empty_pages"] for s in source_stats),
        "image_count": sum(s["image_count"] for s in source_stats),
        "saved_figures": sum(s["saved_figures"] for s in source_stats),
        "vision_model": model, "sources": source_stats,
        "status": "complete" if not errors else "incomplete",
        "chunk_size_stats": {
            name: {"min": min(lengths, default=0),
                   "median": statistics.median(lengths) if lengths else 0,
                   "max": max(lengths, default=0),
                   "below_200_chars": sum(length < 200 for length in lengths)}
            for name, lengths in (("A", [len(c.text) for c in chunks_a]),
                                  ("B", [len(c.text) for c in chunks_b]))
        },
        "configurations": {
            "A": {"method": "fixed_size", "size": size, "overlap": overlap,
                  "filter": None, "chunks": len(chunks_a)},
            "B": {"method": "by_paragraph", "max_size": max_size,
                  "long_overlap": long_overlap, "overlap_scope": "long_paragraph_only",
                  "filter": None, "chunks": len(chunks_b)},
            "C": {"chunks_file": "chunks_B.jsonl", "filter": "question.filter when present"},
        },
        "note": "Initial parameters; not optimized on dev. Retrieval evaluation is a separate step.",
    }
    (output_dir / "ingestion_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "starter/results")
    parser.add_argument("--cache", type=Path, default=ROOT / "data/processed/pages.jsonl")
    parser.add_argument("--size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=50)
    parser.add_argument("--max-size", type=int, default=1000)
    parser.add_argument("--long-overlap", type=int, default=100)
    parser.add_argument("--model", default="mimo-v2.6:9b-mxfp8")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    summary = prepare(args.manifest, args.output_dir, cache_path=args.cache,
                      size=args.size, overlap=args.overlap, max_size=args.max_size, long_overlap=args.long_overlap,
                      model=args.model, ollama_url=args.ollama_url, timeout=args.timeout)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(0 if summary["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
