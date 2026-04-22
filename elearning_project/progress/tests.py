from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from courses.models import Lesson, Semester, Subject

from .models import LessonProgress


class LessonProgressMutationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="studentprogress@example.com",
            password="pass12345",
            name="Student Progress",
            role=User.Role.STUDENT,
        )
        self.semester = Semester.objects.create(
            number=1,
            regulation="R2026",
            description="Test semester",
            is_active=True,
        )
        self.subject = Subject.objects.create(
            semester=self.semester,
            subject_code="CS102",
            name="Data Structures",
            description="Structures subject",
            is_active=True,
        )
        self.lesson = Lesson.objects.create(
            subject=self.subject,
            title="Stacks",
            content="Stacks lesson",
            order=1,
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_complete_lesson_requires_post(self):
        response = self.client.get(reverse("complete_lesson", args=[self.lesson.id]))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(LessonProgress.objects.count(), 0)

    def test_complete_lesson_post_marks_single_progress_row(self):
        first = self.client.post(
            reverse("complete_lesson", args=[self.lesson.id]),
            data={"next": reverse("read_lesson", args=[self.lesson.id])},
        )
        second = self.client.post(
            reverse("complete_lesson", args=[self.lesson.id]),
            data={"next": reverse("read_lesson", args=[self.lesson.id])},
        )
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(LessonProgress.objects.count(), 1)
        self.assertTrue(LessonProgress.objects.get().completed)
