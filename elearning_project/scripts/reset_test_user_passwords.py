import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402


USER_PASSWORDS = {
    "admin@gmail.com": "admin123",
    "principal@test.com": "principal123",
    "faculty@test.com": "faculty123",
    "student@test.com": "student123",
}


def main():
    user_model = get_user_model()
    for email, password in USER_PASSWORDS.items():
        user = user_model.objects.get(email=email)
        user.set_password(password)
        user.save(update_fields=["password"])
        print(email, user.password)


if __name__ == "__main__":
    main()
