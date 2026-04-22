import re

from ..models import PDFPageChunk


MIN_CHUNK_WORDS = 300
MAX_CHUNK_WORDS = 500
MIN_HARD_WORDS = 250
OVERLAP_SENTENCES = 2

TARGET_MIN_WORDS = 200
TARGET_MAX_WORDS = 500
MIN_FINAL_WORDS = 160


def _word_count(text):
    return len(str(text or "").split())


def _is_bullet_line(line):
    return bool(re.match(r"^\s*(?:[-*•]|\d+[\.)])\s+", str(line or "")))


def _is_code_line(line):
    stripped = str(line or "").strip()
    if not stripped:
        return False
    if stripped.startswith(("def ", "class ", "if ", "for ", "while ", "return ", "#include", "public ", "private ")):
        return True
    markers = ("{", "}", ";", "==", "!=", "<=", ">=", "->", "::", "()")
    return sum(1 for marker in markers if marker in stripped) >= 2


def _safe_split_long_unit(unit, max_words=MAX_CHUNK_WORDS):
    words = str(unit or "").split()
    if len(words) <= max_words:
        return [str(unit or "").strip()] if str(unit or "").strip() else []

    pieces = []
    clause_parts = [part.strip() for part in re.split(r"(?<=[,;:])\s+", str(unit or "")) if part.strip()]
    if len(clause_parts) > 1:
        buffer = []
        buffer_words = 0
        for clause in clause_parts:
            count = _word_count(clause)
            if buffer and (buffer_words + count) > max_words:
                pieces.append(" ".join(buffer).strip())
                buffer = [clause]
                buffer_words = count
            else:
                buffer.append(clause)
                buffer_words += count
        if buffer:
            pieces.append(" ".join(buffer).strip())
    else:
        start = 0
        while start < len(words):
            part = " ".join(words[start : start + max_words]).strip()
            if part:
                pieces.append(part)
            start += max_words
    return [piece for piece in pieces if piece]


def _sentence_records_from_pages(pages):
    records = []
    for page_number, page_text in enumerate(pages or [], start=1):
        line = " ".join(str(page_text or "").split()).strip()
        if not line:
            continue

        units = []
        if _is_bullet_line(line) or _is_code_line(line):
            units.extend(_safe_split_long_unit(line))
        else:
            sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", line) if part.strip()]
            if not sentences:
                units.extend(_safe_split_long_unit(line))
            else:
                for sentence in sentences:
                    units.extend(_safe_split_long_unit(sentence))

        for unit in units:
            text = str(unit or "").strip()
            if not text:
                continue
            records.append({"text": text, "page": page_number, "word_count": _word_count(text)})
    return records


def _paragraph_units_from_pages(pages):
    units = []
    for page_number, page_text in enumerate(pages or [], start=1):
        page_source = str(page_text or "")
        if not page_source.strip():
            continue

        paragraphs = [
            " ".join(part.split()).strip()
            for part in re.split(r"\n\s*\n+", page_source)
            if part and part.strip()
        ]
        if not paragraphs:
            paragraphs = [" ".join(page_source.split()).strip()]

        for paragraph in paragraphs:
            if not paragraph:
                continue
            paragraph_words = _word_count(paragraph)
            if paragraph_words > TARGET_MAX_WORDS:
                for piece in _safe_split_long_unit(paragraph, max_words=TARGET_MAX_WORDS):
                    text = piece.strip()
                    if text:
                        units.append({"text": text, "page": page_number, "word_count": _word_count(text)})
                continue
            units.append({"text": paragraph, "page": page_number, "word_count": paragraph_words})
    return units


def _build_global_chunk_records(pages):
    units = _paragraph_units_from_pages(pages)
    if not units:
        units = _sentence_records_from_pages(pages)
    if not units:
        return []

    records = []
    index = 0
    chunk_index = 0
    while index < len(units):
        current = []
        words = 0
        while index < len(units):
            next_item = units[index]
            if current and (words + next_item["word_count"]) > MAX_CHUNK_WORDS:
                break
            current.append(next_item)
            words += next_item["word_count"]
            index += 1
            if words >= TARGET_MIN_WORDS:
                break

        if not current:
            break

        chunk_text = " ".join(item["text"] for item in current).strip()
        if not chunk_text:
            continue

        if words < MIN_FINAL_WORDS and records and index < len(units):
            continue

        page_start = current[0]["page"]
        page_end = current[-1]["page"]
        records.append(
            {
                "chunk_index": chunk_index,
                "text_content": chunk_text,
                "word_count": _word_count(chunk_text),
                "page_start": page_start,
                "page_end": page_end,
                "page_number": page_start,
                "_sentences": current,
            }
        )
        chunk_index += 1

        if index >= len(units):
            break
        if len(current) > OVERLAP_SENTENCES:
            index = max(0, index - OVERLAP_SENTENCES)

    if len(records) >= 2 and records[-1]["word_count"] < MIN_FINAL_WORDS:
        merged_text = f"{records[-2]['text_content']} {records[-1]['text_content']}".strip()
        records[-2]["text_content"] = merged_text
        records[-2]["word_count"] = _word_count(merged_text)
        records[-2]["page_end"] = records[-1]["page_end"]
        records.pop()

    for idx, row in enumerate(records):
        row["chunk_index"] = idx
        row.pop("_sentences", None)
    return records


def create_chunks_for_pdf(reference_pdf, text=None, pages=None):
    PDFPageChunk.objects.filter(reference_pdf=reference_pdf).delete()

    if pages is None:
        raw = str(text or "")
        pages = [line.strip() for line in raw.split("\n") if line.strip()]

    records = _build_global_chunk_records(pages)

    if records and len(records) >= 2 and records[-1]["word_count"] < MIN_FINAL_WORDS:
        merged_text = f"{records[-2]['text_content']} {records[-1]['text_content']}".strip()
        records[-2]["text_content"] = merged_text
        records[-2]["word_count"] = _word_count(merged_text)
        records[-2]["page_end"] = records[-1]["page_end"]
        records.pop()

    rows = []
    subject_name = getattr(getattr(reference_pdf, "subject", None), "name", "") or ""
    unit_title = getattr(getattr(reference_pdf, "unit", None), "title", "") or ""
    subject_code = getattr(getattr(reference_pdf, "subject", None), "subject_code", "") or ""
    chunk_context_prefix = " ".join(part for part in [subject_name, subject_code, unit_title, reference_pdf.title] if part).strip()

    for record in records:
        content = record["text_content"]
        if chunk_context_prefix:
            content = f"{chunk_context_prefix}. {content}".strip()

        rows.append(
            PDFPageChunk(
                reference_pdf=reference_pdf,
                page_number=record["page_number"],
                chunk_index=record["chunk_index"],
                text_content=content,
                metadata={
                    "source": "document_text",
                    "word_count": record["word_count"],
                    "chunk_length": len(record["text_content"]),
                    "page_start": record["page_start"],
                    "page_end": record["page_end"],
                    "subject_id": getattr(reference_pdf, "subject_id", None),
                    "subject_name": subject_name,
                    "subject_code": subject_code,
                    "unit_id": getattr(reference_pdf, "unit_id", None),
                    "unit_title": unit_title,
                    "reference_pdf_id": getattr(reference_pdf, "id", None),
                },
            )
        )

    if rows:
        PDFPageChunk.objects.bulk_create(rows)
    return list(
        PDFPageChunk.objects.filter(reference_pdf=reference_pdf)
        .order_by("page_number", "chunk_index")
        .only("id", "reference_pdf_id", "page_number", "chunk_index", "text_content")
    )
