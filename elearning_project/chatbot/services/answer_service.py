import re
from collections import Counter

from .ai_fallback_service import generate_ai_fallback_answer
from .answer_formatter import format_academic_answer
from ..utils.query_utils import normalize_query_for_search, tokenize_text


NO_RESULT_MESSAGE = "This topic is not available in the selected syllabus."
MIN_OVERLAP_THRESHOLD = 0.08
OVERLAP_STOPWORDS = {
    "what", "is", "are", "the", "a", "an", "and", "or", "to", "of", "in", "for",
    "with", "on", "by", "from", "as", "it", "its", "this", "that", "be", "vs",
    "versus", "why", "how", "where", "when", "define", "explain", "differentiate",
    "compare", "list", "please", "about", "short", "note", "mean", "main",
    "ideas", "important", "simple", "terms",
}

GENERIC_SUBJECT_TOKENS = {
    "unit", "units", "chapter", "topic", "topics", "basic", "advanced", "applications",
    "case", "studies", "core", "concept", "concepts", "define", "definition", "explain",
    "how", "does", "what", "where", "used", "real", "systems", "simple", "terms",
}

NOISE_PATTERNS = [
    r"(?i)seed\s+content",
    r"(?i)seed\s+minimal\s+content",
    r"(?i)detailed\s+explanation",
    r"(?i)unit\s+content\s+dump",
    r"(?i)parser\s+integration\s+test",
    r"(?i)topic\s+coverage",
]

VERB_HINT_PATTERN = re.compile(
    r"(?i)\b("
    r"is|are|was|were|be|being|been|has|have|had|"
    r"do|does|did|can|could|will|would|shall|should|may|might|must|"
    r"allocate|allocates|allocated|allocating|"
    r"schedule|schedules|scheduled|scheduling|"
    r"manage|manages|managed|managing|"
    r"execute|executes|executed|executing|"
    r"process|processes|processed|processing|"
    r"run|runs|running|"
    r"determine|determines|determined|determining|"
    r"provide|provides|provided|providing|"
    r"use|uses|used|using|"
    r"perform|performs|performed|performing|"
    r"(?:[A-Za-z]{4,}(?:ed|ing))"
    r")\b"
)

BANNED_PHRASES = (
    "is a syllabus concept in which",
    "this unit covers",
    "seed content",
    "detailed explanation",
    "exact match is limited",
    "partial syllabus context",
    "this response is grounded",
    "the key point is",
)

GARBAGE_PATTERNS = (
    r"(?i)^\s*this response is grounded.*$",
    r"(?i)^\s*the key point is.*$",
    r"(?i)^\s*this unit covers.*$",
    r"(?i)^\s*in conclusion.*$",
)

COURSE_CODE_PATTERN = re.compile(r"\b\d{2}[A-Z]{2,}\d[A-Z]\d{2}\b")
HEADING_PREFIX_PATTERNS = (
    r"(?i)^(applications|characteristics|advantages|disadvantages|features|examples)\s+(?=[A-Z])",
    r"(?i)^(phases of [A-Za-z][A-Za-z\s&/-]{1,60})\s+(?=[A-Z])",
    r"(?i)^(types of [A-Za-z][A-Za-z\s&/-]{1,60})\s+(?=[A-Z])",
    r"(?i)^(classification algorithms|evaluation metrics|energy flow in ecosystems)\s+(?=[A-Z])",
)
DEFINITION_MARKERS = (
    " refers to ",
    " can be defined as ",
    " means ",
    " is a ",
    " is an ",
    " is the ",
    " are ",
    " is ",
    " follows ",
    " consists of ",
    " involves ",
    " describes ",
    " simplifies ",
)
EXAMPLE_MARKERS = ("for example", "for instance", " such as ", " used in ", " used for ")


def _has_verb(text):
    return bool(VERB_HINT_PATTERN.search(str(text or "")))


def _looks_like_fragment(text):
    sentence = str(text or "").strip()
    if not sentence:
        return True
    words = sentence.split()
    word_count = len(words)
    # BALANCE FIX:
    # Keep if: (5+ words and has a verb) OR (6+ words even without a verb)
    keep_sentence = (word_count >= 5 and _has_verb(sentence)) or (word_count >= 6)
    if not keep_sentence:
        return True
    return False


def _remove_banned_phrases(text):
    cleaned = str(text or "")
    for phrase in BANNED_PHRASES:
        cleaned = re.sub(rf"(?i){re.escape(phrase)}", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _normalize_text_block(text):
    return re.sub(r"\s+", " ", str(text or "").replace("\u00ad", " ").replace("–", " - ")).strip()


def _strip_heading_prefix(text):
    cleaned = _normalize_text_block(text)
    for pattern in HEADING_PREFIX_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" -:;,.")


def _is_metadata_like(text):
    sentence = _normalize_text_block(text)
    if not sentence:
        return False
    if COURSE_CODE_PATTERN.search(sentence):
        return True
    if re.search(r"(?i)\bpage\s+\d+\b", sentence) and not _has_verb(sentence):
        return True
    if re.search(r"(?i)\bunit\s*\d+\s*:", sentence) and not _has_verb(sentence):
        return True
    if (":" in sentence or " - " in sentence) and not _has_verb(sentence) and len(sentence.split()) <= 14:
        return True
    return False


