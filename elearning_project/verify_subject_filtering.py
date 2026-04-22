import os
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django

django.setup()

from django.db import transaction
from django.test import Client

from accounts.models import User
from chatbot.models import PDFPageChunk, ReferencePDF
from chatbot.models import ChatQuery
from chatbot.services.search_service import search_chunks
from courses.models import Subject


def run():
    os_subject = Subject.objects.get(subject_code="20CS4T01")
    cn_subject = Subject.objects.get(subject_code="20CS4T04")
    user = User.objects.filter(is_active=True).order_by("id").first()

    if not user:
        raise RuntimeError("No active user found for verification.")

    with transaction.atomic():
        os_ref = ReferencePDF.objects.create(
            subject=os_subject,
            uploaded_by=user,
            title="OS Filter Verification Reference",
            file="pdfs/os_filter_verification.pdf",
            extracted_text=(
                "Process scheduling in operating systems selects the next ready process based on policies "
                "such as FCFS, SJF, and Round Robin to optimize utilization and responsiveness."
            ),
            is_syllabus_reference=True,
            status=ReferencePDF.Status.APPROVED,
            is_active=True,
            processing_status=ReferencePDF.ProcessingStatus.READY,
            chunk_count=1,
        )

        PDFPageChunk.objects.create(
            reference_pdf=os_ref,
            page_number=1,
            chunk_index=0,
            text_content=(
                "Process scheduling is a core operating system function where the scheduler chooses among "
                "ready processes to allocate CPU time fairly and efficiently."
            ),
            metadata={"source": "filter_verification", "subject_code": "20CS4T01"},
        )

        cn_ref = ReferencePDF.objects.create(
            subject=cn_subject,
            uploaded_by=user,
            title="CN Filter Verification Reference",
            file="pdfs/cn_filter_verification.pdf",
            extracted_text=(
                "Computer networks include packet scheduling and queue management across routers. "
                "Scheduling decisions in networking differ from operating-system CPU scheduling."
            ),
            is_syllabus_reference=True,
            status=ReferencePDF.Status.APPROVED,
            is_active=True,
            processing_status=ReferencePDF.ProcessingStatus.READY,
            chunk_count=1,
        )

        PDFPageChunk.objects.create(
            reference_pdf=cn_ref,
            page_number=1,
            chunk_index=0,
            text_content=(
                "Network scheduling in computer networks uses queue disciplines and bandwidth allocation. "
                "This is computer network domain content and not operating system process scheduling."
            ),
            metadata={"source": "filter_verification", "subject_code": "20CS4T04"},
        )

        chunks = search_chunks(
            query="What is process scheduling?",
            scope="subject",
            subject_id=os_subject.id,
            regulation="MIC20",
            branch="CSE",
            semester=os_subject.semester_id,
        )

        resolved_subject_codes = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                continue
            code = getattr(getattr(chunk.reference_pdf, "subject", None), "subject_code", None)
            if code:
                resolved_subject_codes.append(code)

        only_os = all(code == "20CS4T01" for code in resolved_subject_codes)

        print("Subject-scope result subject codes:", resolved_subject_codes)
        print("Only OS content:", only_os)

        client = Client()
        client.force_login(user)
        response = client.post(
            "/chat/",
            data=json.dumps(
                {
                    "question": "What is process scheduling?",
                    "scope": "subject",
                    "subject_id": str(os_subject.id),
                    "regulation": "MIC20",
                    "branch": "CSE",
                    "semester": str(os_subject.semester_id),
                }
            ),
            content_type="application/json",
        )

        body = response.json()
        persisted = ChatQuery.objects.filter(user=user).order_by("-id").first()
        persisted_subject_id = persisted.subject_id if persisted else None
        print("HTTP status:", response.status_code)
        print("Persisted ChatQuery.subject_id:", persisted_subject_id)
        print(
            "Filtering verdict:",
            "PASS"
            if (response.status_code == 200 and persisted_subject_id == os_subject.id and only_os)
            else "FAIL",
        )

        transaction.set_rollback(True)


if __name__ == "__main__":
    run()
