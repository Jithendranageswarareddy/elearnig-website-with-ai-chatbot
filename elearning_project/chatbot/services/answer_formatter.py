import re

COURSE_CODE_PATTERN = re.compile(r"\b\d{2}[A-Z]{2,}\d[A-Z]\d{2}\b")
HEADING_PREFIX_PATTERNS = (
    r"(?i)^(applications|characteristics|advantages|disadvantages|features|examples)\s+(?=[A-Z])",
    r"(?i)^(phases of [A-Za-z][A-Za-z\s&/-]{1,60})\s+(?=[A-Z])",
    r"(?i)^(types of [A-Za-z][A-Za-z\s&/-]{1,60})\s+(?=[A-Z])",
    r"(?i)^(classification algorithms|evaluation metrics|energy flow in ecosystems)\s+(?=[A-Z])",
)

VERB_HINT_PATTERN = re.compile(
    r"(?i)\b("
    r"is|are|was|were|be|being|been|has|have|had|"
    r"do|does|did|can|could|will|would|shall|should|may|might|must|"
    r"use|uses|used|using|provide|provides|provided|providing|"
    r"manage|manages|managed|managing|allocate|allocates|allocated|allocating|"
    r"process|processes|processed|processing|run|runs|running|"
    r"(?:[A-Za-z]{4,}(?:ed|ing))"
    r")\b"
)


def _clean_text(value):
    text = str(value or "").strip()
    text = text.replace("\u00ad", "")
    text = COURSE_CODE_PATTERN.sub(" ", text)
    text = re.sub(r"(?i)\bis a syllabus concept in which\b", "is", text)
    text = re.sub(r"(?i)\bthis unit covers\b", "", text)
    text = re.sub(r"(?i)\bseed\s+content\b", "", text)
    text = re.sub(r"(?i)\bdetailed\s+explanation\b", "", text)
    text = re.sub(r"(?i)\bexact match is limited\b", "", text)
    text = re.sub(r"(?i)\bpartial syllabus context\b", "", text)
    text = re.sub(r"(?i)\bthis response is grounded[^.?!]*[.?!]?", "", text)
    text = re.sub(r"(?i)\bthe key point is\b", "", text)
    text = re.sub(r"(?i)\b(summary|introduction|workflow)\b\s*[:\-]?\s*", "", text)
    for pattern in HEADING_PREFIX_PATTERNS:
        text = re.sub(pattern, "", text)
    text = re.sub(r"-\s+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"\b(\w+)\s+\1\b", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\.(\s*\.)+", ".", text)
    return text.strip()


def _polish_sentence(value, fallback):
    text = _clean_text(value) or fallback
    if not text:
        return fallback
    if text and text[-1] not in ".!?":
        text = f"{text}."
    text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    return text


def _is_good_phrase(text):
    sentence = _clean_text(text)
    if len(sentence.split()) < 5:
        return False
    if not VERB_HINT_PATTERN.search(sentence):
        return False
    return True


def _limit_sentences(text, max_sentences=6):
    source = str(text or "").strip()
    if not source:
        return source
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", source) if part.strip()]
    limited = parts[: max(1, int(max_sentences))]
    merged = " ".join(limited)
    return _polish_sentence(merged, source)


def _sentence_list(text):
    source = str(text or "").strip()
    if not source:
        return []
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", source) if part.strip()]
    if len(parts) <= 1 and len(source.split()) > 40:
        expanded = re.sub(
            r"(?<!^)\s+(?=(for example|for instance|applications|characteristics|"
            r"supervised learning|unsupervised learning|reinforcement learning|"
            r"stacks?|queues?|trees?|graphs?|thevenin|norton|superposition theorem|"
            r"maximum power transfer theorem))",
            ". ",
            source,
            flags=re.IGNORECASE,
        )
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", expanded) if part.strip()]
    return parts


def _join_sentences(sentences):
    if not sentences:
        return ""
    return _polish_sentence(" ".join(sentences), sentences[0])


def format_academic_answer(*, definition, explanation, key_points, example, conclusion):
    definition_text = _polish_sentence(definition, "Definition is not available in the current reference context.")
    explanation_text = _polish_sentence(explanation, "A concise explanation is provided from the available references.")
    example_text = _polish_sentence(example, "For example, the concept can be applied in a typical academic scenario to solve a practical problem.")
    if not _is_good_phrase(example_text):
        example_text = "For example, the concept can be illustrated using a standard syllabus problem or practical case study."

    definition_sentences = _sentence_list(definition_text)
    explanation_sentences = _sentence_list(explanation_text)
    example_sentences = _sentence_list(example_text)

    selected_definition = definition_sentences[:2]
    selected_explanation = explanation_sentences[:6]
    selected_example = example_sentences[:2]

    if len(selected_definition) < 1:
        selected_definition = _sentence_list("Definition is not available in the current reference context.")[:1]

    if not selected_explanation:
        selected_explanation = _sentence_list(
            "The explanation is summarized from the closest syllabus reference."
        )[:1]

    if not selected_example:
        selected_example = _sentence_list("For example, this concept can be applied in a practical academic scenario.")[:1]

    definition_md = _join_sentences(selected_definition)
    explanation_md = _join_sentences(selected_explanation)
    example_md = _join_sentences(selected_example)

    return "\n\n".join(
        [
            "### Definition",
            definition_md,
            "### Explanation",
            explanation_md,
            "### Example",
            example_md,
        ]
    )
