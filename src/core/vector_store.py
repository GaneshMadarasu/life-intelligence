"""ChromaDB vector store — partitioned by domain+vertical."""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_store_instance: "VectorStore | None" = None


class VectorStore:
    def __init__(self, host: str = "localhost", port: int = 8001, persist_dir: str = "./data/chroma_db") -> None:
        self.host = host
        self.port = port
        self.persist_dir = persist_dir
        self._client = None
        self._collections: dict[str, Any] = {}

    def _get_client(self):
        if self._client is None:
            import chromadb
            try:
                self._client = chromadb.HttpClient(host=self.host, port=self.port)
                self._client.heartbeat()
                logger.info("Connected to ChromaDB at %s:%s", self.host, self.port)
            except Exception:
                logger.warning("ChromaDB HTTP unavailable, using persistent local client")
                self._client = chromadb.PersistentClient(path=self.persist_dir)
        return self._client

    def get_or_create_collection(self, domain: str, vertical: str):
        key = f"{domain}_{vertical}"
        if key not in self._collections:
            client = self._get_client()
            self._collections[key] = client.get_or_create_collection(
                name=key,
                metadata={"domain": domain, "vertical": vertical},
            )
        return self._collections[key]

    def add_chunks(self, chunks: list[dict], domain: str, vertical: str) -> None:
        if not chunks:
            return
        collection = self.get_or_create_collection(domain, vertical)
        ids = [f"{domain}_{vertical}_{c['doc_id']}_{c['chunk_index']}" for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {
                "domain": c.get("domain", domain),
                "vertical": c.get("vertical", vertical),
                "chunk_date": c.get("chunk_date") or "",
                "source_file": c.get("source_file", ""),
                "doc_id": str(c.get("doc_id", "")),
            }
            for c in chunks
        ]
        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            collection.upsert(
                ids=ids[i : i + batch_size],
                documents=documents[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )
        logger.info("Added %d chunks to %s_%s", len(chunks), domain, vertical)

    def search(
        self, query: str, domain: str, vertical: str, top_k: int = 5
    ) -> list[dict]:
        try:
            collection = self.get_or_create_collection(domain, vertical)
            results = collection.query(query_texts=[query], n_results=min(top_k, collection.count() or 1))
            return self._format_results(results)
        except Exception as e:
            logger.warning("Vector search failed for %s/%s: %s", domain, vertical, e)
            return []

    def search_across_domains(
        self, query: str, domains: list[str], top_k: int = 10
    ) -> list[dict]:
        all_results: list[dict] = []
        for key, collection in self._collections.items():
            dom, vert = key.split("_", 1)
            if "all" in domains or dom in domains:
                try:
                    count = collection.count()
                    if count == 0:
                        continue
                    results = collection.query(
                        query_texts=[query], n_results=min(top_k, count)
                    )
                    formatted = self._format_results(results)
                    for r in formatted:
                        r["domain"] = dom
                        r["vertical"] = vert
                    all_results.extend(formatted)
                except Exception as e:
                    logger.warning("Cross-domain search error in %s: %s", key, e)
        all_results.sort(key=lambda x: x.get("distance", 1.0))
        return all_results[:top_k]

    def get_collection_stats(self, domain: str, vertical: str) -> dict:
        try:
            collection = self.get_or_create_collection(domain, vertical)
            return {"domain": domain, "vertical": vertical, "count": collection.count()}
        except Exception:
            return {"domain": domain, "vertical": vertical, "count": 0}

    def _format_results(self, raw_results: dict) -> list[dict]:
        out: list[dict] = []
        docs = raw_results.get("documents", [[]])[0]
        metas = raw_results.get("metadatas", [[]])[0]
        distances = raw_results.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, distances):
            out.append({"text": doc, "metadata": meta, "distance": dist, "score": 1 - dist})
        return out


def get_vector_store() -> VectorStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = VectorStore(
            host=os.getenv("CHROMA_HOST", "localhost"),
            port=int(os.getenv("CHROMA_PORT", "8001")),
            persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db"),
        )
    return _store_instance
