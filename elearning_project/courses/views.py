from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.audit import log_system_event
from accounts.decorators import faculty_required, principal_required
from progress.models import LessonProgress

from .models import Bookmark, History, Lesson, Semester, Subject, Unit


def _ensure_subject_lessons(subject):
    lessons_qs = Lesson.objects.filter(subject=subject, is_active=True)
    if lessons_qs.exists():
        return lessons_qs.order_by("order")

    units = Unit.objects.filter(subject=subject, is_active=True).order_by("unit_number")
    for unit in units:
        Lesson.objects.get_or_create(
            subject=subject,
            order=unit.unit_number,
            defaults={
                "unit": unit,
                "title": unit.title or f"Unit {unit.unit_number}",
                "content": unit.content or f"Introduction to {subject.name} - Unit {unit.unit_number}",
                "is_active": True,
            },
        )

    return Lesson.objects.filter(subject=subject, is_active=True).order_by("order")


@login_required(login_url="user_login")
@principal_required
def add_subject(request):
    semesters = Semester.objects.filter(is_active=True)
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        semester_id = request.POST.get("semester_id")
        subject_code = request.POST.get("subject_code")
        if not all([name, description, semester_id]):
            messages.error(request, "Please complete all required subject fields.")
            return render(request, "add_subject.html", {"semesters": semesters})

        semester = get_object_or_404(Semester, id=semester_id, is_active=True)
        subject = Subject.objects.create(
            name=name,
            description=description,
            semester=semester,
            subject_code=subject_code,
            is_active=True,
        )
        messages.success(request, "Subject added successfully.")
        log_system_event(
            user=request.user,
            action_type="UPLOAD",
            object_type="Subject",
            object_id=subject.id,
            metadata={"semester_id": semester.id, "subject_code": subject.subject_code},
        )
        return redirect("view_subjects")
    return render(request, "add_subject.html", {"semesters": semesters})


@login_required(login_url="user_login")
@principal_required
def view_subjects(request):
    subjects_qs = Subject.objects.filter(is_active=True, semester__is_active=True).select_related("semester")
    ordered_subjects = sorted(subjects_qs, key=lambda subject: (subject.semester.number, subject.name))
    semester_map = {}
    for subject in ordered_subjects:
        semester_map.setdefault(subject.semester.id, {"semester": subject.semester, "subjects": []})["subjects"].append(subject)
    semester_groups = [semester_map[key] for key in sorted(semester_map.keys(), key=lambda sid: semester_map[sid]["semester"].number)]
    return render(request, "view_subjects.html", {"semester_groups": semester_groups})


@login_required(login_url="user_login")
@faculty_required
def add_lesson(request):
    subjects = Subject.objects.filter(is_active=True, semester__is_active=True)

    if request.method == "POST":
        subject_id = request.POST.get("subject_id")
        title = request.POST.get("title")
        content = request.POST.get("content")
        order = request.POST.get("order")
        if not all([subject_id, title, content, order]):
            messages.error(request, "Please complete all required lesson fields.")
            return render(request, "add_lesson.html", {"subjects": subjects})

        subject = get_object_or_404(
            Subject,
            id=subject_id,
            is_active=True,
            semester__is_active=True,
        )

        try:
            order_value = int(order)
        except (TypeError, ValueError):
            messages.error(request, "Lesson order must be a number.")
            return render(request, "add_lesson.html", {"subjects": subjects})

        if Lesson.objects.filter(subject=subject, order=order_value, is_active=True).exists():
            messages.error(request, "A lesson with this order already exists for the selected subject.")
            return render(request, "add_lesson.html", {"subjects": subjects})

        lesson = Lesson.objects.create(
            subject=subject,
            title=title,
            content=content,
            order=order_value,
            is_active=True,
        )

        messages.success(request, "Lesson added successfully.")
        log_system_event(
            user=request.user,
            action_type="UPLOAD",
            object_type="Lesson",
            object_id=lesson.id,
            metadata={"subject_id": subject.id, "order": lesson.order},
        )
        return redirect("view_lessons")

    return render(request, "add_lesson.html", {"subjects": subjects})


@login_required(login_url="user_login")
@faculty_required
def view_lessons(request):
    lessons_qs = Lesson.objects.filter(
        is_active=True,
        subject__is_active=True,
        subject__semester__is_active=True,
    ).select_related("subject", "subject__semester").order_by("subject__name", "order")
    page_obj = Paginator(lessons_qs, 20).get_page(request.GET.get("page"))
    return render(request, "view_lessons.html", {"lessons": page_obj})


