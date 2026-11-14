"""Exact cosine search over two full corpus snapshots in PostgreSQL."""
import json

from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .models import Chunk


class PgVectorStore:
    def __init__(self, connection, dimensions: int, model_digest: str):
        self.db = connection
        self.dimensions = dimensions
        self.digest = model_digest

    def create_schema(self):
        self.db.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS day6_chunks (
                strategy text NOT NULL CHECK (strategy IN ('A','B')),
                chunk_id text NOT NULL, text text NOT NULL, metadata jsonb NOT NULL,
                model_digest text NOT NULL, embedding vector({}) NOT NULL,
                PRIMARY KEY (strategy, chunk_id))
        """).format(sql.Literal(self.dimensions)))

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]):
        """Input is the complete snapshot for this physical strategy."""
        ids = [c.chunk_id for c in chunks]
        if strategy not in ("A", "B") or len(set(ids)) != len(ids) or len(ids) != len(vectors):
            raise ValueError("Invalid strategy, duplicate IDs or misaligned batch")
        rows = []
        for c, v in zip(chunks, vectors):
            if len(v) != self.dimensions:
                raise ValueError("Unexpected embedding dimension")
            meta = dict(c.metadata, document_id=c.document_id, source=c.source, page=c.page)
            rows.append((strategy, c.chunk_id, c.text, Jsonb(meta), self.digest,
                         json.dumps(v, allow_nan=False)))
        with self.db.transaction(), self.db.cursor() as cur:
            cur.execute("LOCK TABLE day6_chunks IN SHARE ROW EXCLUSIVE MODE")
            cur.executemany("""
                INSERT INTO day6_chunks (strategy,chunk_id,text,metadata,model_digest,embedding)
                VALUES (%s,%s,%s,%s,%s,%s::vector)
                ON CONFLICT (strategy,chunk_id) DO UPDATE SET text=excluded.text,
                    metadata=excluded.metadata, model_digest=excluded.model_digest,
                    embedding=excluded.embedding
            """, rows)
            cur.execute("DELETE FROM day6_chunks WHERE strategy=%s AND NOT (chunk_id=ANY(%s))",
                        (strategy, ids))
            return cur.rowcount

    def search(self, strategy, query_vector, top_k=3, filters=None):
        physical = {"A": "A", "B": "B", "C": "B"}[strategy]
        filters = filters or {}
        if filters and (strategy != "C" or filters.keys() - {"section", "language", "document_type"}):
            raise ValueError("Unexpected metadata filter")
        with self.db.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT chunk_id, text, metadata, 1 - (embedding <=> %s::vector) AS score
                FROM day6_chunks WHERE strategy=%s AND model_digest=%s AND metadata @> %s
                ORDER BY score DESC, chunk_id LIMIT %s
            """, (json.dumps(query_vector, allow_nan=False), physical, self.digest, Jsonb(filters), top_k))
            return cur.fetchall()
