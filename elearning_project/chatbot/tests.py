import os
import tempfile
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from courses.models import Lesson, Semester, Subject

from .models import (
    ChatQuery,
    ChunkConceptLink,
    ChunkEmbedding,
    ConceptNode,
    ConceptRelation,
    PDFPageChunk,
    ReferencePDF,
)
from .services.pdf_processor import (
    _extract_page_images,
    clean_page_text,
    process_pdf,
    split_page_into_paragraph_chunks,
)
from .views import detect_query_type
from .services.search_service import search_chunks, search_related_lessons
from .services.answer_service import generate_answer


class ChatbotTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="faculty@example.com",
            password="pass12345",
            name="Faculty",
            role=User.Role.FACULTY,
        )
        self.semester = Semester.objects.create(
            number=1,
            regulation="R2026",
            description="Semester",
            is_active=True,
        )
        self.subject = Subject.objects.create(
            semester=self.semester,
            subject_code="CS101",
            name="Data Structures",
            description="Core subject",
            is_active=True,
        )

    def create_reference_pdf(self, title, **overrides):
        defaults = {
            "subject": self.subject,
            "uploaded_by": self.user,
            "file": "pdfs/test.pdf",
            "extracted_text": "",
            "status": ReferencePDF.Status.APPROVED,
            "is_syllabus_reference": True,
        }
        defaults.update(overrides)
        return ReferencePDF.objects.create(title=title, **defaults)


class ParagraphChunkingTests(ChatbotTestCase):
    def test_clean_page_text_preserves_paragraph_boundaries(self):
        cleaned = clean_page_text(
            "First paragraph line one.\nFirst paragraph line two.\n\n"
            "Second paragraph line has enough characters to remain searchable.\n"
        )
        self.assertEqual(
            cleaned,
            "First paragraph line one. First paragraph line two.\n\n"
            "Second paragraph line has enough characters to remain searchable.",
        )
        self.assertEqual(
            split_page_into_paragraph_chunks(cleaned),
            [
                "First paragraph line one. First paragraph line two.",
                "Second paragraph line has enough characters to remain searchable.",
            ],
        )

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_process_pdf_creates_multiple_paragraph_chunks(self):
        pdf = self.create_reference_pdf(
            "Paragraph PDF",
            file=SimpleUploadedFile("paragraph.pdf", b"dummy pdf"),
        )
        page = Mock()
        page.extract_text.return_value = (
            "This is the first paragraph with enough characters to be indexed.\n"
            "It continues on the next line.\n\n"
            "Second paragraph is also longer than thirty characters for chunking."
        )

        with patch("chatbot.services.pdf_processor.PyPDF2.PdfReader") as mock_reader:
            mock_reader.return_value.pages = [page]
            process_pdf(pdf)

        chunks = list(
            PDFPageChunk.objects.filter(reference_pdf=pdf).order_by("page_number", "chunk_index")
        )
        self.assertEqual(len(chunks), 2)
        self.assertEqual(ChunkEmbedding.objects.filter(chunk__reference_pdf=pdf).count(), 2)
        self.assertTrue(ChunkConceptLink.objects.filter(chunk__reference_pdf=pdf).exists())
        self.assertEqual([chunk.chunk_index for chunk in chunks], [0, 1])
        self.assertIn("first paragraph", chunks[0].text_content.lower())
        self.assertIn("second paragraph", chunks[1].text_content.lower())

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_process_pdf_uses_ocr_when_native_text_is_empty(self):
        pdf = self.create_reference_pdf(
            "Scanned PDF",
            file=SimpleUploadedFile("scanned.pdf", b"dummy pdf"),
        )
        page = Mock()
        page.extract_text.return_value = ""
        ocr_document = Mock()

        with patch("chatbot.services.pdf_processor.PyPDF2.PdfReader") as mock_reader, patch(
            "chatbot.services.pdf_processor._open_ocr_document",
            return_value=ocr_document,
        ), patch(
            "chatbot.services.pdf_processor._ocr_page_text",
            return_value="OCR paragraph extracted from scanned syllabus content with enough detail.",
        ):
            mock_reader.return_value.pages = [page]
            process_pdf(pdf)

        chunk = PDFPageChunk.objects.get(reference_pdf=pdf)
        self.assertTrue(chunk.metadata["ocr_used"])
        self.assertEqual(chunk.metadata["source"], "ocr")
        self.assertIn("scanned syllabus", chunk.text_content.lower())
        ocr_document.close.assert_called_once()

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_process_pdf_persists_failed_status_when_reader_breaks(self):
        pdf = self.create_reference_pdf(
            "Broken PDF",
            file=SimpleUploadedFile("broken.pdf", b"dummy pdf"),
        )

        with patch(
            "chatbot.services.pdf_processor.PyPDF2.PdfReader",
            side_effect=ValueError("broken reader"),
        ):
            with self.assertRaises(ValueError):
                process_pdf(pdf)

        pdf.refresh_from_db()
        self.assertEqual(pdf.processing_status, ReferencePDF.ProcessingStatus.FAILED)
        self.assertIn("broken reader", pdf.processing_error)


