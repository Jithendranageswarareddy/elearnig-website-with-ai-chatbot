import os
import sys
from pathlib import Path

# Repository root
ROOT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = ROOT_DIR / "elearning_project"

# Ensure Django package path is importable
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

from elearning_project.wsgi import application

app = application
