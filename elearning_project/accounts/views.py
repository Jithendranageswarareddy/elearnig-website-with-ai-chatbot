from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from .models import SystemLog, User
from .decorators import principal_required
from .audit import log_system_event
from courses.models import Lesson, Subject


def principal_dashboard_metrics():
    from chatbot.models import ChatQuery, ReferencePDF
    from django.utils import timezone
    from datetime import timedelta
    
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)

    pdf_aggregate = ReferencePDF.objects.filter(is_active=True).aggregate(
        total_pdfs=Count("id"),
        pending_pdfs=Count(
            "id",
            filter=Q(processing_status=getattr(ReferencePDF.ProcessingStatus, "PENDING", "PENDING")),
        ),
    )
    query_aggregate = ChatQuery.objects.aggregate(
        queries_today=Count("id", filter=Q(created_at__date=today)),
        queries_this_week=Count("id", filter=Q(created_at__date__gte=last_7_days)),
    )
    
    return {
        "total_lessons": Lesson.objects.filter(is_active=True).count(),
        "total_pdfs": pdf_aggregate["total_pdfs"],
        "pending_pdfs": pdf_aggregate["pending_pdfs"],
        "queries_today": query_aggregate["queries_today"],
        "queries_this_week": query_aggregate["queries_this_week"],
        "active_students": User.objects.filter(role=User.Role.STUDENT, is_active=True).count(),
        "student_activity": [],
    }


def faculty_dashboard_metrics(user):
    from chatbot.models import ChatQuery, ReferencePDF
    from django.utils import timezone
    from datetime import timedelta
    
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)

    my_pdf_aggregate = ReferencePDF.objects.filter(uploaded_by=user).aggregate(
        my_pdfs=Count("id"),
        my_approved_pdfs=Count("id", filter=Q(status=ReferencePDF.Status.APPROVED)),
        failed_processing_pdfs=Count(
            "id",
            filter=Q(processing_status=getattr(ReferencePDF.ProcessingStatus, "FAILED", "FAILED")),
        ),
    )
    query_aggregate = ChatQuery.objects.aggregate(
        queries_today=Count("id", filter=Q(created_at__date=today)),
        queries_this_week=Count("id", filter=Q(created_at__date__gte=last_7_days)),
    )
    
    return {
        "total_lessons": Lesson.objects.filter(is_active=True).count(),
        "my_pdfs": my_pdf_aggregate["my_pdfs"],
        "my_approved_pdfs": my_pdf_aggregate["my_approved_pdfs"],
        "queries_today": query_aggregate["queries_today"],
        "queries_this_week": query_aggregate["queries_this_week"],
        "failed_processing_pdfs": my_pdf_aggregate["failed_processing_pdfs"],
        "student_activity": [],
    }


def student_dashboard_metrics(user):
    from chatbot.models import ChatQuery
    from progress.models import LessonProgress
    from django.utils import timezone
    
    today = timezone.now().date()
    progress_aggregate = LessonProgress.objects.filter(user=user).aggregate(
        lessons_started=Count("id"),
        lessons_completed=Count("id", filter=Q(completed=True)),
    )
    chat_aggregate = ChatQuery.objects.filter(user=user).aggregate(
        my_queries_today=Count("id", filter=Q(created_at__date=today)),
        my_total_queries=Count("id"),
    )
    
    return {
        "total_lessons": Lesson.objects.filter(is_active=True).count(),
        "lessons_started": progress_aggregate["lessons_started"],
        "lessons_completed": progress_aggregate["lessons_completed"],
        "my_queries_today": chat_aggregate["my_queries_today"],
        "my_total_queries": chat_aggregate["my_total_queries"],
        "student_activity": [],
    }


def _dashboard_template_for(user):
    if user.is_principal:
        return "principal_dashboard.html"
    if user.is_faculty:
        return "faculty_dashboard.html"
    return "student_dashboard.html"


