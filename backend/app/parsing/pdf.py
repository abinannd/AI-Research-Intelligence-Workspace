from __future__ import annotations

import statistics
from dataclasses import dataclass, field

import fitz

SCANNED_CHAR_THRESHOLD = 40


@dataclass
class PageText:
    page_number: int
    text: str
    headings: list[str] = field(default_factory=list)
    likely_scanned: bool = False


@dataclass
class ParsedPdf:
    page_count: int
    pages: list[PageText]


class PdfValidationError(ValueError):
    pass


def validate_pdf_bytes(data: bytes, filename: str, max_bytes: int, max_pages: int) -> int:
    name = (filename or "").lower()
    if not name.endswith(".pdf"):
        raise PdfValidationError("Only PDF files are accepted")
    if len(data) > max_bytes:
        raise PdfValidationError(f"PDF exceeds size limit of {max_bytes} bytes")
    if not data.startswith(b"%PDF"):
        raise PdfValidationError("File is not a valid PDF")
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise PdfValidationError("Could not open PDF") from exc
    try:
        pages = doc.page_count
        if pages < 1:
            raise PdfValidationError("PDF has no pages")
        if pages > max_pages:
            raise PdfValidationError(f"PDF exceeds page limit of {max_pages}")
        return pages
    finally:
        doc.close()


def _page_content(page: fitz.Page) -> PageText:
    data = page.get_text("dict")
    lines: list[tuple[float, str]] = []
    sizes: list[float] = []
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(s.get("text", "") for s in spans).strip()
            if not text:
                continue
            size = max((float(s.get("size", 0)) for s in spans), default=0.0)
            sizes.append(size)
            lines.append((size, text))
    median = statistics.median(sizes) if sizes else 0.0
    headings: list[str] = []
    texts: list[str] = []
    for size, text in lines:
        if median and size >= median * 1.25 and len(text) < 140:
            headings.append(text)
        texts.append(text)
    body = "\n".join(texts).strip()
    return PageText(
        page_number=page.number + 1,
        text=body,
        headings=headings,
        likely_scanned=len(body) < SCANNED_CHAR_THRESHOLD,
    )


def parse_pdf(data: bytes) -> ParsedPdf:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        pages = [_page_content(page) for page in doc]
        return ParsedPdf(page_count=doc.page_count, pages=pages)
    finally:
        doc.close()
