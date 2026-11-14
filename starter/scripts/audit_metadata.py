"""Compare every returned test rank with the manifest and indexed page snapshot."""
import json
from collections import defaultdict

from pypdf import PdfReader

from .checkpoint6 import OUT, RESULTS, ROOT, read_rows, write


def main():
    manifest = json.loads((ROOT / "data/manifest.json").read_text())["sources"][0]
    source_pages = {p["page"]: p for p in manifest["pages"]}
    pages = {p["page"]: p for p in read_rows(RESULTS / "pages.jsonl")}
    pdf = PdfReader(ROOT / manifest["source_path_or_url"])
    raw = {n: " ".join(pdf.pages[n-1].extract_text().split()) for n in source_pages}
    audit = []
    filters = defaultdict(list)
    for trace in read_rows(OUT / "test_scored.jsonl"):
        compliance = []
        for hit in trace["hits"]:
            m = hit["metadata"]
            page = source_pages.get(m.get("page"), {})
            expected = dict(document_id=manifest["source_id"], source=manifest["source_path_or_url"],
                            language=manifest["language"], document_type=manifest["document_type"])
            expected.update({key: page.get(key) for key in ("page_id", "section", "printed_page")})
            errors = [k for k,v in expected.items() if v is None or m.get(k) != v]
            start, end = m.get("char_start"), m.get("char_end")
            text = pages.get(m.get("page"), {}).get("text", "")
            if not (isinstance(start,int) and isinstance(end,int) and 0 <= start < end <= len(text)
                    and text[start:end] == hit["text"]):
                errors.append("page/text offsets")
            words = hit["text"].split()
            width = min(len(words), 8)
            excerpts = (" ".join(words[i:i+width]) for i in range(len(words)-width+1))
            witness = next((w for w in excerpts if w and w in raw.get(m.get("page"), "")), None)
            if witness is None:
                errors.append("PDF excerpt needs review")
            requested = trace["filter"]
            matches = all(m.get(k) == v for k,v in requested.items()) if requested else None
            compliance.append(matches)
            audit.append(dict(id=trace["id"], strategy=trace["strategy"], rank=hit["rank"],
                         chunk_id=hit["chunk_id"], page=m.get("page"), expected=expected, pdf_excerpt=witness,
                         char_start=start,char_end=end, errors=errors, compliant=matches))
        if trace["filter"]:
            filters[trace["strategy"]].append(all(compliance))
    write("metadata.jsonl", audit)
    summary = {}
    for s in "ABC":
        rows = [r for r in audit if r["strategy"] == s]
        summary[s] = dict(correct=sum(not r["errors"] for r in rows), total=len(rows),
                          filter_pass=sum(filters[s]), filter_total=len(filters[s]),
                          filter_rate=sum(filters[s])/len(filters[s]) if filters[s] else None)
    write("metadata_summary.json", summary)


if __name__ == "__main__":
    main()
