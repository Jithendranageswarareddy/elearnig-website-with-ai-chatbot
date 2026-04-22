from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from courses.models import Lesson

from .models import LessonProgress


@login_required(login_url="user_login")
@require_POST
def complete_lesson(request, lesson_id):
    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        is_active=True,
        subject__is_active=True,
        subject__semester__is_active=True,
    )
    progress, created = LessonProgress.objects.get_or_create(
        lesson=lesson,
        user=request.user,
    )
    progress.completed = True
    progress.save()
    return redirect(request.POST.get("next") or f"/learn/{lesson.subject.id}/")

