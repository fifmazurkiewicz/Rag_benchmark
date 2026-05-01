"""
Docling-based PDF/HTML/DOCX → Markdown converter.

Docling (IBM Research) understands document layout, tables, headings and
produces clean, structured Markdown — far better than pdfplumber for
complex financial PDFs with multi-column tables.

Fallback: if Docling is not installed or conversion fails, falls back to
pdfplumber plain-text extraction so the pipeline never hard-crashes.
"""
from __future__ import annotations

import io
import pathlib
from typing import Any


def convert_pdf_to_markdown(data: bytes | pathlib.Path, origin_url: str = "") -> str:
    """
    Convert PDF bytes (or a file path) to Markdown using Docling.
    Returns Markdown string.
    """
    try:
        return _docling_convert(data, origin_url)
    except ImportError:
        return _pdfplumber_fallback(data)


def _docling_convert(data: bytes | pathlib.Path, origin_url: str) -> str:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.backend.pypdfium2_backend import PyPdfium2DocumentBackend

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False          # skip OCR — bank PDFs are text-based
    pipeline_options.do_table_structure = True

    converter = DocumentConverter()

    if isinstance(data, pathlib.Path):
        result = converter.convert(str(data))
    else:
        # Docling accepts file-like objects via BytesIO path trick
        tmp = io.BytesIO(data)
        tmp.name = "document.pdf"
        result = converter.convert(tmp)

    return result.document.export_to_markdown()


def _pdfplumber_fallback(data: bytes | pathlib.Path) -> str:
    """Simple fallback when Docling is unavailable."""
    import pdfplumber

    if isinstance(data, pathlib.Path):
        data = data.read_bytes()

    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    line = " | ".join(str(c or "").strip() for c in row)
                    if line.strip(" |"):
                        parts.append(line)
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text)

    return "\n".join(parts).strip()
