import os
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django
from django.test import Client
from django.core.files.base import ContentFile

django.setup()

from accounts.models import User
from courses.models import Semester, Subject, Unit, Lesson
from chatbot.models import ReferencePDF, PDFPageChunk


results = {
    "auth": {},
    "admin_flow": {},
    "learning_flow": {},
    "chatbot": {},
    "ui": {},
}

# 1) AUTH FLOW
client = Client()
register_resp = client.post(
    "/register/",
    {
        "name": "Student One",
        "email": "student1@example.com",
        "password": "Test@12345",
        "password2": "Test@12345",
    },
)
results["auth"]["student_register_status"] = register_resp.status_code
results["auth"]["student_register_redirect"] = getattr(register_resp, "url", "")

student = User.objects.filter(email="student1@example.com").first()
if student is None:
    student = User.objects.create_user(
        email="student1@example.com",
        password="Test@12345",
        name="Student One",
        role=User.Role.STUDENT,
    )
    results["auth"]["student_register_fallback_created"] = True
else:
    results["auth"]["student_register_fallback_created"] = False

principal, _ = User.objects.get_or_create(
    email="principal1@example.com",
    defaults={"name": "Principal", "role": User.Role.PRINCIPAL},
)
principal.set_password("Test@12345")
principal.role = User.Role.PRINCIPAL
principal.save(update_fields=["password", "role"])

faculty, _ = User.objects.get_or_create(
    email="faculty1@example.com",
    defaults={"name": "Faculty", "role": User.Role.FACULTY},
)
faculty.set_password("Test@12345")
faculty.role = User.Role.FACULTY
faculty.save(update_fields=["password", "role"])
for role_name, email in [
    ("principal", principal.email),
    ("faculty", faculty.email),
    ("student", student.email),
]:
    role_client = Client()
    login_resp = role_client.post(
        "/user-login/",
        {"email": email, "password": "Test@12345"},
    )
    dash_resp = role_client.get("/user-dashboard/")
    results["auth"][f"{role_name}_login_status"] = login_resp.status_code
    results["auth"][f"{role_name}_dashboard_status"] = dash_resp.status_code

# 2) ADMIN FLOW (data setup)
semester, _ = Semester.objects.get_or_create(number=1, regulation="2020")
subject, _ = Subject.objects.update_or_create(
    subject_code="20CS1T01",
    defaults={
        "name": "Programming in C",
        "description": "Basics",
        "semester": semester,
        "is_active": True,
    },
)
unit, _ = Unit.objects.update_or_create(
    subject=subject,
    unit_number=1,
    defaults={
        "title": "Foundations",
        "content": "Variables, control flow, and functions",
    },
)
lesson, _ = Lesson.objects.update_or_create(
    subject=subject,
    order=1,
    defaults={
        "unit": unit,
        "title": "Variables",
        "content": "A variable stores data.",
        "is_active": True,
    },
)

pdf_file = ContentFile(
    b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF",
    name="intro.pdf",
)
ref_pdf, _ = ReferencePDF.objects.update_or_create(
    subject=subject,
    title="Intro C",
    defaults={
        "lesson": lesson,
        "unit": unit,
        "uploaded_by": faculty,
        "file": pdf_file,
        "extracted_text": "Variables and functions are core C concepts.",
        "is_syllabus_reference": True,
        "status": ReferencePDF.Status.APPROVED,
        "is_active": True,
        "processing_status": ReferencePDF.ProcessingStatus.READY,
    },
)

PDFPageChunk.objects.update_or_create(
    reference_pdf=ref_pdf,
    page_number=1,
    chunk_index=0,
    defaults={
        "text_content": "Variables are named storage locations in C language.",
        "metadata": {},
    },
)
PDFPageChunk.objects.update_or_create(
    reference_pdf=ref_pdf,
    page_number=1,
    chunk_index=1,
    defaults={
        "text_content": "Functions organize reusable logic with parameters and return values.",
        "metadata": {},
    },
)

results["admin_flow"]["subject_created"] = Subject.objects.count()
results["admin_flow"]["unit_created"] = Unit.objects.count()
results["admin_flow"]["lesson_created"] = Lesson.objects.count()
results["admin_flow"]["pdf_created"] = ReferencePDF.objects.count()

# 3) LEARNING FLOW
student_client = Client()
student_client.force_login(student)
learn_resp = student_client.get("/learn/")
lesson_resp = student_client.get(f"/lesson/{lesson.id}/")
results["learning_flow"]["learn_subjects_status"] = learn_resp.status_code
results["learning_flow"]["read_lesson_status"] = lesson_resp.status_code

# 4) CHATBOT FLOW
queries = {
    "global": f"/chat/?scope=global&regulation=2020&branch=CS&semester={semester.id}",
    "subject": f"/chat/?scope=subject&subject_id={subject.id}&regulation=2020&branch=CS&semester={semester.id}",
    "lesson": f"/chat/?scope=lesson&lesson_id={lesson.id}&regulation=2020&branch=CS&semester={semester.id}",
    "unit": f"/chat/?scope=unit&unit_id={unit.id}&regulation=2020&branch=CS&semester={semester.id}",
}
for scope, url in queries.items():
    resp = student_client.post(
        url,
        data=json.dumps({"question": "Explain variables in C", "strict_mode": True}),
        content_type="application/json",
    )
    results["chatbot"][f"{scope}_status"] = resp.status_code

# 5) UI VALIDATION
chat_page = student_client.get("/chat/")
content = chat_page.content.decode("utf-8", errors="ignore")
results["ui"]["chat_page_status"] = chat_page.status_code
results["ui"]["has_regulation_filter"] = "data-input-regulation" in content
results["ui"]["has_branch_filter"] = "data-input-branch" in content
results["ui"]["has_semester_filter"] = "data-input-semester" in content
results["ui"]["has_subject_filter"] = "data-input-subject" in content
results["ui"]["has_unit_filter"] = "data-input-unit" in content

print(json.dumps(results, indent=2))
