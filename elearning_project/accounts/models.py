from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email must be set")

        extra_fields.setdefault("role", "STUDENT")
        # Guard against None values from legacy callers/forms.
        raw_name = extra_fields.get("name")
        extra_fields["name"] = (raw_name or "").strip()
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "PRINCIPAL")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        PRINCIPAL = "PRINCIPAL", "Principal"
        FACULTY = "FACULTY", "Faculty"
        STUDENT = "STUDENT", "Student"

    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def is_principal(self):
        return self.role == self.Role.PRINCIPAL or self.is_superuser

    @property
    def is_faculty(self):
        return self.role == self.Role.FACULTY

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_faculty_or_principal(self):
        return self.is_principal or self.is_faculty

    def save(self, *args, **kwargs):
        # Defensive guard: never write NULL to the non-nullable name column.
        self.name = (self.name or "").strip()
        if self.is_superuser:
            self.role = self.Role.PRINCIPAL
            self.is_staff = True
        elif self.role in {self.Role.PRINCIPAL, self.Role.FACULTY}:
            self.is_staff = True
        else:
            self.is_staff = False
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or self.email


class SystemLog(models.Model):
    class ActionType(models.TextChoices):
        UPLOAD = "UPLOAD", "Upload"
        DELETE = "DELETE", "Delete"
        APPROVE = "APPROVE", "Approve"
        LOGIN = "LOGIN", "Login"
        CHAT_QUERY = "CHAT_QUERY", "Chat Query"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_logs",
    )
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action_type} by {self.user_id or 'anonymous'} at {self.timestamp}"
