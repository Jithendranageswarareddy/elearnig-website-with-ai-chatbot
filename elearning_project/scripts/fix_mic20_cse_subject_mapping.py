import os
import sys
from pathlib import Path

import django


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")
os.chdir(ROOT)
django.setup()

from courses.models import Semester, Subject  # noqa: E402

EXPECTED = {
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


def main():
    semester_map = {}
    for sem_no in range(1, 9):
        semester, _ = Semester.objects.get_or_create(
            number=sem_no,
            regulation="MIC20",
            defaults={"description": f"Semester {sem_no} - MIC20", "is_active": True},
        )
        if not semester.is_active:
            semester.is_active = True
            semester.save(update_fields=["is_active"])
        semester_map[sem_no] = semester

    created = 0
    updated = 0

    expected_codes = set()

    for sem_no, rows in EXPECTED.items():
        sem_obj = semester_map[sem_no]
        for code, name in rows:
            expected_codes.add(code)
            defaults = {
                "name": name,
                "description": f"{name} - Semester {sem_no}",
                "semester": sem_obj,
                "branch": "CSE",
                "is_active": True,
            }
            subject, was_created = Subject.objects.get_or_create(subject_code=code, defaults=defaults)
            if was_created:
                created += 1
            changed = False
            if subject.name != name:
                subject.name = name
                changed = True
            if subject.semester_id != sem_obj.id:
                subject.semester = sem_obj
                changed = True
            if subject.branch != "CSE":
                subject.branch = "CSE"
                changed = True
            if not subject.is_active:
                subject.is_active = True
                changed = True
            if not subject.description:
                subject.description = f"{name} - Semester {sem_no}"
                changed = True
            if changed and not was_created:
                subject.save()
                updated += 1

    extras = Subject.objects.filter(
        subject_code__startswith="20CS",
        branch="CSE",
        semester__regulation="MIC20",
    ).exclude(subject_code__in=sorted(expected_codes))

    extra_codes = list(extras.values_list("subject_code", flat=True))

    validation = []
    for sem_no in sorted(EXPECTED.keys()):
        rows = EXPECTED[sem_no]
        for code, name in rows:
            subject = Subject.objects.get(subject_code=code)
            validation.append(
                {
                    "code": code,
                    "name_ok": subject.name == name,
                    "semester_ok": subject.semester.number == sem_no,
                    "semester": subject.semester.number,
                    "name": subject.name,
                }
            )

    failed = [row for row in validation if not (row["name_ok"] and row["semester_ok"])]

    print(
        {
            "created": created,
            "updated": updated,
            "expected_subjects": len(expected_codes),
            "extra_subject_codes": extra_codes,
            "validation_failed": len(failed),
            "validation_failures": failed,
        }
    )


if __name__ == "__main__":
    main()
