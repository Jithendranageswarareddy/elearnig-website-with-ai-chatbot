import os
import sys
from pathlib import Path

# ensure project root on path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elearning_project.settings')
import django
django.setup()

from django.core.management import call_command

out_path = Path(r"C:/Users/jithendra/OneDrive/Desktop/E learning Final Year Project/Final year project final/elearning_project/before_user_migration.json")
out_path.parent.mkdir(parents=True, exist_ok=True)

with out_path.open('w', encoding='utf-8') as f:
    call_command('dumpdata', '--natural-primary', '--natural-foreign', stdout=f)

print('dump written to', out_path)