def _dashboard_context_for(user):
    from chatbot.models import ChatQuery, ReferencePDF
    from courses.models import Bookmark, History
    from progress.models import LessonProgress
    from django.utils import timezone
    from datetime import timedelta
    
    if user.is_principal:
        context = principal_dashboard_metrics()
        from chatbot.models import ReferencePDF, ChatQuery
        faculty_activity = (
            ReferencePDF.objects.filter(is_active=True)
            .values("uploaded_by__email")
            .annotate(upload_count=Count("id"))
            .order_by("-upload_count")[:8]
        )
        top_subject_queries = (
            ChatQuery.objects.filter(subject__isnull=False)
            .values("subject__name")
            .annotate(query_count=Count("id"))
            .order_by("-query_count")[:8]
        )
        pdf_status_aggregate = ReferencePDF.objects.filter(is_active=True).aggregate(
            approved_pdfs=Count("id", filter=Q(status=ReferencePDF.Status.APPROVED)),
            held_pdfs=Count("id", filter=Q(status=ReferencePDF.Status.HOLD)),
            failed_processing_pdfs=Count(
                "id",
                filter=Q(processing_status=getattr(ReferencePDF.ProcessingStatus, "FAILED", "FAILED")),
            ),
        )
        
        # Add comprehensive principal metrics
        context.update({
            "total_pdfs": context.get("total_pdfs", 0),
            "approved_pdfs": pdf_status_aggregate["approved_pdfs"],
            "held_pdfs": pdf_status_aggregate["held_pdfs"],
            "failed_processing_pdfs": pdf_status_aggregate["failed_processing_pdfs"],
            "total_subjects": Subject.objects.filter(is_active=True).count(),
            "total_students": User.objects.filter(role=User.Role.STUDENT, is_active=True).count(),
            "total_chatbot_queries": ChatQuery.objects.count(),
            "daily_usage_today": context.get("queries_today", 0),
            "daily_usage_last_week": context.get("queries_this_week", 0),
            "total_concepts": 0,  # Placeholder for concept nodes
            "completed_progress": 0,
            "in_progress": 0,
            "pending_progress": context.get("total_lessons", 0),
            "faculty_activity": faculty_activity,
            "top_subject_queries": top_subject_queries,
        })
        return context
        
    if user.is_faculty:
        context = faculty_dashboard_metrics(user)
        pending_approval_pdfs = ReferencePDF.objects.filter(
            uploaded_by=user,
            is_active=True,
        ).exclude(status=ReferencePDF.Status.APPROVED).order_by("-uploaded_at")[:8]
        
        # Add faculty-specific metrics
        context.update({
            "uploaded_pdfs": context.get("my_pdfs", 0),
            "approved_pdfs": context.get("my_approved_pdfs", 0),
            "on_hold_pdfs": ReferencePDF.objects.filter(uploaded_by=user, status=ReferencePDF.Status.HOLD).count(),
            "failed_processing": context.get("failed_processing_pdfs", 0),
            "chatbot_usage_count": context.get("queries_this_week", 0),
            "recent_uploaded_pdfs": ReferencePDF.objects.filter(uploaded_by=user).order_by("-uploaded_at")[:5],
            "pending_approval_pdfs": pending_approval_pdfs,
        })
        return context
        
    # Student dashboard
    context = student_dashboard_metrics(user)
    subject_progress_rows = []
    subject_progress_qs = (
        Subject.objects.filter(is_active=True, semester__is_active=True)
        .annotate(
            total_lessons=Count("lessons", filter=Q(lessons__is_active=True), distinct=True),
            completed_lessons=Count(
                "lessons__progress_entries",
                filter=Q(
                    lessons__progress_entries__user=user,
                    lessons__progress_entries__completed=True,
                ),
                distinct=True,
            ),
        )
        .order_by("name")
    )

    for item in subject_progress_qs:
        total_lessons = int(item.total_lessons or 0)
        completed_lessons = int(item.completed_lessons or 0)
        progress_percent = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0
        subject_progress_rows.append(
            {
                "subject_name": item.name,
                "subject_code": item.subject_code,
                "total_lessons": total_lessons,
                "completed_lessons": completed_lessons,
                "progress_percent": progress_percent,
            }
        )

    weak_areas = sorted(
        [row for row in subject_progress_rows if row["total_lessons"] > 0],
        key=lambda row: (row["progress_percent"], row["subject_name"]),
    )[:5]

    recent_viewed_topics = (
        History.objects.filter(
            user=user,
            lesson__is_active=True,
            lesson__subject__is_active=True,
            lesson__subject__semester__is_active=True,
        )
        .select_related("lesson", "lesson__subject")
        .order_by("-viewed_at")[:8]
    )

    performance_queries = (
        ChatQuery.objects.filter(user=user, subject__isnull=False)
        .values("subject__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:8]
    )

    context.update({
        "enrolled_subjects": Subject.objects.filter(is_active=True).count(),
        "completed_lessons": context.get("lessons_completed", 0),
        "incomplete_lessons": context.get("lessons_started", 0) - context.get("lessons_completed", 0),
        "bookmarked_lessons_count": Bookmark.objects.filter(user=user).count(),
        "recent_questions": ChatQuery.objects.filter(user=user).order_by("-created_at")[:10],
        "bookmarked_lessons": Bookmark.objects.filter(user=user).select_related("lesson").order_by("-id")[:5],
        "most_viewed_lessons": Lesson.objects.filter(is_active=True).order_by("-id")[:5],
        "recent_viewed_topics": recent_viewed_topics,
        "subject_progress_rows": subject_progress_rows,
        "weak_areas": weak_areas,
        "performance_queries": performance_queries,
    })
    return context


def _render_dashboard(request):
    template_name = _dashboard_template_for(request.user)
    context = _dashboard_context_for(request.user)
    return render(request, template_name, context)


@login_required(login_url='user_login')
@principal_required
def dashboard_view(request):
    return _render_dashboard(request)


@login_required(login_url='user_login')
@principal_required
@require_POST
def logout_view(request):
    user = request.user
    logout(request)
    messages.success(request, "You have been logged out.")
    log_system_event(
        user=user,
        action_type="LOGIN",
        object_type="UserSession",
        object_id=user.id,
        metadata={"event": "logout", "route": "logout_view"},
    )
    return redirect('user_login')

def index(request):
    return render(request, 'index.html')


def register(request):
    if request.method == "POST":
        name = (request.POST.get("name") or request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        role = (request.POST.get("role") or "").strip()

        valid_roles = {choice[0] for choice in User.Role.choices}

        if not email or not password:
            messages.error(request, "Email and password are required.")
            return render(request, "register.html")

        if not role:
            messages.error(request, "Please select a role")
            return redirect("register")

        if role not in valid_roles:
            messages.error(request, "Invalid role selected.")
            return redirect("register")

        if password2 is not None and password != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, "register.html")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return render(request, "register.html", {"error": "Email already exists"})

        if not name:
            name = email.split("@")[0]

        user = User.objects.create_user(
            email=email,
            password=password,
            name=name,
            role=role,
            is_staff=False,
            is_superuser=False,
        )

        messages.success(request, "Registration successful. Please log in.")
        return redirect("user_login")

    return render(request, "register.html")


def user_login(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Login successful.")
            log_system_event(
                user=user,
                action_type="LOGIN",
                object_type="UserSession",
                object_id=user.id,
                metadata={"event": "login", "route": "user_login"},
            )
            if user.role == User.Role.PRINCIPAL:
                return redirect("principal_dashboard")
            if user.role == User.Role.FACULTY:
                return redirect("faculty_dashboard")
            return redirect("student_dashboard")
        else:
            messages.error(request, "Invalid credentials.")
            return render(request, "user_login.html", {"error": "Invalid credentials"})

    return render(request, "user_login.html")


@login_required(login_url='user_login')
def user_dashboard(request):
    return _render_dashboard(request)


@login_required(login_url='user_login')
@require_POST
def user_logout(request):
    user = request.user if request.user.is_authenticated else None
    logout(request)
    messages.success(request, "You have been logged out.")
    if user:
        log_system_event(
            user=user,
            action_type="LOGIN",
            object_type="UserSession",
            object_id=user.id,
            metadata={"event": "logout", "route": "user_logout"},
        )
    return redirect("index")


@login_required(login_url='user_login')
@principal_required
def view_users(request):
    users = User.objects.filter(is_active=True)
    return render(request, "view_users.html", {"users": users})


@login_required(login_url='user_login')
@principal_required
def audit_logs(request):
    logs = SystemLog.objects.select_related("user").all()[:100]
    return render(request, "audit_logs.html", {"logs": logs})


@login_required(login_url='user_login')
@principal_required
def student_activity_view(request):
    context = {
        "student_activity": principal_dashboard_metrics()["student_activity"],
    }
    return render(request, "student_activity.html", context)


@login_required(login_url='user_login')
@principal_required
def delete_user(request, user_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = get_object_or_404(User, id=user_id)
    if not user.is_active:
        messages.warning(request, "User is already inactive.")
        return redirect("view_users")

    if request.user.is_superuser and request.user.id == user.id:
        messages.warning(request, "Superuser cannot deactivate their own account.")
        return redirect("view_users")

    user.is_active = False
    user.save(update_fields=["is_active"])
    messages.success(request, "User archived successfully.")
    log_system_event(
        user=request.user,
        action_type="DELETE",
        object_type="User",
        object_id=user.id,
        metadata={"soft_delete": True, "target_role": user.role},
    )
    return redirect("view_users")
