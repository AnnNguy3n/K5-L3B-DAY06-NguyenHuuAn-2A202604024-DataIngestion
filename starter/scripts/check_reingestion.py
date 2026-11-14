"""Integration check in a session-local table using real chunks and embeddings."""
import json
import os
from dataclasses import replace

import psycopg
from dotenv import load_dotenv

from starter.src.embeddings import MyEmbedder
from starter.src.models import Chunk
from starter.src.run import RESULTS, STARTER, read_rows
from starter.src.store import PgVectorStore


def main():
    load_dotenv(STARTER / ".env")
    model = MyEmbedder()
    first, second = [Chunk(**r) for r in read_rows(RESULTS / "chunks_A.jsonl")[:2]]
    # Simulate a correction at the same source position and deletion of the other chunk.
    corrected = replace(first, text=first.text.rstrip(".") + ".")
    if corrected.text == first.text:
        corrected = replace(first, text=first.text + " (revised)")
    v1, v2, revised = model.embed_documents([first.text, second.text, corrected.text])
    with psycopg.connect(os.environ["DATABASE_URL"]) as db:
        db.execute("CREATE TEMP TABLE day6_chunks (LIKE public.day6_chunks INCLUDING ALL)")
        store = PgVectorStore(db, model.dimensions, model.digest)
        store.upsert("A", [first, second], [v1, v2])
        store.upsert("B", [second], [v2])
        deleted = store.upsert("A", [corrected], [revised])
        found = store.search("A", revised)
        sibling = store.search("B", v2)
        if (deleted != 1 or len(found) != 1 or found[0]["chunk_id"] != first.chunk_id
                or found[0]["text"] != corrected.text or found[0]["score"] < 0.999999
                or len(sibling) != 1 or sibling[0]["chunk_id"] != second.chunk_id):
            raise RuntimeError("Snapshot replacement failed")
        print(json.dumps(dict(temporary_table=True, removed=deleted, retained_id=first.chunk_id,
                              revised_text_matches=True, revised_vector_cosine=found[0]["score"],
                              other_strategy_unchanged=True), indent=2))


if __name__ == "__main__":
    main()