class BalancedRetrievalTests(ChatbotTestCase):
    def test_balanced_retrieval_surfaces_relevant_chunk_from_late_pdf(self):
        reference_pdfs = [
            self.create_reference_pdf(f"PDF {index}")
            for index in range(1, 51)
        ]
        chunks = []
        for pdf_index, reference_pdf in enumerate(reference_pdfs, start=1):
            for page_number in range(1, 21):
                text = (
                    f"commonterm syllabus paragraph for pdf {pdf_index} page {page_number}. "
                    "This paragraph covers shared curriculum material."
                )
                if pdf_index == 50 and page_number == 20:
                    text += " audituniqueterm definitive capstone answer from the final syllabus document."
                chunks.append(
                    PDFPageChunk(
                        reference_pdf=reference_pdf,
                        page_number=page_number,
                        chunk_index=0,
                        text_content=text,
                        metadata={"source": "pdf_text"},
                    )
                )
        PDFPageChunk.objects.bulk_create(chunks)

        results = search_chunks("commonterm audituniqueterm")

        self.assertTrue(results)
        self.assertEqual(results[0].reference_pdf_id, reference_pdfs[-1].id)
        self.assertIn("audituniqueterm", results[0].text_content)

    def test_hybrid_ranking_uses_semantic_score_to_break_tfidf_ties(self):
        early_pdf = self.create_reference_pdf("Early PDF")
        late_pdf = self.create_reference_pdf("Late PDF")
        early_chunk = PDFPageChunk.objects.create(
            reference_pdf=early_pdf,
            page_number=1,
            chunk_index=0,
            text_content="Queue operations are described in the syllabus overview.",
            metadata={"source": "pdf_text"},
        )
        late_chunk = PDFPageChunk.objects.create(
            reference_pdf=late_pdf,
            page_number=4,
            chunk_index=1,
            text_content="This architecture structure section explains queue operations in detail.",
            metadata={"source": "pdf_text"},
        )

        with patch(
            "chatbot.services.search_service.embed_query",
            return_value=(1.0, 0.0),
        ), patch(
            "chatbot.services.search_service.embedding_map_for_chunk_ids",
            return_value={
                early_chunk.id: [0.0, 1.0],
                late_chunk.id: [1.0, 0.0],
            },
        ):
            results = search_chunks("queue operations design layout")

        self.assertTrue(results)
        self.assertEqual(results[0].id, late_chunk.id)

    def test_search_related_lessons_returns_internal_fallback_matches(self):
        Lesson.objects.create(
            subject=self.subject,
            title="Graph Traversal",
            content="Depth first search and breadth first search are lesson topics.",
            order=1,
            is_active=True,
        )

        lessons = search_related_lessons("graph search traversal")

        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0].title, "Graph Traversal")


