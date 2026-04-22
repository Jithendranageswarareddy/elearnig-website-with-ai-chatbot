import re

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "is", "it",
    "of", "on", "or", "that", "the", "to", "was", "what", "when", "where", "which", "with",
    "please", "explain", "briefly", "about", "tell", "me", "can", "could", "would",
}

QUERY_ALIAS_MAP = {
    "os": "operating system os",
    "tcp": "tcp transport layer",
    "udp": "udp transport layer",
    "ds": "data structures ds",
    "ml": "machine learning ml",
    "oop": "object oriented programming oop",
    "oops": "object oriented programming oops",
}


def normalize_scope(scope, allowed=None, default="global"):
    allowed_scopes = set(allowed or {"global", "subject", "lesson", "unit", "pdf"})
    normalized = str(scope or default).strip().lower()
    return normalized if normalized in allowed_scopes else default


def tokenize_text(text, *, stopwords=None, min_len=2):
    stopword_set = set(stopwords or STOPWORDS)
    tokens = re.findall(r"[a-zA-Z0-9]+", str(text or "").lower())
    return [token for token in tokens if len(token) >= min_len and token not in stopword_set]


def query_terms(text, *, max_terms=8):
    return tokenize_text(text)[:max(1, int(max_terms))]


def normalize_query_for_search(question):
    source = str(question or "").strip()
    if not source:
        return ""

    source = re.sub(r"[\r\n\t]+", " ", source)
    source = re.sub(r"[`*_#>\[\]{}|]", " ", source)
    source = re.sub(r"\s+", " ", source).strip()

    source = re.sub(r"(?i)^\s*(explain|describe|define|discuss)\s+this\s+from\s+the\s+selected\s+pdf\s*[:\-]?\s*", "", source)
    source = re.sub(r"(?i)^\s*(question|query)\s*[:\-]\s*", "", source)

    if "?" in source:
        source = source.split("?")[0].strip()

    source = re.sub(r"(?i)^\s*give\s+(?:a\s+)?short\s+note\s+on\s+", "", source)
    source = re.sub(r"(?i)^\s*what\s+do\s+you\s+mean\s+by\s+", "", source)
    source = re.sub(r"(?i)^\s*what\s+are\s+the\s+main\s+ideas\s+in\s+", "", source)
    source = re.sub(r"(?i)^\s*why\s+is\s+(.+?)\s+important\s*$", r"\1", source)
    source = re.sub(r"(?i)\s+in\s+simple\s+terms\s*$", "", source)

    source = re.sub(r"\b(unit|chapter|lesson)\s*\d+\b", "", source, flags=re.IGNORECASE)
    for alias, expanded in QUERY_ALIAS_MAP.items():
        source = re.sub(rf"(?i)\b{re.escape(alias)}\b", expanded, source)
    source = re.sub(r"\s+", " ", source).strip()

    normalized = " ".join(tokenize_text(source))
    return normalized if normalized else str(question or "").strip()
