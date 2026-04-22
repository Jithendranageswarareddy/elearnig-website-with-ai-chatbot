import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django

django.setup()

from scripts.full_automated_data_stress_pipeline import (
    build_database_knowledge_map,
    ingest_external_pdfs,
)


def main():
    source = r"C:\Users\jithendra\OneDrive\Desktop\E learning Final Year Project\Final year project final\AI PDF's"
    ctx = build_database_knowledge_map()
    result = ingest_external_pdfs(source, ctx["knowledge_map"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
