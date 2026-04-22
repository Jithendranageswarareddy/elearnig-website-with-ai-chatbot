import logging
import re

from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings


logger = logging.getLogger(__name__)
SUBJECT_CODE_PATTERN = re.compile(r"^\d{2}[A-Z]{2}\d[TP]\d{2}$")


class Semester(models.Model):
    number = models.PositiveSmallIntegerField()  # 1 through 8
    regulation = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["number", "regulation"]
        constraints = [
            models.UniqueConstraint(
                fields=["number", "regulation"],
                name="unique_semester_identity",
            )
        ]

    def __str__(self):
        return f"Semester {self.number} ({self.regulation})"


class Subject(models.Model):
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subjects",
    )
    branch = models.CharField(max_length=10, blank=True, null=True)
    subject_code = models.CharField(max_length=50, blank=True, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["semester__number", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(semester__isnull=False),
                name="subject_requires_semester",
            ),
            models.UniqueConstraint(
                fields=["semester", "name"],
                name="unique_subject_per_semester",
            )
        ]
        indexes = [
            models.Index(fields=["semester", "is_active"]),
        ]

    @property
    def subject_type(self):
        code = (self.subject_code or "").strip().upper()
        if len(code) >= 6 and code[5] in {"T", "P"}:
            return code[5]
        return ""

    def clean(self):
        super().clean()
        code = (self.subject_code or "").strip().upper()
        self.subject_code = code
        if code and not SUBJECT_CODE_PATTERN.fullmatch(code):
            raise ValidationError(
                {
                    "subject_code": "Subject code must match format YYBBSTNN (e.g., 20CS1T01)."
                }
            )

    def _theory_unit_count_warning(self):
        if not self.pk:
            return ""
        if self.subject_type != "T":
            return ""
        active_units = self.units.filter(is_active=True).count()
        if active_units != 5:
            return (
                f"Theory subject '{self.subject_code or self.name}' should have exactly 5 active units; "
                f"currently has {active_units}."
            )
        return ""

    def save(self, *args, **kwargs):
        code = (self.subject_code or "").strip().upper()
        self.subject_code = code

        if code and not self.branch:
            try:
                self.branch = code[2:4] or None
            except Exception as e:
                print("ERROR:", str(e))
                pass

        if code and not self.semester_id:
            try:
                sem_number = int(code[4])
                candidates = Semester.objects.filter(number=sem_number)
                regulation_hint = code[:2]
                if regulation_hint:
                    narrowed = candidates.filter(regulation__icontains=regulation_hint)
                    if narrowed.count() == 1:
                        self.semester = narrowed.first()
                    elif candidates.count() == 1:
                        self.semester = candidates.first()
                elif candidates.count() == 1:
                    self.semester = candidates.first()
            except Exception as e:
                print("ERROR:", str(e))
                pass

        warning = self._theory_unit_count_warning()
        if warning:
            logger.warning(warning)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Unit(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="units",
    )
    unit_number = models.IntegerField()
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["subject", "unit_number"]
        unique_together = ("subject", "unit_number")
        indexes = [models.Index(fields=["subject", "unit_number"])]

    def __str__(self):
        return f"{self.subject.name} - Unit {self.unit_number}: {self.title}"


class Lesson(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="lessons")
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lessons",
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["subject", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "order"],
                name="unique_lesson_order_per_subject",
            )
        ]
        indexes = [models.Index(fields=["subject", "order"])]

    def __str__(self):
        return self.title


class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="bookmarks")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "lesson"],
                name="unique_bookmark_per_user_lesson",
            )
        ]


class History(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_history",
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="history_entries")
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-viewed_at"]
        indexes = [models.Index(fields=["user", "viewed_at"])]
