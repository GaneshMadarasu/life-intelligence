"""Universal document loader — PDF, DOCX, CSV, JSON, TXT, images (OCR), XML."""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATE_PATTERNS = [
    r"\b(\d{4}-\d{2}-\d{2})\b",
    r"\b(\d{1,2}/\d{1,2}/\d{4})\b",
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
    r"\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b",
]


class DocumentLoader:
    def load(self, file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        suffix = path.suffix.lower()
        dispatch = {
            ".pdf": self._load_pdf,
            ".docx": self._load_docx,
            ".doc": self._load_docx,
            ".csv": self._load_csv,
            ".json": self._load_json,
            ".txt": self._load_txt,
            ".md": self._load_txt,
            ".png": self._load_image,
            ".jpg": self._load_image,
            ".jpeg": self._load_image,
            ".tiff": self._load_image,
            ".xml": self._load_xml,
        }
        loader = dispatch.get(suffix, self._load_txt)
        result = loader(str(path))
        result["dates_detected"] = self._detect_dates(result.get("text", ""))
        return result

    def _load_pdf(self, path: str) -> dict:
        try:
            import pdfplumber
            pages_text = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    pages_text.append(text)
            full_text = "\n".join(pages_text)
            return {
                "text": full_text,
                "pages": len(pages_text),
                "file_type": "pdf",
                "metadata": {"source_file": path, "page_count": len(pages_text)},
            }
        except Exception as e:
            logger.warning("PDF load failed for %s: %s", path, e)
            return {"text": "", "pages": 0, "file_type": "pdf", "metadata": {"source_file": path}}

    def _load_docx(self, path: str) -> dict:
        try:
            from docx import Document
            doc = Document(path)
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            return {
                "text": text,
                "pages": 1,
                "file_type": "docx",
                "metadata": {"source_file": path},
            }
        except Exception as e:
            logger.warning("DOCX load failed for %s: %s", path, e)
            return {"text": "", "pages": 0, "file_type": "docx", "metadata": {"source_file": path}}

    def _load_csv(self, path: str) -> dict:
        try:
            import pandas as pd
            df = pd.read_csv(path)
            text = df.to_string(index=False)
            return {
                "text": text,
                "pages": 1,
                "file_type": "csv",
                "metadata": {"source_file": path, "rows": len(df), "columns": list(df.columns)},
            }
        except Exception as e:
            logger.warning("CSV load failed for %s: %s", path, e)
            return {"text": "", "pages": 0, "file_type": "csv", "metadata": {"source_file": path}}

    def _load_json(self, path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            text = json.dumps(data, indent=2)
            return {
                "text": text,
                "pages": 1,
                "file_type": "json",
                "metadata": {"source_file": path},
                "raw": data,
            }
        except Exception as e:
            logger.warning("JSON load failed for %s: %s", path, e)
            return {"text": "", "pages": 0, "file_type": "json", "metadata": {"source_file": path}}

    def _load_txt(self, path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            return {
                "text": text,
                "pages": 1,
                "file_type": "txt",
                "metadata": {"source_file": path},
            }
        except Exception as e:
            logger.warning("TXT load failed for %s: %s", path, e)
            return {"text": "", "pages": 0, "file_type": "txt", "metadata": {"source_file": path}}

    def _load_image(self, path: str) -> dict:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(path)
            text = pytesseract.image_to_string(img)
            return {
                "text": text,
                "pages": 1,
                "file_type": "image",
                "metadata": {"source_file": path},
            }
        except Exception as e:
            logger.warning("Image OCR failed for %s: %s", path, e)
            return {"text": "", "pages": 0, "file_type": "image", "metadata": {"source_file": path}}

    def _load_xml(self, path: str) -> dict:
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            parts: list[str] = []
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    parts.append(f"{elem.tag}: {elem.text.strip()}")
            text = "\n".join(parts)
            return {
                "text": text,
                "pages": 1,
                "file_type": "xml",
                "metadata": {"source_file": path},
            }
        except Exception as e:
            logger.warning("XML load failed for %s: %s", path, e)
            return {"text": "", "pages": 0, "file_type": "xml", "metadata": {"source_file": path}}

    def _detect_dates(self, text: str) -> list[str]:
        dates: list[str] = []
        for pattern in DATE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches if isinstance(matches[0], str) else [m[0] for m in matches] if matches else [])
        return list(dict.fromkeys(dates))  # deduplicate preserving order
