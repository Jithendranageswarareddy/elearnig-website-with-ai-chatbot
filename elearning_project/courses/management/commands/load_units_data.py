from django.core.management.base import BaseCommand
from django.db import transaction

from courses.models import Subject, Unit


def _is_theory(subject_code: str) -> bool:
    return len(subject_code or "") >= 6 and subject_code[5] == "T"


def _default_units(subject_name: str):
    return [
        (
            1,
            "Unit 1: Foundations",
            f"This unit introduces the foundational concepts of {subject_name}, key definitions, scope, and academic context for structured learning.",
        ),
        (
            2,
            "Unit 2: Core Concepts and Process Management",
            f"This unit explains core concepts of {subject_name} with process-level reasoning, control flow, and concept mapping for search-friendly understanding.",
        ),
        (
            3,
            "Unit 3: Design and Implementation",
            f"This unit covers design principles and implementation strategy in {subject_name}, including reliability, performance, and structured problem solving.",
        ),
        (
            4,
            "Unit 4: Advanced Topics",
            f"This unit discusses advanced topics of {subject_name}, optimization techniques, and practical engineering constraints in real systems.",
        ),
        (
            5,
            "Unit 5: Applications and Case Studies",
            f"This unit presents applications, case studies, and analytical methods in {subject_name} to strengthen concept-based learning and revision.",
        ),
    ]


# Subject-specific overrides where required for clean academic retrieval.
UNIT_DATA = {
    "20CS4T01": [
        (
            1,
            "Unit 1: Introduction to Operating Systems",
            "An operating system is system software that manages hardware resources and provides services to applications. This unit covers OS goals, structures, system calls, kernel concepts, and user-kernel interaction.",
        ),
        (
            2,
            "Unit 2: Process Management and Scheduling",
            "Process scheduling is the operating system mechanism for selecting a ready process for CPU execution. This unit covers process states, PCB, context switching, schedulers, FCFS, SJF, Priority, Round Robin, starvation, and response-time tradeoffs.",
        ),
        (
            3,
            "Unit 3: Memory Management",
            "This unit explains address binding, logical and physical memory, paging, segmentation, virtual memory, demand paging, replacement policies, and memory allocation strategies.",
        ),
        (
            4,
            "Unit 4: File and I/O Management",
            "This unit covers file systems, directory structures, allocation methods, free-space management, buffering, spooling, and device management in operating systems.",
        ),
        (
            5,
            "Unit 5: Protection, Security, and Case Studies",
            "This unit discusses OS protection models, access control, authentication, security threats, and comparative case studies across modern operating systems.",
        ),
    ],
}


class Command(BaseCommand):
    help = "Insert/update unit data for MIC20-CSE subjects using existing Semester/Subject/Unit models only."

    @transaction.atomic
    def handle(self, *args, **options):
        theory_subjects = Subject.objects.filter(
            semester__regulation="MIC20",
            branch="CSE",
            is_active=True,
            semester__is_active=True,
            subject_code__regex=r"^\d{2}CS\dT\d{2}$",
        ).order_by("semester__number", "subject_code")

        practical_subjects = Subject.objects.filter(
            semester__regulation="MIC20",
            branch="CSE",
            is_active=True,
            semester__is_active=True,
            subject_code__regex=r"^\d{2}CS\dP\d{2}$",
        )

        theory_count = theory_subjects.count()
        updated_units = 0

        for subject in theory_subjects:
            unit_rows = UNIT_DATA.get(subject.subject_code) or _default_units(subject.name)

            for unit_number, title, content in unit_rows:
                Unit.objects.update_or_create(
                    subject=subject,
                    unit_number=unit_number,
                    defaults={
                        "title": title,
                        "content": content,
                        "is_active": True,
                    },
                )
                updated_units += 1

            Unit.objects.filter(subject=subject, unit_number__gt=5).delete()

        # Ensure no units exist for practical subjects.
        practical_deleted = 0
        for subject in practical_subjects:
            deleted, _ = Unit.objects.filter(subject=subject).delete()
            practical_deleted += deleted

        total_units = Unit.objects.filter(
            subject__semester__regulation="MIC20",
            subject__branch="CSE",
            subject__is_active=True,
        ).count()

        per_subject_ok = all(
            Unit.objects.filter(subject=subject).count() == 5
            for subject in theory_subjects
        )

        practical_ok = all(
            Unit.objects.filter(subject=subject).count() == 0
            for subject in practical_subjects
        )

        self.stdout.write(self.style.SUCCESS("load_units_data completed."))
        self.stdout.write(f"Theory subjects : {theory_count}")
        self.stdout.write(f"Units upserted  : {updated_units}")
        self.stdout.write(f"Units deleted on practical subjects: {practical_deleted}")
        self.stdout.write(f"Total units     : {total_units}")
        self.stdout.write(f"Theory count check (expected 28): {'PASS' if theory_count == 28 else 'FAIL'}")
        self.stdout.write(f"Per-theory 5 units check   : {'PASS' if per_subject_ok else 'FAIL'}")
        self.stdout.write(f"Practical has no units     : {'PASS' if practical_ok else 'FAIL'}")
