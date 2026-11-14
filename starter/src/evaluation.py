"""Score single-chunk evidence retrieval against the frozen benchmark."""
from collections import defaultdict


def evaluate_query(question: dict, hits: list[dict]) -> dict:
    if len(hits) != 3 or len({h["chunk_id"] for h in hits}) != 3:
        raise ValueError("Expected three distinct ranked chunks")
    keys = ("gold_source_id", "gold_page", "evidence_quote")
    gold = [{k: q[k] for k in keys} for q in
            [question, *question.get("accepted_alternatives", [])]]
    labeled = []
    for rank, hit in enumerate(hits, 1):
        text = " ".join(hit["text"].split())
        matches = []
        for i, g in enumerate(gold):
            quote = " ".join(g["evidence_quote"].split())
            if not quote:
                raise ValueError("Empty gold evidence")
            if (hit["metadata"]["document_id"] == g["gold_source_id"]
                    and hit["metadata"]["page"] == g["gold_page"] and quote in text):
                matches.append(i)
        labeled.append(dict(hit, rank=rank, hit=bool(matches), matched_gold_indices=matches))
    return dict(question, gold=gold, hits=labeled, hit1=labeled[0]["hit"],
                evidence_hit3=any(h["hit"] for h in labeled))


def summarize(traces: list[dict]) -> dict:
    groups = defaultdict(list)
    for row in traces:
        groups[row["split"], row["strategy"]].append(row)
    summary = {}
    for (split, strategy), rows in groups.items():
        metrics = {}
        for key in ("hit1", "evidence_hit3"):
            count = sum(row[key] for row in rows)
            metrics[key] = dict(count=count, total=len(rows), rate=count / len(rows))
        summary.setdefault(split, {})[strategy] = metrics
    return summary