def _is_standalone_heading(text):
    sentence = _strip_heading_prefix(text)
    if not sentence or _has_verb(sentence):
        return False
    if sentence.endswith(":") and len(sentence.split()) <= 6:
        return True
    return bool(
        re.fullmatch(
            r"(?i)(applications|characteristics|advantages|disadvantages|features|examples|"
            r"classification algorithms|evaluation metrics|communication|overview|"
            r"introduction|phases(?: of [a-z\s&/-]+)?|types(?: of [a-z\s&/-]+)?)",
            sentence,
        )
    )


def _starts_with_heading_label(text):
    sentence = _normalize_text_block(text)
    return bool(
        re.match(
            r"(?i)^(applications|characteristics|advantages|disadvantages|features|examples|"
            r"phases|types|classification algorithms|evaluation metrics|energy flow in ecosystems)\b",
            sentence,
        )
    )


def _sentence_key(text):
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def _trim_snippet_at_cues(text):
    snippet = _normalize_text_block(text)
    if not snippet:
        return ""
    snippet = re.split(
        r"(?i)\b(for example|for instance|summary|introduction|workflow|applications|"
        r"characteristics|advantages|disadvantages)\b",
        snippet,
    )[0]
    snippet = re.sub(
        r"(?i)\b(arrays?|linked lists?|queues?|trees?|graphs?|unsupervised learning|"
        r"reinforcement learning|superposition theorem|thevenin(?:\s+s)? theorem|"
        r"norton(?:\s+s)? theorem|maximum power transfer theorem)\b.*$",
        "",
        snippet,
    )
    snippet = re.sub(r"\s+", " ", snippet).strip(" -:;,.")
    return snippet


def _topic_context_windows(question, context):
    source = _normalize_text_block(context)
    if not source:
        return []
    windows = []
    seen = set()
    for phrase in _definition_search_phrases(question):
        for match in re.finditer(rf"(?i)\b{re.escape(phrase)}\b", source):
            start = match.start()
            end = min(len(source), match.end() + 260)
            window = source[start:end].strip()
            key = window.lower()
            if key in seen:
                continue
            seen.add(key)
            windows.append(window)
    return windows[:4]


def _clean_chunk_text(text):
    raw = str(text or "")
    raw = raw.replace("\u00ad", "")
    raw = COURSE_CODE_PATTERN.sub(" ", raw)
    raw = raw.replace("–", " - ")
    raw = re.sub(r"(?i)^\s*[^.]{0,140}\s-\s[^.]{0,140}\.\s*", "", raw)
    raw = _remove_banned_phrases(raw)
    raw = re.sub(r"(?i)\bthis unit focuses on\b", "", raw)
    raw = re.sub(r"(?i)\bseed\s+minimal\s+content\b", "", raw)
    raw = re.sub(r"(?i)\bdetailed\s+explanation\b", "", raw)
    raw = re.sub(r"(?i)\bunit\s+content\s+dump\b", "", raw)
    raw = re.sub(r"-\s*\n\s*", "", raw)
    # line-level hard cleaning (MANDATORY): remove broken short lines < 4 words
    line_parts = [line.strip() for line in re.split(r"\r?\n+", raw)]
    cleaned_line_parts = []
    seen_lines = set()
    for line in line_parts:
        if not line:
            continue
        line = _strip_heading_prefix(line)
        if _is_metadata_like(line) or _is_standalone_heading(line):
            continue
        if _looks_like_fragment(line):
            continue
        lowered = line.lower()
        if lowered in seen_lines:
            continue
        if any(re.search(pattern, lowered) for pattern in NOISE_PATTERNS):
            continue
        seen_lines.add(lowered)
        cleaned_line_parts.append(line)

    normalized = (
        " ".join(
            line if re.search(r"[.!?]$", line) else f"{line}."
            for line in cleaned_line_parts
        )
        if cleaned_line_parts
        else raw
    )
    normalized = re.sub(r"\s+", " ", normalized)

    # sentence-level cleaning
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    cleaned_parts = []
    seen = set()
    for part in parts:
        line = _strip_heading_prefix(part.strip())
        if not line:
            continue
        if _is_metadata_like(line) or _is_standalone_heading(line):
            continue
        if _looks_like_fragment(line):
            continue
        key = line.lower()
        if key in seen:
            continue
        if any(re.search(pattern, key) for pattern in NOISE_PATTERNS):
            continue
        seen.add(key)
        cleaned_parts.append(line)
    cleaned = " ".join(cleaned_parts)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    return cleaned.strip()


def _sentence_split(text):
    normalized = _clean_chunk_text(text)
    if not normalized:
        return []
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]
    if len(parts) <= 1 and len(normalized.split()) > 45:
        expanded = re.sub(
            r"(?<!^)\s+(?=(for example|for instance|summary|introduction|applications|"
            r"characteristics|advantages|disadvantages|concept of|ml workflow|workflow|"
            r"supervised learning|unsupervised learning|reinforcement learning|stacks?|"
            r"queues?|linked lists?|trees?|graphs?|superposition theorem|thevenin|norton|"
            r"maximum power transfer theorem))",
            ". ",
            normalized,
            flags=re.IGNORECASE,
        )
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", expanded) if part.strip()]
    return parts