class QueryAnalysisTests(TestCase):
    def test_detect_query_type(self):
        self.assertEqual(detect_query_type("What is a stack?"), "definition")
        self.assertEqual(detect_query_type("Compare stack and queue"), "comparison")
        self.assertEqual(detect_query_type("How to perform graph traversal?"), "procedure")
        self.assertEqual(detect_query_type("Give an example of recursion"), "example")
        self.assertEqual(detect_query_type("Explain recursion"), "explanation")


class ArchitectureViewTests(ChatbotTestCase):
    def test_principal_can_access_system_architecture(self):
        principal = User.objects.create_user(
            email="principal-arch@example.com",
            password="pass12345",
            name="Principal",
            role=User.Role.PRINCIPAL,
        )

        self.client.force_login(principal)
        response = self.client.get(reverse("system_architecture"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System Architecture")

    def test_non_principal_is_redirected_from_system_architecture(self):
        student = User.objects.create_user(
            email="student-arch@example.com",
            password="pass12345",
            name="Student",
            role=User.Role.STUDENT,
        )

        self.client.force_login(student)
        response = self.client.get(reverse("system_architecture"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("user_dashboard"))


class DiagramExtractionTests(ChatbotTestCase):
    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_diagram_extraction_reuses_same_file_for_duplicate_images(self):
        pdf = self.create_reference_pdf("Diagram PDF")
        duplicate_bytes = b"same-image-bytes"
        first_page = Mock()
        second_page = Mock()
        first_page.get_images.return_value = [(11,)]
        second_page.get_images.return_value = [(12,)]
        document = Mock()
        document.__iter__ = Mock(return_value=iter([first_page, second_page]))
        document.extract_image.side_effect = [
            {"image": duplicate_bytes, "ext": "png"},
            {"image": duplicate_bytes, "ext": "png"},
        ]

        fitz_stub = Mock()
        fitz_stub.open.return_value = document

        with patch("chatbot.services.pdf_processor.fitz", fitz_stub):
            _extract_page_images(pdf, "ignored.pdf")

        images = list(pdf.pdf_images.order_by("page_number", "id"))
        self.assertEqual(len(images), 2)
        self.assertEqual(images[0].image_hash, images[1].image_hash)
        self.assertEqual(images[0].image_path, images[1].image_path)


class UploadPipelineTests(ChatbotTestCase):
    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_upload_pdf_auto_approves_document_and_queues_processing(self):
        self.client.force_login(self.user)
        with patch("chatbot.views.PyPDF2.PdfReader") as mock_reader, patch(
            "chatbot.views.queue_reference_pdf_processing",
            return_value={"queued": True, "task_id": "task-1"},
        ) as mock_queue:
            page = Mock()
            page.extract_text.return_value = "Uploaded syllabus paragraph."
            mock_reader.return_value.pages = [page]

            response = self.client.post(
                reverse("upload_pdf"),
                data={
                    "title": "Uploaded Through View",
                    "subject_id": str(self.subject.id),
                    "file": SimpleUploadedFile("upload.pdf", b"%PDF-1.4"),
                },
            )

        self.assertEqual(response.status_code, 302)
        pdf = ReferencePDF.objects.get(title="Uploaded Through View")
        self.assertEqual(pdf.status, ReferencePDF.Status.APPROVED)
        self.assertTrue(pdf.is_syllabus_reference)
        self.assertEqual(pdf.extracted_text, "")
        mock_queue.assert_called_once_with(pdf, replace_existing=True)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_faculty_can_edit_and_delete_own_pdf(self):
        pdf = self.create_reference_pdf("Editable PDF")
        other_subject = Subject.objects.create(
            semester=self.semester,
            subject_code="CS102",
            name="Algorithms",
            description="Algorithms subject",
            is_active=True,
        )

        self.client.force_login(self.user)
        edit_response = self.client.post(
            reverse("edit_pdf", args=[pdf.id]),
            {"title": "Edited PDF", "subject_id": str(other_subject.id)},
        )
        self.assertEqual(edit_response.status_code, 302)
        pdf.refresh_from_db()
        self.assertEqual(pdf.title, "Edited PDF")
        self.assertEqual(pdf.subject_id, other_subject.id)

        delete_response = self.client.post(reverse("delete_pdf", args=[pdf.id]))
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(ReferencePDF.objects.filter(id=pdf.id).exists())


class ChatInteractionTests(ChatbotTestCase):
    def setUp(self):
        super().setUp()
        self.student = User.objects.create_user(
            email="student-chat@example.com",
            password="pass12345",
            name="Student Chat",
            role=User.Role.STUDENT,
        )
        self.pdf = self.create_reference_pdf("Chat PDF")
        self.chunk = PDFPageChunk.objects.create(
            reference_pdf=self.pdf,
            page_number=2,
            chunk_index=0,
            text_content="Stack is a linear data structure following LIFO order. Example: function calls use a stack.",
            metadata={"source": "pdf_text"},
        )

    def test_curriculum_chat_reuses_cached_response(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("curriculum_chat"),
            data={"question": "What is stack?", "subject_id": str(self.subject.id)},
        )
        self.assertEqual(response.status_code, 200)

        with patch("chatbot.views.search_chunks", side_effect=AssertionError("cache should be used")):
            cached_response = self.client.post(
                reverse("curriculum_chat"),
                data={"question": "What is stack?", "subject_id": str(self.subject.id)},
            )

        self.assertEqual(cached_response.status_code, 200)
        self.assertContains(cached_response, "Detailed Explanation")

    @patch("chatbot.views.search_chunks")
    def test_curriculum_chat_uses_rewritten_query_for_retrieval(self, mock_search_chunks):
        self.client.force_login(self.student)
        mock_search_chunks.return_value = [self.chunk]

        response = self.client.post(
            reverse("curriculum_chat"),
            data={"question": "Please explain OOP and polymorphism", "subject_id": str(self.subject.id)},
        )

        self.assertEqual(response.status_code, 200)
        called_query = mock_search_chunks.call_args.args[0]
        self.assertIn("object oriented programming", called_query.lower())
        self.assertIn("polymorphism", called_query.lower())

    @override_settings(CHAT_RATE_LIMIT_COUNT=1, CHAT_RATE_LIMIT_WINDOW=60)
    def test_curriculum_chat_rate_limits_requests(self):
        cache.clear()
        self.client.force_login(self.student)
        first = self.client.post(
            reverse("curriculum_chat"),
            data={"question": "What is stack?", "subject_id": str(self.subject.id)},
        )
        second = self.client.post(
            reverse("curriculum_chat"),
            data={"question": "Explain stack again", "subject_id": str(self.subject.id)},
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertContains(second, "rate limit", status_code=429)

    def test_student_cannot_access_unapproved_secure_pdf(self):
        self.client.force_login(self.student)
        pdf = self.create_reference_pdf("Restricted PDF", status=ReferencePDF.Status.HOLD)

        response = self.client.get(reverse("serve_reference_pdf", args=[pdf.id]))

        self.assertEqual(response.status_code, 403)

    def test_curriculum_chat_history_handles_malformed_pagination(self):
        self.client.force_login(self.student)

        ChatQuery.objects.create(
            user=self.student,
            subject=self.subject,
            reference_pdf=self.pdf,
            question="Sample question",
            normalized_question="sample question",
            strict_mode=True,
            result_count=1,
            result_reference_ids=[self.pdf.id],
            related_concepts=["Stack"],
            response_text="Sample response",
        )

        response = self.client.get(reverse("curriculum_chat_history") + "?page=abc&page_size=xyz")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 20)
        self.assertEqual(payload["total_items"], 1)

    @patch("chatbot.views.search_chunks")
    def test_chatbot_rejects_out_of_syllabus_questions(self, mock_search_chunks):
        self.client.force_login(self.student)
        mock_search_chunks.return_value = []

        response = self.client.post(
            reverse("curriculum_chat"),
            data={"question": "Explain black hole thermodynamics", "subject_id": str(self.subject.id)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "The approved syllabus materials do not contain sufficient information to answer this question.",
        )
