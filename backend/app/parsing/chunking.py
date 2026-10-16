from __future__ import annotations

from dataclasses import dataclass

from app.parsing.pdf import PageText


@dataclass
class ChunkDraft:
    page_number: int
    heading: str | None
    text: str


def _split_windows(text: str, size: int, overlap: int) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if len(cleaned) <= size:
        return [cleaned]
    windows: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        windows.append(cleaned[start:end].strip())
        if end >= len(cleaned):
            break
        start = max(0, end - overlap)
    return [w for w in windows if w]


def chunk_pages(pages: list[PageText], size: int = 1200, overlap: int = 180) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    last_heading: str | None = None
    for page in pages:
        if page.likely_scanned or not page.text.strip():
            continue
        heading = page.headings[0] if page.headings else last_heading
        if page.headings:
            last_heading = page.headings[-1]
        for window in _split_windows(page.text, size=size, overlap=overlap):
            drafts.append(ChunkDraft(page_number=page.page_number, heading=heading, text=window))
    return drafts
