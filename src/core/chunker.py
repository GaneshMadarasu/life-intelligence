"""Date-aware smart chunker — respects sentence boundaries, tags chunks with detected dates."""

from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

DATE_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b"
    r"|"
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


class SmartChunker:
    def chunk(
        self,
        text: str,
        metadata: dict,
        chunk_size: int = 800,
        overlap: int = 150,
    ) -> list[dict[str, Any]]:
        if not text or not text.strip():
            return []

        sentences = SENTENCE_END.split(text)
        chunks: list[dict] = []
        current_chars: list[str] = []
        current_len = 0
        chunk_index = 0
        start_char = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            slen = len(sentence)

            if current_len + slen > chunk_size and current_chars:
                chunk_text = " ".join(current_chars)
                chunks.append(
                    self._make_chunk(
                        chunk_text, chunk_index, start_char, start_char + len(chunk_text), metadata
                    )
                )
                chunk_index += 1

                # overlap: keep last N chars worth of sentences
                overlap_sentences: list[str] = []
                overlap_len = 0
                for s in reversed(current_chars):
                    if overlap_len + len(s) > overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s)

                start_char = start_char + len(chunk_text) - overlap_len
                current_chars = overlap_sentences
                current_len = overlap_len

            current_chars.append(sentence)
            current_len += slen

        if current_chars:
            chunk_text = " ".join(current_chars)
            chunks.append(
                self._make_chunk(
                    chunk_text, chunk_index, start_char, start_char + len(chunk_text), metadata
                )
            )

        return chunks

    def _make_chunk(
        self,
        text: str,
        index: int,
        start: int,
        end: int,
        metadata: dict,
    ) -> dict[str, Any]:
        chunk_date = self._extract_dominant_date(text) or metadata.get("date") or metadata.get("doc_date")
        return {
            "text": text,
            "chunk_index": index,
            "start_char": start,
            "end_char": end,
            "chunk_date": chunk_date,
            "domain": metadata.get("domain", ""),
            "vertical": metadata.get("vertical", ""),
            "doc_id": metadata.get("doc_id", metadata.get("source_file", "")),
            "source_file": metadata.get("source_file", ""),
        }

    def _extract_dominant_date(self, text: str) -> str | None:
        matches = DATE_RE.findall(text)
        if not matches:
            return None
        # Return the first ISO-like date found, fall back to any match
        for m in matches:
            candidate = m[0] if m[0] else m[1] if len(m) > 1 else ""
            if candidate and re.match(r"\d{4}-\d{2}-\d{2}", candidate):
                return candidate
        flat = [m[0] or (m[1] if len(m) > 1 else "") for m in matches]
        return flat[0] if flat else None
