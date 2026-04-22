from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from chatbot.models import PDFPageChunk, ReferencePDF
from chatbot.services.answer_service import NO_RESULT_MESSAGE, generate_answer
from chatbot.services.search_service import search_chunks
from courses.models import Semester, Subject, Unit


REGULATION = "MIC20"
BRANCH = "CSE"

MIC20_CSE_SUBJECTS = {
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


def _is_theory(subject_code):
    return len(subject_code) >= 6 and subject_code[5] == "T"


def _unit_payloads(subject_name):
    templates = [
        (
            "Unit 1: Foundations and Scope",
            [
                "Fundamental definitions",
                "Historical background",
                "System components",
                "Problem domains",
                "Terminology and standards",
                "Real-world relevance",
            ],
            f"{subject_name} introduces core principles used to model, analyze, and solve engineering problems. This unit establishes vocabulary, scope, and conceptual foundations required for advanced study.",
        ),
        (
            "Unit 2: Core Concepts and Models",
            [
                "Conceptual models",
                "Data and process views",
                "Core operations",
                "Model comparison",
                "Correctness and constraints",
                "Design considerations",
            ],
            f"This unit explains the central conceptual models of {subject_name} and how they are applied in practical scenarios. It focuses on representation, correctness, and decision-making tradeoffs.",
        ),
        (
            "Unit 3: Design and Implementation",
            [
                "Architecture patterns",
                "Implementation workflow",
                "Resource handling",
                "Performance considerations",
                "Testing approach",
                "Common implementation pitfalls",
            ],
            f"Design and implementation topics in {subject_name} are covered with an emphasis on robust construction. Students learn to convert theory into deployable, testable solutions.",
        ),
        (
            "Unit 4: Advanced Topics and Optimization",
            [
                "Advanced techniques",
                "Optimization strategies",
                "Scalability concerns",
                "Security and reliability",
                "Monitoring and diagnostics",
                "Failure handling",
            ],
            f"Advanced concepts of {subject_name} are explored to improve quality, performance, and reliability. The unit highlights optimization and operational concerns in modern systems.",
        ),
        (
            "Unit 5: Applications and Case Studies",
            [
                "Industry use cases",
                "Case study analysis",
                "Toolchain overview",
                "Best practices",
                "Evaluation metrics",
                "Future trends",
            ],
            f"This unit applies {subject_name} concepts in case-driven contexts. Students connect principles with implementation outcomes using metrics, best practices, and trend analysis.",
        ),
    ]

    payloads = []
    for index, (title, subtopics, explanation) in enumerate(templates, start=1):
        content = (
            f"{explanation}\n\n"
            f"Subtopics: {', '.join(subtopics)}.\n\n"
            f"Learning focus: Build concept-level understanding of {subject_name}, relate it to system design, and prepare searchable academic context for revision and question answering."
        )
        payloads.append((index, title, content))
    return payloads


def _seed_operating_system_chat_reference():
    os_subject = Subject.objects.filter(subject_code="20CS4T01").first()
    if not os_subject:
        return False

    uploader = User.objects.filter(is_active=True).order_by("id").first()
    if not uploader:
        return False

    ref, _ = ReferencePDF.objects.update_or_create(
        subject=os_subject,
        title="MIC20 CSE Operating Systems Seed Reference",
        defaults={
            "uploaded_by": uploader,
            "file": "pdfs/mic20_os_seed_reference.pdf",
            "extracted_text": (
                "An operating system is system software that manages hardware resources, schedules processes, "
                "handles memory, controls file systems, and provides essential services to application programs."
            ),
            "is_syllabus_reference": True,
            "status": ReferencePDF.Status.APPROVED,
            "is_active": True,
            "processing_status": ReferencePDF.ProcessingStatus.READY,
            "chunk_count": 1,
        },
    )

    PDFPageChunk.objects.update_or_create(
        reference_pdf=ref,
        page_number=1,
        chunk_index=0,
        defaults={
            "text_content": (
                "An operating system is system software that manages computer hardware resources and provides "
                "services for programs. Core functions include process management, memory management, file "
                "management, device management, and system security."
            ),
            "metadata": {
                "source": "mic20_seed",
                "unit": "Unit 1",
                "topic": "Operating System Basics",
                "word_count": 39,
            },
        },
    )
    ref.chunk_count = PDFPageChunk.objects.filter(reference_pdf=ref).count()
    ref.save(update_fields=["chunk_count"])

    return True


class Command(BaseCommand):
    help = "Insert structured MIC20-CSE academic data (semesters, subjects, and theory units)."

    @transaction.atomic
    def handle(self, *args, **options):
        semester_count = 0
        subject_count = 0
        theory_subject_count = 0
        unit_count = 0

        for sem_number in range(1, 9):
            _, created = Semester.objects.update_or_create(
                number=sem_number,
                regulation=REGULATION,
                defaults={
                    "description": f"{BRANCH} curriculum semester {sem_number} for regulation {REGULATION}",
                    "is_active": True,
                },
            )
            if created:
                semester_count += 1

        for sem_number, subjects in MIC20_CSE_SUBJECTS.items():
            semester = Semester.objects.get(number=sem_number, regulation=REGULATION)
            for subject_code, subject_name in subjects:
                subject, created = Subject.objects.update_or_create(
                    subject_code=subject_code,
                    defaults={
                        "semester": semester,
                        "branch": BRANCH,
                        "name": subject_name,
                        "description": (
                            f"{subject_name} is offered in Semester {sem_number} under {REGULATION}-{BRANCH}. "
                            "The course description is structured for concept-based learning and chatbot retrieval."
                        ),
                        "is_active": True,
                    },
                )
                subject_count += 1

                if _is_theory(subject_code):
                    theory_subject_count += 1
                    for unit_number, title, content in _unit_payloads(subject_name):
                        Unit.objects.update_or_create(
                            subject=subject,
                            unit_number=unit_number,
                            defaults={
                                "title": title,
                                "content": content,
                                "is_active": True,
                            },
                        )
                        unit_count += 1
                else:
                    Unit.objects.filter(subject=subject).delete()

        seeded = _seed_operating_system_chat_reference()

        chunks = search_chunks("What is operating system?")
        answer = generate_answer("What is operating system?", chunks)
        markdown = (answer.get("markdown") or "").lower()
        chat_ok = NO_RESULT_MESSAGE.lower() not in markdown

        total_semesters = Semester.objects.filter(regulation=REGULATION).count()
        total_subjects = Subject.objects.filter(semester__regulation=REGULATION, branch=BRANCH).count()
        total_units = Unit.objects.filter(subject__semester__regulation=REGULATION, subject__branch=BRANCH).count()

        self.stdout.write(self.style.SUCCESS("MIC20-CSE structured data insertion completed."))
        self.stdout.write(f"Semesters inserted/updated: {total_semesters}")
        self.stdout.write(f"Subjects inserted/updated : {total_subjects}")
        self.stdout.write(f"Theory units inserted      : {total_units}")
        self.stdout.write(f"Theory subjects            : {theory_subject_count}")
        self.stdout.write(f"Expected unit count        : {theory_subject_count * 5}")
        self.stdout.write(f"Operating system chat seed : {'YES' if seeded else 'NO'}")
        self.stdout.write(f"Chat sanity (OS query)     : {'PASS' if chat_ok else 'FAIL'}")
