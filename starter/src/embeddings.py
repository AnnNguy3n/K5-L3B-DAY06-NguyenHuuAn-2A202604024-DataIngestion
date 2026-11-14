"""Text retrieval with the locally installed EmbeddingGemma 2."""
import json
import math
from urllib.request import Request, urlopen

MODEL = "embeddinggemma-2:740m-mxfp8"
QUERY = "task: search result | query: "
DOCUMENT = "title: none | text: "
BATCH = 16


class MyEmbedder:
    def __init__(self, model_name: str = MODEL, url: str = "http://127.0.0.1:11434"):
        if model_name != MODEL:
            raise ValueError(f"Checkpoint requires {MODEL}")
        self.model_name = model_name
        self.url = url.rstrip("/")
        tags = self.request("tags")["models"]
        tag = next((row for row in tags if row["name"] == model_name), None)
        if not tag or "embedding" not in tag["capabilities"]:
            raise ValueError(f"Local embedding model unavailable: {model_name}")
        self.digest = tag["digest"]
        self.dimensions = tag["details"]["embedding_length"]
        probe = self._embed([QUERY + "project phases", DOCUMENT + "project phases"])
        self.info = dict(tag=tag, ollama=self.request("version")["version"],
                         query_prefix=QUERY, document_prefix=DOCUMENT,
                         probe_dimensions=[len(v) for v in probe], batch_size=BATCH,
                         truncate=False, dimensions_parameter=None)

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(f"{self.url}/api/{path}", data, {"Content-Type": "application/json"})
        with urlopen(req, timeout=180) as response:
            return json.load(response)

    def _embed(self, inputs):
        response = self.request("embed", dict(model=self.model_name, input=inputs, truncate=False))
        vectors = response["embeddings"]
        if response["model"] != self.model_name or len(vectors) != len(inputs):
            raise ValueError("Unexpected model or batch length from Ollama")
        for v in vectors:
            if len(v) != self.dimensions or not all(map(math.isfinite, v)) or not any(v):
                raise ValueError(f"Invalid vector for cosine search, received length {len(v)}")
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for start in range(0, len(texts), BATCH):
            vectors.extend(self._embed([DOCUMENT + t for t in texts[start:start+BATCH]]))
        return vectors

    def embed_query(self, question: str) -> list[float]:
        return self._embed([QUERY + question])[0]
