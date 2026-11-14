"""Build both physical indexes or query the persisted indexes in a new process."""
import argparse
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import psycopg
from dotenv import load_dotenv

from .embeddings import MODEL, MyEmbedder
from .models import Chunk
from .store import PgVectorStore

STARTER = Path(__file__).resolve().parents[1]
RESULTS = STARTER / "results"
QUESTIONS = STARTER.parent / "benchmark/questions.jsonl"


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf8").splitlines()]


def write_output(name, data):
    path = RESULTS / name
    tmp = path.with_suffix(".tmp")
    tmp.write_text(data, encoding="utf8")
    tmp.replace(path)


def build(store, model):
    stats = {}
    for strategy in ("A", "B"):
        path = RESULTS / f"chunks_{strategy}.jsonl"
        chunks = [Chunk(**row) for row in read_rows(path)]
        start = perf_counter()
        vectors = model.embed_documents([c.text for c in chunks])
        embedded = perf_counter()
        removed = store.upsert(strategy, chunks, vectors)
        stats[strategy] = dict(chunks=len(chunks), removed=removed, embed_s=embedded-start,
                               write_s=perf_counter()-embedded,
                               input_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return stats


def retrieve(store, model):
    traces = []
    for row in read_rows(QUESTIONS):
        if row["split"] != "dev":
            continue
        question = row["question"]
        v = model.embed_query(question)
        by_strategy = {}
        for strategy in "ABC":
            filters = (row.get("filter") or {}) if strategy == "C" else {}
            hits = store.search(strategy, v, filters=filters)
            if len(hits) != 3 or any(h["metadata"].get(k) != val
                                     for h in hits for k, val in filters.items()):
                raise RuntimeError(f"Invalid dev top-3 for {row['id']} {strategy}")
            if strategy == "C" and not filters and hits != by_strategy["B"]:
                raise RuntimeError("Unfiltered C differs from B")
            by_strategy[strategy] = hits
            traces.append(dict(id=row["id"], split="dev", question=question, strategy=strategy,
                               filter=filters, hits=hits))
    return traces


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", choices=["build", "dev"], default="build")
    parser.add_argument("--label", choices=["initial", "reload", "restart"])
    args = parser.parse_args()
    label = args.label or args.mode
    start = perf_counter()
    load_dotenv(STARTER / ".env")
    model = MyEmbedder(os.getenv("EMBEDDING_MODEL") or MODEL)
    report = dict(mode=args.mode, pid=os.getpid(), utc=datetime.now(timezone.utc).isoformat(),
                  model=model.info, python=platform.python_version(), psycopg=psycopg.__version__,
                  metric="cosine", api_cost_usd=0, electricity_hardware_cost=None)
    with psycopg.connect(os.environ["DATABASE_URL"]) as db:
        store = PgVectorStore(db, model.dimensions, model.digest)
        if args.mode == "build":
            store.create_schema()
            report["ingestion"] = build(store, model)
        report["postgres"], report["pgvector"] = db.execute("""
            SELECT current_setting('server_version'), extversion FROM pg_extension WHERE extname='vector'
        """).fetchone()
        report["stored"] = db.execute("""
            SELECT strategy, count(*), count(distinct chunk_id), min(vector_dims(embedding)),
                   max(vector_dims(embedding)) FROM day6_chunks WHERE model_digest=%s
            GROUP BY strategy ORDER BY strategy
        """, (model.digest,)).fetchall()
        search_start = perf_counter()
        traces = retrieve(store, model)
        report["dev_seconds"] = perf_counter()-search_start
    output = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in traces)
    report.update(seconds=perf_counter()-start, dev_traces=len(traces),
                  trace_sha256=hashlib.sha256(output.encode()).hexdigest(),
                  filtered_C=sum(bool(t["filter"]) for t in traces if t["strategy"] == "C"))
    write_output("dev_top3.jsonl", output)
    write_output(f"checkpoint5_{label}.json", json.dumps(report, indent=2) + "\n")
    print(label, report["stored"], report["seconds"], report["trace_sha256"])


if __name__ == "__main__":
    main()
