from django.db import models
from django.conf import settings
from courses.models import Lesson


class LessonProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progress_entries",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progress_entries",
    )
    completed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "lesson"],
                name="unique_lesson_progress_per_user_lesson",
            )
        ]
        indexes = [
            models.Index(fields=["user", "completed"]),
        ]
