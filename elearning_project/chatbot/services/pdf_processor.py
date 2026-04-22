import re
from collections import Counter

import fitz
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import PDFPageChunk
from courses.models import Unit


MIN_PARAGRAPH_CHARS = 80

UNIT_HEADING_REGEX = re.compile(
    r"(?im)^\s*unit\s*[-:]?\s*(?P<label>\d{1,2}|[ivxlcdm]+)\s*(?:[:\-\.)]\s*(?P<title>[^\n\r]{0,180}))?\s*$"
)

ROMAN_MAP = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
}

HEADER_FOOTER_PATTERNS = [
    r"^page\s*\d+(?:\s*of\s*\d+)?$",
    r"^unit\s*\d+[a-z]?(?:\s*[:\-].*)?$",
    r"\blovely\s+professional\s+university\b",
    r"\b\w+\s+university\b",
    r"^\s*\d+\s*$",
    r"^\s*page\s*\d+\s*/\s*\d+\s*$",
    r"^\s*\d+\s*/\s*\d+\s*$",
]


def _looks_low_quality_text(text: str) -> bool:
    sample = (text or "").strip()
    if len(sample) < 100:
        return True
    non_space = [char for char in sample if not char.isspace()]
    if not non_space:
        return True
    noisy_chars = sum(
        1
        for char in non_space
        if not (char.isalnum() or char in ".,;:!?()[]{}'\"/%+-=&")
    )
    return (noisy_chars / max(1, len(non_space))) > 0.15


def _unit_number_from_label(label: str):
    raw = (label or "").strip().lower()
    if not raw:
        return None
    if raw.isdigit():
        number = int(raw)
    else:
        number = ROMAN_MAP.get(raw)
    if not number or number < 1 or number > 5:
        return None
    return number


