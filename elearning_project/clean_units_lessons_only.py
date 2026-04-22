import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django

django.setup()

from django.db import transaction

from courses.models import Bookmark, History, Lesson, Semester, Subject, Unit
from progress.models import LessonProgress


REGULATION = "MIC20"
BRANCH = "CSE"

SUBJECTS_BY_SEMESTER = {
    1: [
        ("20CS1T01", "Programming for Problem Solving"),
        ("20CS1T02", "Engineering Mathematics I"),
        ("20CS1T03", "Basic Electrical Engineering"),
        ("20CS1T04", "Engineering Physics"),
        ("20CS1P05", "Programming Lab"),
        ("20CS1P06", "Physics Lab"),
    ],
    2: [
        ("20CS2T01", "Data Structures"),
        ("20CS2T02", "Engineering Mathematics II"),
        ("20CS2T03", "Digital Logic Design"),
        ("20CS2T04", "Environmental Science"),
        ("20CS2P05", "Data Structures Lab"),
        ("20CS2P06", "Digital Logic Lab"),
    ],
    3: [
        ("20CS3T01", "Object Oriented Programming"),
        ("20CS3T02", "Discrete Mathematics"),
        ("20CS3T03", "Computer Organization"),
        ("20CS3T04", "Database Management Systems"),
        ("20CS3P05", "OOP Lab"),
        ("20CS3P06", "DBMS Lab"),
    ],
    4: [
        ("20CS4T01", "Operating Systems"),
        ("20CS4T02", "Design and Analysis of Algorithms"),
        ("20CS4T03", "Software Engineering"),
        ("20CS4T04", "Computer Networks"),
        ("20CS4P05", "OS Lab"),
        ("20CS4P06", "CN Lab"),
    ],
    5: [
        ("20CS5T01", "Artificial Intelligence"),
        ("20CS5T02", "Compiler Design"),
        ("20CS5T03", "Data Warehousing & Mining"),
        ("20CS5T04", "Web Technologies"),
        ("20CS5P05", "AI Lab"),
        ("20CS5P06", "Web Tech Lab"),
    ],
    6: [
        ("20CS6T01", "Machine Learning"),
        ("20CS6T02", "Distributed Systems"),
        ("20CS6T03", "Cryptography & Network Security"),
        ("20CS6T04", "Mobile Computing"),
        ("20CS6P05", "ML Lab"),
        ("20CS6P06", "Security Lab"),
    ],
    7: [
        ("20CS7T01", "Big Data Analytics"),
        ("20CS7T02", "Cloud Computing"),
        ("20CS7T03", "Internet of Things"),
        ("20CS7P04", "Mini Project"),
    ],
    8: [
        ("20CS8P01", "Major Project"),
        ("20CS8T02", "Professional Ethics"),
    ],
}


def ensure_semesters_and_subjects():
    created_subjects = 0
    for sem_number, subjects in SUBJECTS_BY_SEMESTER.items():
        semester, _ = Semester.objects.get_or_create(
            number=sem_number,
            regulation=REGULATION,
            defaults={
                "description": f"{BRANCH} Semester {sem_number} under {REGULATION}",
                "is_active": True,
            },
        )

        for subject_code, subject_name in subjects:
            _, created = Subject.objects.get_or_create(
                subject_code=subject_code,
                defaults={
                    "semester": semester,
                    "branch": BRANCH,
                    "name": subject_name,
                    "description": f"{subject_name} ({subject_code})",
                    "is_active": True,
                },
            )
            if created:
                created_subjects += 1
    return created_subjects


def main():
    with transaction.atomic():
        created_subjects = ensure_semesters_and_subjects()

        # Content/learning-material rows before lesson deletion.
        LessonProgress.objects.all().delete()
        History.objects.all().delete()
        Bookmark.objects.all().delete()

        # Required FK-safe order.
        Lesson.objects.all().delete()
        Unit.objects.all().delete()

    print(f"Subjects newly created (ignored if existing): {created_subjects}")
    print(f"Unit count after cleanup: {Unit.objects.count()}")
    print(f"Lesson count after cleanup: {Lesson.objects.count()}")
    print(f"Subject count after cleanup: {Subject.objects.count()}")


if __name__ == "__main__":
    main()
