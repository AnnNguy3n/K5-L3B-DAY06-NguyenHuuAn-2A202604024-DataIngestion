"""Select on cached dev evidence, then run held-out retrieval under that lock."""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from time import perf_counter

import psycopg
from dotenv import load_dotenv

from starter.src.embeddings import MODEL, MyEmbedder
from starter.src.evaluation import evaluate_query, summarize
from starter.src.run import QUESTIONS, RESULTS, STARTER, read_rows
from starter.src.store import PgVectorStore

ROOT = STARTER.parent
OUT = RESULTS / "checkpoint6"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    path = OUT / name
    if name.endswith(".jsonl"):
        value = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in data)
    else:
        value = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(value, encoding="utf8")
    tmp.replace(path)


def inputs():
    files = [QUESTIONS, ROOT / "BENCHMARK.md", ROOT / "data/manifest.json",
             RESULTS / "checkpoint5_initial.json", RESULTS / "dev_top3.jsonl",
             RESULTS / "pages.jsonl", OUT / "coherence_positions.json"]
    source = json.loads(files[2].read_text())["sources"][0]
    pdf = ROOT / source["source_path_or_url"]
    if sha(pdf) != source["snapshot"]["sha256"]:
        raise ValueError("Corpus changed")
    baseline = json.loads((RESULTS / "checkpoint5_initial.json").read_text())
    if sha(RESULTS / "dev_top3.jsonl") != baseline["trace_sha256"]:
        raise ValueError("Dev trace changed")
    for s in "AB":
        path = RESULTS / f"chunks_{s}.jsonl"
        if sha(path) != baseline["ingestion"][s]["input_sha256"]:
            raise ValueError("Chunk snapshot changed")
        files.append(path)
    files.extend([pdf, *(STARTER / "src" / f for f in
                 ("embeddings.py", "store.py", "evaluation.py")), ROOT / __file__])
    return {str(p.relative_to(ROOT)): sha(p) for p in files}


def scored(q, strategy, applied, hits):
    return dict(evaluate_query(q, hits), strategy=strategy, applied_filter=applied)


def select(questions):
    hashes = inputs()
    dev = {q["id"]: q for q in questions if q["split"] == "dev"}
    cached = read_rows(RESULTS / "dev_top3.jsonl")
    pairs = {(t["id"], t["strategy"]) for t in cached}
    if len(cached) != 45 or pairs != {(i, s) for i in dev for s in "ABC"}:
        raise ValueError("Incomplete dev trace")
    traces = []
    for t in cached:
        q, s = dev[t["id"]], t["strategy"]
        if (t["question"] != q["question"] or t["split"] != "dev"
                or t["filter"] != (q["filter"] if s == "C" else {})):
            raise ValueError("Dev inputs differ")
        traces.append(scored(q, s, t["filter"], t["hits"]))
    metrics = summarize(traces)
    scores = {s: (m["evidence_hit3"]["count"], m["hit1"]["count"])
              for s, m in metrics["dev"].items()}
    leaders = sorted(s for s in scores if scores[s] == max(scores.values()))
    times = None
    if len(leaders) > 1:
        rerun, times = retrieve(list(dev.values()))
        if {(t["id"], t["strategy"]): t["hits"] for t in rerun} != {
                (t["id"], t["strategy"]): t["hits"] for t in traces}:
            raise ValueError("Tie-break run differs from cached dev")
        leaders.sort(key=lambda s: (times["search_seconds"][s], s))
    write("dev_scored.jsonl", traces)
    write("dev_summary.json", metrics)
    write("selection_lock.json", dict(locked_utc=datetime.now(timezone.utc).isoformat(),
          selected=leaders[0], rule=["max dev evidence_hit3", "max dev hit1",
          "min dev retrieval seconds (shared query embedding)", "ascending strategy name"],
          metrics=metrics, dev_timing=times, sha256=hashes, top_k=3, metric="cosine",
          model=MODEL, dimensions=768, physical_indexes={"A":"A","B":"B","C":"B"}))


def retrieve(questions):
    baseline = json.loads((RESULTS / "checkpoint5_initial.json").read_text())
    load_dotenv(STARTER / ".env")
    model = MyEmbedder()
    if model.info != baseline["model"] or model.dimensions != 768:
        raise ValueError("Model configuration differs from checkpoint 5")
    traces = []
    seconds = dict.fromkeys("ABC", 0.)
    embedding_seconds = 0.
    with psycopg.connect(os.environ["DATABASE_URL"]) as db:
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        store = PgVectorStore(db, 768, model.digest)
        for s in "AB":
            expected = {c["chunk_id"]: (c["text"], dict(c["metadata"], document_id=c["document_id"],
                        source=c["source"], page=c["page"])) for c in read_rows(RESULTS / f"chunks_{s}.jsonl")}
            actual = db.execute("SELECT chunk_id,text,metadata FROM day6_chunks WHERE strategy=%s "
                                "AND model_digest=%s AND vector_dims(embedding)=768", (s,model.digest))
            if {i:(t,m) for i,t,m in actual} != expected:
                raise ValueError("Stored corpus differs from checkpoint 5")
        for q in questions:
            start = perf_counter()
            vector = model.embed_query(q["question"])
            embedding_seconds += perf_counter() - start
            for s in "ABC":
                applied = q["filter"] if s == "C" else {}
                start = perf_counter()
                hits = store.search(s, vector, filters=applied)
                seconds[s] += perf_counter() - start
                if s == "C" and not applied and hits != previous:
                    raise ValueError("Unfiltered C differs from B")
                previous = hits
                traces.append(scored(q,s,applied,hits))
    return traces, dict(search_seconds=seconds, shared_query_embedding_seconds=embedding_seconds,
                        local_api_usd=0, electricity_hardware_cost=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["select","test"])
    args = parser.parse_args()
    questions = read_rows(QUESTIONS)
    lock = OUT / "selection_lock.json"
    if args.mode == "select":
        if lock.exists():
            raise SystemExit("Selection already locked")
        select(questions)
    else:
        decision = json.loads(lock.read_text())
        if decision["sha256"] != inputs():
            raise ValueError("Locked inputs changed")
        traces, timing = retrieve([q for q in questions if q["split"] == "test"])
        write("test_scored.jsonl", traces)
        write("test_summary.json", dict(**summarize(traces), timing=timing,
              lock_sha256=sha(lock), finished_utc=datetime.now(timezone.utc).isoformat()))


if __name__ == "__main__":
    main()