def _extract_unit_sections_from_raw_text(raw_text: str):
    text = (raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
    matches = list(UNIT_HEADING_REGEX.finditer(text))
    if not matches:
        return {}

    sections = {}
    for index, match in enumerate(matches):
        unit_number = _unit_number_from_label(match.group("label"))
        if not unit_number:
            continue

        heading_title = (match.group("title") or "").strip(" :-\t")
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content_raw = text[start:end].strip()
        content = clean_text(content_raw)
        if len(content) < MIN_PARAGRAPH_CHARS:
            continue

        current = sections.get(unit_number)
        if current is None or len(content) > len(current.get("content", "")):
            sections[unit_number] = {
                "title": heading_title or f"Unit {unit_number}",
                "content": content,
            }
    return sections


def extract_unit_sections_from_pdf(pdf_path):
    document = fitz.open(pdf_path)
    try:
        raw_pages = []
        for page in document:
            try:
                raw_pages.append(page.get_text() or "")
            except Exception as e:
                print("ERROR:", str(e))
                raw_pages.append("")
        raw_text = "\n".join(raw_pages)
    finally:
        document.close()

    return _extract_unit_sections_from_raw_text(raw_text)


def upsert_units_from_pdf(reference_pdf_instance, unit_sections, replace_existing=True):
    if not getattr(settings, "ENABLE_PDF_TO_LESSON", False):
        return 0

    subject = getattr(reference_pdf_instance, "subject", None)
    if not subject or not unit_sections:
        return 0

    saved = 0
    for unit_number in sorted(unit_sections.keys()):
        if unit_number < 1 or unit_number > 5:
            continue
        payload = unit_sections[unit_number]
        Unit.objects.update_or_create(
            subject=subject,
            unit_number=unit_number,
            defaults={
                "title": payload.get("title") or f"Unit {unit_number}",
                "content": payload.get("content") or "",
                "is_active": True,
            },
        )
        saved += 1

    Unit.objects.filter(subject=subject, unit_number__gt=5).delete()
    return saved


def _is_header_or_footer_line(line: str) -> bool:
    candidate = (line or "").strip().lower()
    if not candidate:
        return True
    return any(re.search(pattern, candidate, flags=re.IGNORECASE) for pattern in HEADER_FOOTER_PATTERNS)


def _normalize_line_noise(line: str) -> str:
    cleaned = re.sub(r"[^\w\s\.,;:!?()\[\]/%+\-]", " ", line or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def clean_text(text: str) -> str:
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u00ad", "")
    normalized = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", normalized)

    lines = []

    for raw_line in normalized.split("\n"):
        line = _normalize_line_noise(raw_line)
        if not line:
            continue
        if _is_header_or_footer_line(line):
            continue
        lines.append(line)

    cleaned = " ".join(lines)
    cleaned = re.sub(r"\s+([\.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _remove_repeated_page_margins(raw_pages):
    pages = [str(page or "") for page in (raw_pages or [])]
    if len(pages) < 3:
        return pages

    edge_counter = Counter()
    page_edges = []
    for page in pages:
        lines = [line.strip() for line in page.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
        top = lines[:2]
        bottom = lines[-2:] if len(lines) >= 2 else lines
        page_edges.append((lines, top, bottom))
        for line in top + bottom:
            canonical = re.sub(r"\s+", " ", line.lower()).strip()
            if canonical:
                edge_counter[canonical] += 1

    threshold = max(2, int(len(pages) * 0.4))
    repeated = {line for line, count in edge_counter.items() if count >= threshold}
    if not repeated:
        return pages

    cleaned_pages = []
    for lines, _top, _bottom in page_edges:
        filtered = []
        for line in lines:
            canonical = re.sub(r"\s+", " ", line.lower()).strip()
            if canonical in repeated:
                continue
            filtered.append(line)
        cleaned_pages.append("\n".join(filtered))
    return cleaned_pages


def clean_page_text(text: str) -> str:
    return clean_text(text)


def split_page_into_paragraph_chunks(text: str):
    cleaned = clean_text(text)
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    chunks = [part.strip() for part in parts if len(part.strip()) >= 20]
    return chunks or [cleaned]


def _extract_page_images(reference_pdf_instance, pdf_path):
    return []


def _page_text(page):
    try:
        raw_text = page.get_text() or ""
    except Exception as e:
        print("ERROR:", str(e))
        raw_text = ""
    if raw_text.strip() and not _looks_low_quality_text(raw_text):
        return raw_text
    return raw_text


def extract_text_from_pdf(pdf_path):
    pages = []
    document = fitz.open(pdf_path)
    try:
        for page in document:
            raw_text = _page_text(page)
            pages.append(raw_text)
        pages = _remove_repeated_page_margins(pages)
        cleaned_pages = []
        for raw_text in pages:
            cleaned_page = clean_text(raw_text)
            if cleaned_page:
                cleaned_pages.append(cleaned_page)
    finally:
        document.close()
    return cleaned_pages


def process_pdf(reference_pdf_instance, replace_existing=True):
    """Extract clean text only from an uploaded PDF (no OCR/chunking/embedding)."""
    pdf_path = reference_pdf_instance.file.path
    reference_pdf_instance.processing_status = reference_pdf_instance.ProcessingStatus.PROCESSING
    reference_pdf_instance.processing_error = ""
    reference_pdf_instance.save(
        update_fields=["processing_status", "processing_error"]
    )

    try:
        with transaction.atomic():
            if replace_existing:
                PDFPageChunk.objects.filter(reference_pdf=reference_pdf_instance).delete()
            pages = extract_text_from_pdf(pdf_path)
            unit_sections = (
                extract_unit_sections_from_pdf(pdf_path)
                if getattr(settings, "ENABLE_PDF_TO_LESSON", False)
                else {}
            )
            extracted_text = "\n".join(pages)
            chunk_count = PDFPageChunk.objects.filter(reference_pdf=reference_pdf_instance).count()
            diagram_count = 0
            if getattr(settings, "ENABLE_PDF_TO_LESSON", False):
                upsert_units_from_pdf(reference_pdf_instance, unit_sections, replace_existing=replace_existing)
            reference_pdf_instance.extracted_text = extracted_text
            reference_pdf_instance.chunk_count = chunk_count
            reference_pdf_instance.diagram_count = diagram_count
            reference_pdf_instance.last_processed_at = timezone.now()
            if extracted_text.strip():
                reference_pdf_instance.processing_status = reference_pdf_instance.ProcessingStatus.READY
                reference_pdf_instance.processing_error = ""
            else:
                reference_pdf_instance.processing_status = reference_pdf_instance.ProcessingStatus.FAILED
                reference_pdf_instance.processing_error = (
                    "No extractable text was found in the PDF."
                )
            reference_pdf_instance.save(
                update_fields=[
                    "extracted_text",
                    "chunk_count",
                    "diagram_count",
                    "last_processed_at",
                    "processing_status",
                    "processing_error",
                ]
            )
    except Exception as exc:
        reference_pdf_instance.processing_status = reference_pdf_instance.ProcessingStatus.FAILED
        reference_pdf_instance.processing_error = str(exc)
        reference_pdf_instance.last_processed_at = timezone.now()
        reference_pdf_instance.save(
            update_fields=["processing_status", "processing_error", "last_processed_at"]
        )
        raise