def _clean_garbage_sentence(sentence):
    # Remove known boilerplate/metadata artifacts before ranking or formatting.
    cleaned = _strip_heading_prefix(str(sentence or "").strip())
    if not cleaned:
        return ""
    if _is_metadata_like(cleaned) or _is_standalone_heading(cleaned):
        return ""
    for pattern in GARBAGE_PATTERNS:
        if re.search(pattern, cleaned):
            return ""
    return _refine_academic_english(cleaned)


def _dedupe_sentences(sentences, max_sentences=5):
    # Preserve sentence order while removing near-duplicate content.
    final_answer = []
    seen = set()
    for sentence in sentences or []:
        cleaned = _clean_garbage_sentence(sentence)
        if not cleaned:
            continue
        key = re.sub(r"\s+", " ", cleaned.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        if cleaned not in final_answer:
            final_answer.append(cleaned)
        if len(final_answer) >= max(1, int(max_sentences)):
            break
    return final_answer


def _chunk_value(chunk, key, default=None):
    if isinstance(chunk, dict):
        return chunk.get(key, default)
    return getattr(chunk, key, default)


def _chunk_text(chunk):
    return _clean_chunk_text(_chunk_value(chunk, "text_content", "") or "")


def _chunk_score(chunk):
    metadata = (_chunk_value(chunk, "retrieval_metadata", {}) or {})
    try:
        return float(metadata.get("score", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _chunk_pdf_title(chunk):
    from_dict = _chunk_value(chunk, "reference_pdf_title")
    if from_dict:
        return str(from_dict)
    reference_pdf = _chunk_value(chunk, "reference_pdf")
    return getattr(reference_pdf, "title", "Unknown PDF")


def _chunk_subject_name(chunk):
    from_dict = _chunk_value(chunk, "reference_pdf_subject_name")
    if from_dict:
        return str(from_dict)
    reference_pdf = _chunk_value(chunk, "reference_pdf")
    return getattr(getattr(reference_pdf, "subject", None), "name", "Unknown Subject")


def _chunk_unit_title(chunk):
    from_dict = _chunk_value(chunk, "reference_pdf_unit_title")
    if from_dict:
        return str(from_dict)
    reference_pdf = _chunk_value(chunk, "reference_pdf")
    unit_obj = getattr(reference_pdf, "unit", None)
    return getattr(unit_obj, "title", "Unknown Unit")


def _reference_rows(chunks, limit=5):
    rows = []
    seen = set()
    for chunk in chunks or []:
        reference_pdf_id = _chunk_value(chunk, "reference_pdf_id")
        page_number = _chunk_value(chunk, "page_number")
        key = (reference_pdf_id, page_number)
        if reference_pdf_id is None or page_number is None:
            continue
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "label": f"{_chunk_pdf_title(chunk)} - Page {page_number}",
                "pdf_title": _chunk_pdf_title(chunk),
                "subject_name": _chunk_subject_name(chunk),
                "unit_title": _chunk_unit_title(chunk),
                "page_number": page_number,
                "preview": " ".join(_chunk_text(chunk).split())[:260],
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _token_overlap(question, content):
    normalized_question = normalize_query_for_search(question)
    q_terms = set(tokenize_text(normalized_question, stopwords=OVERLAP_STOPWORDS, min_len=2))
    c_terms = set(tokenize_text(content, stopwords=OVERLAP_STOPWORDS, min_len=2))
    if not q_terms:
        return 0.0
    return float(len(q_terms & c_terms)) / float(len(q_terms))


def _question_intent_terms(question):
    normalized_question = normalize_query_for_search(question)
    tokens = tokenize_text(normalized_question, stopwords=OVERLAP_STOPWORDS, min_len=2)
    seen = set()
    ordered = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered[:8]


def _subject_phrase_from_question(question):
    terms = [term for term in _question_intent_terms(question) if term not in GENERIC_SUBJECT_TOKENS]
    phrase = " ".join(terms[:3]).strip()
    if not phrase:
        return "This concept"
    return phrase[0].upper() + phrase[1:]


def _sentence_match_score(sentence, intent_terms):
    sentence_l = str(sentence or "").lower()
    if not sentence_l:
        return 0.0
    hit_count = sum(1 for term in intent_terms if re.search(rf"\b{re.escape(term)}\b", sentence_l))
    if not intent_terms:
        return 0.0
    return float(hit_count) / float(len(intent_terms))


def _sentence_term_hits(sentence, intent_terms):
    sentence_l = str(sentence or "").lower()
    if not sentence_l or not intent_terms:
        return 0
    return sum(1 for term in intent_terms if term in sentence_l)


def is_valid_sentence(sentence, query_terms):
    # Keep explanations grounded in query intent using a strict term-match rule.
    match_count = sum(1 for token in (query_terms or []) if token in str(sentence or "").lower())
    return match_count >= 2


def _select_relevant_explanation(question, candidate_sentences, fallback_text=""):
    # Selection order: strict matches -> soft matches -> safe fallback text.
    intent_terms = _question_intent_terms(question)

    cleaned_candidates = [
        _clean_garbage_sentence(item)
        for item in (candidate_sentences or [])
        if str(item or "").strip()
    ]
    cleaned_candidates = [item for item in cleaned_candidates if item]
    cleaned_candidates = [
        item for item in cleaned_candidates
        if not item.lower().startswith("for example")
    ]
    cleaned_candidates = _dedupe_sentences(cleaned_candidates, max_sentences=5)

    strong = [
        sentence
        for sentence in cleaned_candidates
        if is_valid_sentence(sentence, intent_terms)
    ]
    if strong:
        return " ".join(strong[:3]).strip()

    soft = [
        sentence
        for sentence in cleaned_candidates
        if _sentence_term_hits(sentence, intent_terms) >= 1
    ]
    if soft:
        return " ".join(soft[:3]).strip()

    if fallback_text:
        return _refine_academic_english(fallback_text)
    return ""


def _is_irrelevant_sentence(sentence, intent_terms):
    if not sentence or _looks_like_fragment(sentence):
        return True
    if not intent_terms:
        return False
    sentence_l = str(sentence).lower()
    # Softer gate: keep useful lines instead of over-discarding.
    # If question has >2 keywords, allow 1 keyword hit OR overlap >= 0.30.
    # For short intent lists (<=2), same fallback keeps coverage stable.
    keyword_hits = sum(1 for term in intent_terms if re.search(rf"\b{re.escape(term)}\b", sentence_l))
    overlap = _sentence_match_score(sentence, intent_terms)

    if len(intent_terms) > 2:
        if keyword_hits >= 1 or overlap >= 0.30:
            return False
        return True

    if keyword_hits >= 1 or overlap >= 0.30:
        return False
    return True


def _refine_academic_english(text):
    refined = _strip_heading_prefix(_remove_banned_phrases(text))
    refined = str(refined or "").strip()
    refined = re.sub(r"(?i)^\s*(summary|overview|introduction)\s*[:\-]?\s*", "", refined)
    refined = re.sub(r"\s+", " ", refined)
    refined = re.sub(r"\s+([,.;:])", r"\1", refined)
    refined = re.sub(r"\b([a-z])([A-Z]{2,})\b", lambda m: (m.group(1) + m.group(2)).upper(), refined)
    refined = re.sub(r"\b(\w+)\s+\1\b", r"\1", refined, flags=re.IGNORECASE)
    refined = re.sub(r"\.(\s*\.)+", ".", refined)
    if refined and refined[-1] not in ".!?":
        refined += "."
    if refined:
        refined = refined[0].upper() + refined[1:]
    return refined


def _collapse_duplicate_words(text):
    words = str(text or "").split()
    if not words:
        return ""
    output = [words[0]]
    for word in words[1:]:
        if word.lower().strip(".,;:!?") == output[-1].lower().strip(".,;:!?"):
            continue
        output.append(word)
    return " ".join(output).strip()


def _normalize_definition_action(clause):
    text = _collapse_duplicate_words(_refine_academic_english(clause)).rstrip(".!? ")
    text = re.sub(r"(?i)^\s*[a-z][a-z\s&/-]{2,50}\s+(?=(a|an|the|this|it)\b)", "", text)
    text = re.sub(r"(?i)\bdetermine which process gets cpu time\b", "allocate CPU time among processes", text)
    text = re.sub(r"(?i)\bcpu scheduling algorithms\b", "scheduling algorithms", text)
    text = re.sub(r"(?i)\bprocess scheduling algorithms\b", "scheduling algorithms", text)
    text = re.sub(
        r"(?i)^\s*(?:[A-Za-z]+\s+){0,3}algorithms?\s+(?=(allocate|manage|schedule|execute|control|organize|prioritize|handle|coordinate|assign)\b)",
        "",
        text,
    )
    text = re.sub(r"(?i)^\s*(that|which)\s+", "", text)
    if re.search(r"(?i)^\s*to\s+", text):
        text = re.sub(r"(?i)^\s*to\s+", "", text)
    return text.strip()


def _force_direct_definition(question, definition):
    q = str(question or "").strip().lower()
    d = _refine_academic_english(definition)
    if not d:
        topic = _subject_phrase_from_question(q)
        return f"{topic} is explained using the available academic references."

    # Build a direct first-line answer from question intent.
    subject_phrase = _subject_phrase_from_question(q)
    subject_lower = subject_phrase.lower()
    d_lower = d.lower()
    if d_lower.startswith(subject_lower) and any(
        marker in f" {d_lower} "
        for marker in (" is ", " are ", " refers to ", " means ", " follows ", " consists of ", " involves ", " simplifies ")
    ):
        return _collapse_duplicate_words(d if d.endswith((".", "!", "?")) else f"{d}.")
    action = _normalize_definition_action(d)

    if re.search(r"(?i)^the requested concept is explained", action):
        return _refine_academic_english(action)

    # If source already contains a clean direct-definition phrase, keep it with duplicate cleanup.
    direct_markers = (" refers to ", " can be defined as ", " means ")
    direct_verbs = (" is ", " are ", " follows ", " consists of ", " acts as ", " provides ")
    if any(marker in action.lower() for marker in direct_markers) or any(marker in action.lower() for marker in direct_verbs):
        return _collapse_duplicate_words(action if action.endswith((".", "!", "?")) else f"{action}.")

    if "cpu" in action.lower() and re.search(r"(?i)\ballocate\b", action):
        sentence = f"{subject_phrase} is the method used by an operating system to {action}."
    elif re.search(r"(?i)\b(allocate|manage|schedule|execute|control|organize|prioritize|handle|coordinate|assign)\b", action):
        sentence = f"{subject_phrase} is the method used to {action}."
    else:
        sentence = f"{subject_phrase} refers to {action}."
    return _collapse_duplicate_words(_refine_academic_english(sentence))


def _generate_example(question, definition, explanation):
    topic = " ".join(_question_intent_terms(question)[:3]).strip().lower()
    if "transport" in topic or "tcp" in topic or "udp" in topic:
        return "For example, web browsing uses TCP for reliable delivery, while video calls use UDP to reduce latency."
    if "supervised" in topic or "machine learning" in topic:
        return "For example, an email spam filter learns from labeled emails to classify new messages as spam or not spam."
    if "scheduling" in topic or "process" in topic:
        return "For example, Round Robin scheduling shares CPU time among interactive applications so the system remains responsive."
    if "stack" in topic:
        return "For example, function calls in a compiler runtime are managed using a stack to track return addresses."
    if "asymmetric" in topic or "cryptography" in topic:
        return "For example, RSA uses a public key for encryption and a private key for decryption in secure communication."
    if "network" in topic and "theorem" in topic:
        return "For example, Thevenin's theorem replaces a complex circuit with an equivalent voltage source and series resistance for easier analysis."
    if "deadlock" in topic:
        return "For example, two database transactions waiting on each other's locks can create deadlock and require recovery."
    if "cloud" in topic:
        return "For example, a startup can deploy an application on cloud virtual machines and scale resources during peak traffic."
    return "For example, this concept can be illustrated using a standard syllabus problem or practical case study."


def _generate_explanation(question, definition, context):
    topic = " ".join(_question_intent_terms(question)[:4]).strip().lower()
    source = f"{definition} {context}".lower()
    if "stack" in topic or " lifo " in f" {source} ":
        return "A stack allows insertion and deletion at one end, so the most recently added item is removed first."
    if "supervised" in topic or "labeled data" in source:
        return "In supervised learning, the model learns from labeled input-output data so it can predict the correct output for new inputs."
    if "asymmetric" in topic or ("public key" in source and "private key" in source):
        return "It uses a pair of keys, where the public key can be shared openly and the private key is kept secret by the owner."
    if "network theorem" in topic or "network theorems" in source:
        return "Network theorems convert complex electrical circuits into simpler equivalent forms, making analysis easier and faster."
    return ""


def _generate_definition(question, context):
    topic = " ".join(_question_intent_terms(question)[:4]).strip().lower()
    source = str(context or "").lower()
    if "stack" in topic or " lifo " in f" {source} ":
        return "A stack is a linear data structure that follows the last in, first out (LIFO) principle."
    if "supervised" in topic or "labeled data" in source:
        return "Supervised learning is a type of machine learning in which a model is trained using labeled data."
    if "asymmetric" in topic or ("public key" in source and "private key" in source):
        return "Asymmetric cryptography is a cryptographic method that uses a public key and a private key."
    if "network theorem" in topic or "network theorems" in source:
        return "Network theorems are principles used to simplify the analysis of complex electrical circuits."
    return ""


def _definition_score(sentence, question):
    cleaned = _clean_garbage_sentence(sentence)
    if not cleaned:
        return -1.0
    lowered = f" {cleaned.lower()} "
    intent_terms = _question_intent_terms(question)
    score = min(_sentence_term_hits(cleaned, intent_terms), 2) * 0.45
    if any(cleaned.lower().startswith(phrase.lower()) for phrase in _definition_search_phrases(question)):
        score += 1.2
    if any(marker in lowered for marker in DEFINITION_MARKERS):
        score += 1.5
    if re.match(r"(?i)^(a|an|the)\s+", cleaned):
        score += 0.8
    if _starts_with_heading_label(sentence):
        score -= 1.2
    if " used in " in lowered and not any(marker in lowered for marker in (" is a ", " is an ", " is the ", " refers to ", " means ", " can be defined as ")):
        score -= 0.8
    if any(marker in lowered for marker in EXAMPLE_MARKERS):
        score -= 0.8
    if not _has_verb(cleaned):
        score -= 0.3
    return score


def _example_score(sentence, question):
    cleaned = _clean_garbage_sentence(sentence)
    if not cleaned:
        return -1.0
    lowered = f" {cleaned.lower()} "
    intent_terms = _question_intent_terms(question)
    score = min(_sentence_term_hits(cleaned, intent_terms), 2) * 0.30
    if lowered.strip().startswith("for example") or lowered.strip().startswith("for instance"):
        score += 2.0
    if " such as " in lowered or " used in " in lowered or " used for " in lowered:
        score += 1.0
    if _starts_with_heading_label(sentence):
        score += 0.3
    return score


def _select_definition_sentence(question, sentences):
    scored = []
    for sentence in sentences or []:
        cleaned = _clean_garbage_sentence(sentence)
        if not cleaned:
            continue
        scored.append((_definition_score(cleaned, question), cleaned))
    if scored:
        scored.sort(key=lambda item: (-item[0], item[1]))
        if scored[0][0] > 0:
            return scored[0][1]
        return scored[0][1]
    return ""


def _select_example_sentence(question, sentences):
    scored = []
    for sentence in sentences or []:
        cleaned = _clean_garbage_sentence(sentence)
        if not cleaned:
            continue
        scored.append((_example_score(cleaned, question), cleaned))
    if not scored:
        return ""
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[0][1] if scored[0][0] > 0.4 else ""


def _definition_search_phrases(question):
    terms = [term for term in _question_intent_terms(question) if term not in GENERIC_SUBJECT_TOKENS]
    phrases = []
    if len(terms) >= 3:
        phrases.append(" ".join(terms[:3]))
    if len(terms) >= 2:
        phrases.append(" ".join(terms[:2]))
    phrases.extend(terms[:3])
    ordered = []
    seen = set()
    for phrase in phrases:
        key = phrase.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(phrase.strip())
    return ordered


def _extract_definition_from_context(question, context):
    source = _normalize_text_block(context)
    if not source:
        return ""
    verb_group = r"(is|are|refers to|means|can be defined as|follows|involves|consists of|simplifies)"
    candidates = []
    for phrase in _definition_search_phrases(question):
        pattern = re.compile(
            rf"(?i)\b{re.escape(phrase)}\b[^.?!]{{0,32}}\b{verb_group}\b[^.?!]{{0,180}}"
        )
        for match in pattern.finditer(source):
            snippet = _trim_snippet_at_cues(match.group(0))
            cleaned = _clean_garbage_sentence(snippet)
            if cleaned and (
                cleaned.lower().startswith(phrase.lower())
                or cleaned.lower().startswith(f"the {phrase.lower()}")
                or cleaned.lower().startswith(f"a {phrase.lower()}")
                or cleaned.lower().startswith(f"an {phrase.lower()}")
            ):
                candidates.append(cleaned)

    if candidates:
        candidates.sort(
            key=lambda item: (
                -_definition_score(item, question),
                len(item.split()),
            )
        )
        best = candidates[0]
        if len(best.split()) <= 35:
            return best
        return _refine_academic_english(" ".join(best.split()[:28]))

    lowered = source.lower()
    if "public and private keys" in lowered and any(term in lowered for term in ("asymmetric", "crypto", "cryptography")):
        return "Asymmetric cryptography is a cryptographic method that uses a public key and a private key."
    return ""


def _extract_example_from_context(question, context):
    source = _normalize_text_block(context)
    if not source:
        return ""
    for window in _topic_context_windows(question, source):
        match = re.search(r"(?i)\bfor example\b[^.?!]{0,220}", window)
        if match:
            snippet = _trim_snippet_at_cues(match.group(0))
            cleaned = _clean_garbage_sentence(snippet)
            if cleaned and len(cleaned.split()) >= 6:
                return cleaned
    match = re.search(r"(?i)\bfor example\b[^.?!]{0,220}", source)
    if match:
        snippet = _trim_snippet_at_cues(match.group(0))
        cleaned = _clean_garbage_sentence(snippet)
        if cleaned and len(cleaned.split()) >= 6:
            return cleaned
    return ""


def _dedupe_chunks(chunks):
    unique = []
    seen = set()
    for chunk in chunks or []:
        text = " ".join(_chunk_text(chunk).split()).lower()
        key = (_chunk_value(chunk, "reference_pdf_id"), _chunk_value(chunk, "page_number"), text[:220])
        if key in seen:
            continue
        seen.add(key)
        unique.append(chunk)
    return unique


def _extract_key_concepts(sentences, limit=5):
    counts = Counter()
    for sentence in sentences:
        for token in re.findall(r"[A-Za-z]{4,}", sentence.lower()):
            if token not in OVERLAP_STOPWORDS:
                counts[token] += 1
    return [word.title() for word, _ in counts.most_common(limit)]


def _collect_best_sentences(chunks, question, max_sentences=10):
    intent_terms = _question_intent_terms(question)
    ranked = []
    for index, chunk in enumerate(chunks or []):
        base_weight = 1.0 - (index * 0.08)
        score_weight = _chunk_score(chunk)
        for sentence in _sentence_split(_chunk_text(chunk)):
            if _is_irrelevant_sentence(sentence, intent_terms):
                continue
            sentence_score = _sentence_match_score(sentence, intent_terms)
            if sentence_score <= 0 and len(intent_terms) > 0:
                continue
            verb_bonus = 0.05 if _has_verb(sentence) else 0.0
            title_penalty = 0.10 if " - " in sentence else 0.0
            metadata_penalty = 0.40 if _is_metadata_like(sentence) else 0.0
            heading_penalty = 0.18 if _is_standalone_heading(sentence) else 0.0
            opener_penalty = 0.12 if _starts_with_heading_label(sentence) and not _has_verb(sentence) else 0.0
            total = (
                (sentence_score * 0.75)
                + (score_weight * 0.20)
                + (base_weight * 0.05)
                + verb_bonus
                - title_penalty
                - metadata_penalty
                - heading_penalty
                - opener_penalty
            )
            ranked.append((total, sentence))

    if not ranked:
        fallback = []
        for chunk in chunks or []:
            fallback.extend(_sentence_split(_chunk_text(chunk)))
        return [item for item in fallback if not _looks_like_fragment(item)][:max_sentences]

    ranked.sort(key=lambda item: (-item[0], item[1]))
    deduped = []
    seen = set()
    for _score, sentence in ranked:
        key = sentence.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(sentence)
        if len(deduped) >= max_sentences:
            break
    return deduped


def _follow_up_suggestions(question, key_concepts):
    suggestions = []
    for concept in key_concepts[:3]:
        suggestions.append(f"Explain {concept} in more detail.")
    if key_concepts:
        suggestions.append(f"What are the advantages and limitations of {key_concepts[0]}?")
    if not suggestions:
        suggestions = [
            f"Can you explain this topic with a practical example?",
            f"What are important exam points for this concept?",
            f"How does this relate to previous units?",
        ]
    return suggestions[:3]


def _build_answer_from_reference(reference):
    if not reference:
        return "Not available"
    subject_name = reference.get("subject_name") or "Unknown Subject"
    unit_title = reference.get("unit_title") or "Unknown Unit"
    return f"{subject_name} → {unit_title}"


def _confidence_label(score):
    if score > 0.75:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"


def _safe_excerpt(text, default=""):
    cleaned = " ".join(str(text or "").split())
    return cleaned if cleaned else default


def generate_answer(question, retrieved_chunks, recent_questions=None):
    candidate_chunks = _dedupe_chunks(list(retrieved_chunks or []))[:2]
    candidate_chunks = [
        chunk
        for chunk in candidate_chunks
        if not (_chunk_value(chunk, "retrieval_metadata", {}) or {}).get("empty_result")
    ]

    references = _reference_rows(candidate_chunks, limit=5)
    retrieval_previews = [
        {
            "label": row["label"],
            "excerpt": row["preview"],
            "pdf_url": "",
            "page_number": row["page_number"],
        }
        for row in references
    ]

    merged_context = "\n".join(_safe_excerpt(_chunk_text(chunk)) for chunk in candidate_chunks)
    topic_context = "\n".join(_topic_context_windows(question, merged_context))
    merged_sentences = _dedupe_sentences(
        _collect_best_sentences(candidate_chunks, question, max_sentences=20),
        max_sentences=5,
    )
    if len(merged_sentences) < 2:
        merged_sentences.append("This concept is explained using the closest available reference content.")

    overlap = _token_overlap(question, merged_context)
    semantic_score = max((_chunk_score(chunk) for chunk in candidate_chunks), default=0.0)
    relevance_score = round((overlap * 0.7) + (semantic_score * 0.3), 4)
    max_score = 1.0
    confidence_score = round(max(0.0, min(1.0, relevance_score / max_score)), 2)
    confidence_label = _confidence_label(confidence_score)

    if confidence_label == "Low":
        return {
            "markdown": NO_RESULT_MESSAGE,
            "structured_response": [],
            "related_concepts": [],
            "related_concept_links": [],
            "references": [],
            "references_count": 0,
            "reference_previews": [],
            "diagrams": [],
            "follow_up_questions": [],
            "follow_up_suggestions": [],
            "retrieval_previews": [],
            "relevance_score": relevance_score,
            "confidence_score": confidence_score,
            "confidence_label": confidence_label,
            "confidence_display": f"Confidence: {confidence_label}",
            "question_type": "contextual" if recent_questions else "direct",
            "expanded_question": question,
            "search_query": question,
            "generation_mode": "rejected",
            "llm_model_used": None,
            "candidate_source": "FAISS/DB",
            "retrieved_chunk_count": len(candidate_chunks),
            "next_topics": [],
            "insufficient_context": True,
            "answer_from": "Not available",
        }

    ai_mode = "none"
    ai_model = None
    ai_answer = ""

    # direct question matching: first lines must answer intent
    definition = _select_definition_sentence(question, merged_sentences)
    context_definition = _extract_definition_from_context(question, topic_context or merged_context)
    if context_definition and (
        not definition
        or _definition_score(context_definition, question) >= _definition_score(definition, question)
    ):
        definition = context_definition
    filtered_sentences = [
        item
        for item in merged_sentences
        if _clean_garbage_sentence(item)
    ]
    example = _select_example_sentence(question, filtered_sentences)
    context_example = _extract_example_from_context(question, topic_context or merged_context)
    if context_example:
        example = context_example
    used_keys = {_sentence_key(definition), _sentence_key(example)}
    explanation_candidates = [
        item
        for item in filtered_sentences
        if _sentence_key(item) not in used_keys
    ]
    explanation = _select_relevant_explanation(
        question,
        (_sentence_split(topic_context) + explanation_candidates)[:5] if topic_context else explanation_candidates[:5],
        fallback_text=topic_context or " ".join(explanation_candidates[:2]) or merged_context[:450],
    )

    # Hybrid confidence policy:
    # High: DB only
    # Medium: DB + AI enhance
    # Low: STRICT REJECTION (prevent hallucination on out-of-syllabus queries)
    if confidence_label == "Low":
        # Get API key from settings to check if AI fallback is available
        from django.conf import settings
        api_key = getattr(settings, "OPENROUTER_API_KEY", "").strip()
        
        if api_key:
            # Only try AI if we have a valid API key
            ai_result = generate_ai_fallback_answer(
                question,
                merged_context or "No relevant chunk available.",
                recent_questions=recent_questions,
            )
            if ai_result.get("used"):
                ai_mode = "ai_only"
                ai_model = ai_result.get("model")
                ai_answer = ai_result.get("answer") or ""
                fallback_sentences = _sentence_split(ai_answer)
                if fallback_sentences:
                    definition = fallback_sentences[0]
                    sanitized_fallback = _dedupe_sentences(fallback_sentences, max_sentences=5)
                    definition = sanitized_fallback[0] if sanitized_fallback else definition
                    explanation = _select_relevant_explanation(
                        question,
                        sanitized_fallback[1:5],
                        fallback_text=explanation,
                    ) or explanation
                    example = sanitized_fallback[4] if len(sanitized_fallback) > 4 else example
            else:
                # AI failed or refused → strict rejection
                ai_mode = "rejected"
                definition = NO_RESULT_MESSAGE
                explanation = ""
                example = ""
        else:
            # No API key available → strict rejection (prevent hallucination)
            ai_mode = "rejected"
            definition = NO_RESULT_MESSAGE
            explanation = ""
            example = ""

    elif confidence_label == "Medium":
        ai_result = generate_ai_fallback_answer(
            question,
            merged_context,
            recent_questions=recent_questions,
        )
        if ai_result.get("used"):
            ai_mode = "db_plus_ai"
            ai_model = ai_result.get("model")
            ai_answer = ai_result.get("answer") or ""
            ai_sentences = _dedupe_sentences(_sentence_split(ai_answer), max_sentences=5)
            if ai_sentences:
                explanation = _select_relevant_explanation(
                    question,
                    ai_sentences[:5],
                    fallback_text=explanation,
                ) or explanation
                if len(ai_sentences) > 3:
                    example = ai_sentences[3]

    # refinement step for professional readable output
    definition = _force_direct_definition(question, definition)
    core_phrase = _subject_phrase_from_question(question).lower()
    if (
        _is_metadata_like(definition)
        or "this unit explains" in str(definition).lower()
        or len(str(definition).split()) > 28
        or not (
            str(definition).lower().startswith(core_phrase)
            or str(definition).lower().startswith(f"a {core_phrase}")
            or str(definition).lower().startswith(f"an {core_phrase}")
            or str(definition).lower().startswith(f"the {core_phrase}")
        )
    ):
        generated_definition = _generate_definition(question, topic_context or merged_context)
        if generated_definition:
            definition = generated_definition
    explanation = _select_relevant_explanation(
        question,
        _sentence_split(explanation),
        fallback_text=explanation,
    ) or _refine_academic_english(explanation)
    if (
        _looks_like_fragment(explanation)
        or _is_metadata_like(explanation)
        or len(str(explanation).split()) > 45
        or "for example" in str(explanation).lower()
        or "this unit explains" in str(explanation).lower()
        or "summary" in str(explanation).lower()
        or "introduction" in str(explanation).lower()
        or "this concept is explained using the closest available reference content" in str(explanation).lower()
        or len(str(explanation).split()) < 8
    ):
        generated_explanation = _generate_explanation(question, definition, topic_context or merged_context)
        if generated_explanation:
            explanation = generated_explanation
    example = _refine_academic_english(example)
    if (
        _looks_like_fragment(example)
        or str(example).strip().lower() in str(explanation).strip().lower()
        or len(str(example).split()) < 8
        or _is_metadata_like(example)
        or not str(example).lower().startswith("for example")
        or (len(str(example).split()) > 35 and not str(example).lower().startswith("for example"))
        or "improves system performance" in str(example).lower()
    ):
        example = _generate_example(question, definition, explanation)
    example = _refine_academic_english(example)

    key_concepts = _extract_key_concepts(merged_sentences)
    conclusion = ""

    markdown = format_academic_answer(
        definition=definition,
        explanation=explanation,
        key_points=key_concepts,
        example=example,
        conclusion=conclusion,
    )

    follow_ups = _follow_up_suggestions(question, key_concepts)
    answer_from = _build_answer_from_reference(references[0] if references else None)

    return {
        "markdown": markdown,
        "structured_response": [],
        "related_concepts": key_concepts,
        "related_concept_links": [],
        "references": references,
        "references_count": len(references),
        "reference_previews": references,
        "diagrams": [],
        "follow_up_questions": follow_ups,
        "follow_up_suggestions": follow_ups,
        "retrieval_previews": retrieval_previews,
        "relevance_score": relevance_score,
        "confidence_score": confidence_score,
        "confidence_label": confidence_label,
        "confidence_display": f"Confidence: {confidence_label}",
        "question_type": "contextual" if recent_questions else "direct",
        "expanded_question": question,
        "search_query": question,
        "generation_mode": ai_mode if ai_mode != "none" else "db_only",
        "llm_model_used": ai_model,
        "candidate_source": "FAISS/DB",
        "retrieved_chunk_count": len(candidate_chunks),
        "next_topics": follow_ups,
        "insufficient_context": False,
        "answer_from": answer_from,
    }
