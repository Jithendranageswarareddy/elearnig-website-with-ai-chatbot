import tempfile
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from chatbot.models import ReferencePDF
from courses.models import Semester, Subject

from .models import User


class LoginViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="faculty@test.com",
            password="faculty123",
            name="Faculty",
            role=User.Role.FACULTY,
        )

    def test_login_accepts_email_field(self):
        response = self.client.post(
            reverse("login"),
            {"email": "faculty@test.com", "password": "faculty123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("user_dashboard"))

    def test_login_accepts_legacy_username_field(self):
        response = self.client.post(
            reverse("login"),
            {"username": "faculty@test.com", "password": "faculty123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("user_dashboard"))


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class RoleSecurityTests(TestCase):
    def setUp(self):
        self.semester = Semester.objects.create(
            number=1,
            regulation="R2026",
            description="Test semester",
            is_active=True,
        )
        self.subject = Subject.objects.create(
            semester=self.semester,
            subject_code="CS101",
            name="Intro CS",
            description="Basics",
            is_active=True,
        )
        self.principal = User.objects.create_user(
            email="principal@example.com",
            password="pass12345",
            name="Principal User",
            role=User.Role.PRINCIPAL,
        )
        self.faculty = User.objects.create_user(
            email="faculty@example.com",
            password="pass12345",
            name="Faculty User",
            role=User.Role.FACULTY,
        )
        self.student = User.objects.create_user(
            email="student@example.com",
            password="pass12345",
            name="Student User",
            role=User.Role.STUDENT,
        )

    def _upload_payload(self, title):
        return {
            "title": title,
            "subject_id": str(self.subject.id),
            "file": SimpleUploadedFile(
                "sample.pdf",
                b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF",
                content_type="application/pdf",
            ),
        }

    def test_principal_can_upload(self):
        self.client.force_login(self.principal)
        with patch("chatbot.views.PyPDF2.PdfReader") as mock_reader, patch(
            "chatbot.views.queue_reference_pdf_processing",
            return_value={"queued": True, "task_id": "task-principal"},
        ):
            page = Mock()
            page.extract_text.return_value = "principal upload content"
            mock_reader.return_value.pages = [page]
            response = self.client.post(
                reverse("upload_pdf"),
                data=self._upload_payload("Principal Upload"),
            )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ReferencePDF.objects.filter(
                uploaded_by=self.principal,
                title="Principal Upload",
            ).exists()
        )

    def test_principal_can_approve(self):
        pdf = ReferencePDF.objects.create(
            subject=self.subject,
            uploaded_by=self.faculty,
            title="Pending PDF",
            file=SimpleUploadedFile("pending.pdf", b"%PDF-1.4"),
            extracted_text="pending",
            status=ReferencePDF.Status.HOLD,
            is_syllabus_reference=False,
        )
        self.client.force_login(self.principal)
        response = self.client.post(reverse("approve_pdf", args=[pdf.id]))
        self.assertEqual(response.status_code, 302)
        pdf.refresh_from_db()
        self.assertEqual(pdf.status, ReferencePDF.Status.APPROVED)

    def test_principal_can_hold_pdf(self):
        pdf = ReferencePDF.objects.create(
            subject=self.subject,
            uploaded_by=self.faculty,
            title="Approved PDF",
            file=SimpleUploadedFile("approved.pdf", b"%PDF-1.4"),
            extracted_text="approved",
            status=ReferencePDF.Status.APPROVED,
            is_syllabus_reference=True,
        )
        self.client.force_login(self.principal)
        response = self.client.post(reverse("hold_pdf", args=[pdf.id]))
        self.assertEqual(response.status_code, 302)
        pdf.refresh_from_db()
        self.assertEqual(pdf.status, ReferencePDF.Status.HOLD)

    def test_principal_can_manage_users(self):
        self.client.force_login(self.principal)
        response = self.client.get(reverse("view_users"))
        self.assertEqual(response.status_code, 200)

    def test_faculty_can_upload(self):
        self.client.force_login(self.faculty)
        with patch("chatbot.views.PyPDF2.PdfReader") as mock_reader, patch(
            "chatbot.views.queue_reference_pdf_processing",
            return_value={"queued": True, "task_id": "task-faculty"},
        ):
            page = Mock()
            page.extract_text.return_value = "faculty upload content"
            mock_reader.return_value.pages = [page]
            response = self.client.post(
                reverse("upload_pdf"),
                data=self._upload_payload("Faculty Upload"),
            )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ReferencePDF.objects.filter(
                uploaded_by=self.faculty,
                title="Faculty Upload",
            ).exists()
        )

    def test_faculty_cannot_approve(self):
        pdf = ReferencePDF.objects.create(
            subject=self.subject,
            uploaded_by=self.faculty,
            title="Faculty Pending PDF",
            file=SimpleUploadedFile("pending_faculty.pdf", b"%PDF-1.4"),
            extracted_text="pending",
            status=ReferencePDF.Status.HOLD,
            is_syllabus_reference=False,
        )
        self.client.force_login(self.faculty)
        response = self.client.post(reverse("approve_pdf", args=[pdf.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("user_dashboard"))
        pdf.refresh_from_db()
        self.assertEqual(pdf.status, ReferencePDF.Status.HOLD)
        self.assertFalse(pdf.is_syllabus_reference)

    def test_student_cannot_upload(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("upload_pdf"),
            data=self._upload_payload("Student Upload"),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("user_dashboard"))
        self.assertFalse(ReferencePDF.objects.filter(title="Student Upload").exists())

    def test_student_cannot_approve(self):
        pdf = ReferencePDF.objects.create(
            subject=self.subject,
            uploaded_by=self.faculty,
            title="Student Pending PDF",
            file=SimpleUploadedFile("pending_student.pdf", b"%PDF-1.4"),
            extracted_text="pending",
            status=ReferencePDF.Status.HOLD,
            is_syllabus_reference=False,
        )
        self.client.force_login(self.student)
        response = self.client.post(reverse("approve_pdf", args=[pdf.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("user_dashboard"))
        pdf.refresh_from_db()
        self.assertEqual(pdf.status, ReferencePDF.Status.HOLD)
        self.assertFalse(pdf.is_syllabus_reference)

    def test_student_cannot_access_admin_endpoints(self):
        self.client.force_login(self.student)
        protected_urls = [
            reverse("dashboard"),
            reverse("view_users"),
            reverse("add_subject"),
            reverse("view_subjects"),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse("user_dashboard"))
