import re
import unicodedata
from pathlib import Path

import pymupdf

MAX_PAGES = 30
ALLOWED_EXT = {".pdf", ".txt"}
ALLOWED_MIME = {"application/pdf", "text/plain", "application/octet-stream"}


class DocumentError(Exception):
    """User-facing problem with an uploaded file."""


def clean_filename(name: str) -> str:
    """Display-only name. Never used for the stored path."""
    name = Path(name.replace("\\", "/")).name
    name = "".join(c for c in name if unicodedata.category(c)[0] != "C")
    return (name.strip() or "document")[:300]


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def validate_and_extract(filename: str, content_type: str | None, data: bytes) -> tuple[str, str, list[dict]]:
    """Returns (extension, normalized content_type, pages). Raises DocumentError."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise DocumentError(f"'{filename}': only PDF and TXT files are supported.")
    if (content_type or "").split(";")[0].strip().lower() not in ALLOWED_MIME:
        raise DocumentError(f"'{filename}': unexpected file type ({content_type}).")
    if not data:
        raise DocumentError(f"'{filename}' is empty.")

    if ext == ".pdf":
        if b"%PDF-" not in data[:1024]:
            raise DocumentError(f"'{filename}' is not a valid PDF.")
        return ext, "application/pdf", _extract_pdf(filename, data)
    return ext, "text/plain", _extract_txt(filename, data)


def _extract_pdf(filename: str, data: bytes) -> list[dict]:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise DocumentError(f"'{filename}' could not be read as a PDF.")
    with doc:
        if doc.needs_pass:
            raise DocumentError(f"'{filename}' is password-protected.")
        if doc.page_count > MAX_PAGES:
            raise DocumentError(f"'{filename}' has more than {MAX_PAGES} pages.")
        pages = [{"page": i + 1, "text": normalize(p.get_text())} for i, p in enumerate(doc)]
    if not any(p["text"] for p in pages):
        raise DocumentError(
            f"'{filename}' has no extractable text. It may be a scanned image (OCR is not supported yet)."
        )
    return pages


def _extract_txt(filename: str, data: bytes) -> list[dict]:
    if b"\x00" in data:
        raise DocumentError(f"'{filename}' does not look like a text file.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise DocumentError(f"'{filename}' must be UTF-8 text.")
    text = normalize(text)
    if not text:
        raise DocumentError(f"'{filename}' contains no text.")
    return [{"page": 1, "text": text}]