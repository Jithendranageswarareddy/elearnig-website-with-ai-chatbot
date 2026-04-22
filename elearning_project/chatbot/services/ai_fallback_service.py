import json
import urllib.error
import urllib.request

from django.conf import settings


def _openrouter_headers():
    headers = {
        "Content-Type": "application/json",
    }
    api_key = (getattr(settings, "OPENROUTER_API_KEY", "") or "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    site_url = (getattr(settings, "OPENROUTER_SITE_URL", "") or "").strip()
    app_name = (getattr(settings, "OPENROUTER_APP_NAME", "") or "").strip()
    if site_url:
        headers["HTTP-Referer"] = site_url
    if app_name:
        headers["X-Title"] = app_name
    return headers


def _build_prompt(question, context_text, recent_questions=None):
    history = ""
    if recent_questions:
        history_items = [f"- {item}" for item in recent_questions if str(item or "").strip()]
        if history_items:
            history = "\nRecent conversation context:\n" + "\n".join(history_items[:5])

    return (
        "You are an academic assistant. Use syllabus context as primary source. "
        "If context is weak, provide a cautious concise answer and clearly mention limitation.\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{context_text[:6000]}"
        f"{history}\n\n"
        "Output concise factual explanation only."
    )


def generate_ai_fallback_answer(question, context_text, recent_questions=None, model=None):
    api_key = (getattr(settings, "OPENROUTER_API_KEY", "") or "").strip()
    if not api_key:
        return {
            "used": False,
            "model": None,
            "answer": "",
            "reason": "missing_api_key",
        }

    target_model = model or getattr(settings, "CHATBOT_OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free")
    base_url = (getattr(settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1") or "").rstrip("/")
    timeout = int(getattr(settings, "OPENROUTER_TIMEOUT_SECONDS", 8) or 8)

    payload = {
        "model": target_model,
        "messages": [
            {
                "role": "user",
                "content": _build_prompt(question, context_text, recent_questions=recent_questions),
            }
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }

    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=_openrouter_headers(),
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="ignore")
            parsed = json.loads(body)
            content = (
                parsed.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            return {
                "used": bool(content),
                "model": target_model,
                "answer": content,
                "reason": "ok" if content else "empty_response",
            }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return {
            "used": False,
            "model": target_model,
            "answer": "",
            "reason": "request_failed",
        }
