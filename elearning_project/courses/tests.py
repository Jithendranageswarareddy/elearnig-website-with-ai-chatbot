from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Bookmark, History, Lesson, Semester, Subject


class CourseMutationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student@example.com",
            password="pass12345",
            name="Student",
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
            subject_code="CS101",
            name="Algorithms",
            description="Algorithms subject",
            is_active=True,
        )
        self.lesson = Lesson.objects.create(
            subject=self.subject,
            title="Sorting",
            content="Sorting content",
            order=1,
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_read_lesson_get_does_not_create_history(self):
        response = self.client.get(reverse("read_lesson", args=[self.lesson.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(History.objects.count(), 0)

    def test_track_lesson_view_requires_post(self):
        response = self.client.get(reverse("track_lesson_view", args=[self.lesson.id]))
        self.assertEqual(response.status_code, 405)

    def test_track_lesson_view_creates_history(self):
        response = self.client.post(
            reverse("track_lesson_view", args=[self.lesson.id]),
            data={"next": reverse("read_lesson", args=[self.lesson.id])},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(History.objects.count(), 1)

    def test_add_bookmark_requires_post(self):
        response = self.client.get(reverse("add_bookmark", args=[self.lesson.id]))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_add_bookmark_post_creates_single_bookmark(self):
        first = self.client.post(
            reverse("add_bookmark", args=[self.lesson.id]),
            data={"next": reverse("read_lesson", args=[self.lesson.id])},
        )
        second = self.client.post(
            reverse("add_bookmark", args=[self.lesson.id]),
            data={"next": reverse("read_lesson", args=[self.lesson.id])},
        )
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(Bookmark.objects.count(), 1)