def learn_subjects(request):
    semesters = Semester.objects.filter(is_active=True).order_by("number")
    subjects_qs = Subject.objects.filter(is_active=True, semester__is_active=True).select_related("semester")
    sem_id = request.GET.get("semester")
    if sem_id:
        subjects_qs = subjects_qs.filter(semester_id=sem_id)
    ordered_subjects = sorted(
        subjects_qs,
        key=lambda subject: (
            subject.semester.number,
            0 if len(subject.subject_code or "") >= 6 and subject.subject_code[5] == "T" else 1,
            subject.subject_code or "",
            subject.name,
        ),
    )
    page_obj = Paginator(ordered_subjects, 60).get_page(request.GET.get("page"))

    semester_groups = []
    grouped = {}
    for subject in page_obj.object_list:
        grouped.setdefault(subject.semester.id, {"semester": subject.semester, "subjects": []})["subjects"].append(subject)
    for semester in semesters:
        if semester.id in grouped:
            semester_groups.append(grouped[semester.id])

    return render(
        request,
        "learn_subjects.html",
        {
            "subjects": page_obj,
            "semesters": semesters,
            "selected_semester": sem_id,
            "semester_groups": semester_groups,
        },
    )


@login_required(login_url="user_login")
def read_lesson(request, lesson_id):
    from chatbot.models import ReferencePDF

    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        is_active=True,
        subject__is_active=True,
        subject__semester__is_active=True,
    )
    pdfs = ReferencePDF.objects.filter(
        lesson=lesson,
        is_active=True,
    )
    is_bookmarked = Bookmark.objects.filter(user=request.user, lesson=lesson).exists()
    is_completed = LessonProgress.objects.filter(
        user=request.user,
        lesson=lesson,
        completed=True,
    ).exists()
    return render(
        request,
        "read_lesson.html",
        {
            "lesson": lesson,
            "pdfs": pdfs,
            "is_bookmarked": is_bookmarked,
            "is_completed": is_completed,
        },
    )


def learn_lessons_with_progress(request, subject_id):
    subject = get_object_or_404(
        Subject,
        id=subject_id,
        is_active=True,
        semester__is_active=True,
    )
    lessons = _ensure_subject_lessons(subject)

    total_lessons = lessons.count()
    completed_lessons = LessonProgress.objects.filter(
        lesson__in=lessons,
        completed=True,
        user=request.user,
    ).count() if request.user.is_authenticated else 0
    progress_percent = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0

    return render(
        request,
        "learn_lessons.html",
        {
            "subject": subject,
            "lessons": lessons,
            "progress_percent": progress_percent,
            "completed_lessons": completed_lessons,
            "total_lessons": total_lessons,
        },
    )


def search_lessons(request):
    query = request.GET.get("q")
    results = []
    if query:
        results = Lesson.objects.filter(
            title__icontains=query,
            is_active=True,
            subject__is_active=True,
            subject__semester__is_active=True,
        )
    return render(request, "search.html", {"results": results})


@login_required(login_url="user_login")
@require_POST
def track_lesson_view(request, lesson_id):
    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        is_active=True,
        subject__is_active=True,
        subject__semester__is_active=True,
    )
    History.objects.create(user=request.user, lesson=lesson)
    return redirect(request.POST.get("next") or f"/lesson/{lesson.id}/")


@login_required(login_url="user_login")
@require_POST
def add_bookmark(request, lesson_id):
    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        is_active=True,
        subject__is_active=True,
        subject__semester__is_active=True,
    )
    Bookmark.objects.get_or_create(user=request.user, lesson=lesson)
    return redirect(request.POST.get("next") or f"/lesson/{lesson.id}/")


@login_required(login_url="user_login")
def view_bookmarks(request):
    bookmarks = Bookmark.objects.filter(
        user=request.user,
        lesson__is_active=True,
        lesson__subject__is_active=True,
        lesson__subject__semester__is_active=True,
    )
    return render(request, "bookmarks.html", {"bookmarks": bookmarks})


@login_required(login_url="user_login")
def view_history(request):
    history = History.objects.filter(
        user=request.user,
        lesson__is_active=True,
        lesson__subject__is_active=True,
        lesson__subject__semester__is_active=True,
    ).order_by("-viewed_at")
    return render(request, "history.html", {"history": history})


@login_required(login_url="user_login")
@principal_required
def delete_subject(request, subject_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    subject = get_object_or_404(Subject, id=subject_id)
    if not subject.is_active:
        messages.warning(request, "Subject is already inactive.")
        return redirect("view_subjects")

    subject.is_active = False
    subject.save(update_fields=["is_active"])
    Lesson.objects.filter(subject=subject, is_active=True).update(is_active=False)
    messages.success(request, "Subject archived successfully.")
    log_system_event(
        user=request.user,
        action_type="DELETE",
        object_type="Subject",
        object_id=subject.id,
        metadata={"soft_delete": True},
    )
    return redirect("view_subjects")


@login_required(login_url="user_login")
@faculty_required
def delete_lesson(request, lesson_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    lesson = get_object_or_404(Lesson, id=lesson_id)
    if not lesson.is_active:
        messages.warning(request, "Lesson is already inactive.")
        return redirect("view_lessons")

    lesson.is_active = False
    lesson.save(update_fields=["is_active"])
    messages.success(request, "Lesson archived successfully.")
    log_system_event(
        user=request.user,
        action_type="DELETE",
        object_type="Lesson",
        object_id=lesson.id,
        metadata={"soft_delete": True},
    )
    return redirect("view_lessons")
