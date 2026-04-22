import os
import sys


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django  # noqa: E402


django.setup()

from chatbot.models import ReferencePDF  # noqa: E402
from chatbot.services.pdf_processor import process_pdf  # noqa: E402


def main():
    total = 0
    failures = 0
    for reference_pdf in ReferencePDF.objects.order_by("id"):
        total += 1
        try:
            process_pdf(reference_pdf, replace_existing=True)
            print(f"reindexed: {reference_pdf.id} {reference_pdf.title}")
        except Exception as exc:
            failures += 1
            print(f"failed: {reference_pdf.id} {reference_pdf.title} -> {exc}")

    print(f"done: total={total} failures={failures}")


if __name__ == "__main__":
    main()
