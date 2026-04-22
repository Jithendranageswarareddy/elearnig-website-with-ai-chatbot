from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def _is_authenticated_with_role(user, allowed_roles):
    return user.is_authenticated and getattr(user, "role", None) in allowed_roles


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if _is_authenticated_with_role(request.user, allowed_roles):
                return view_func(request, *args, **kwargs)
            if not request.user.is_authenticated:
                messages.warning(request, "Please log in to continue.")
                return redirect("user_login")
            messages.warning(request, "You do not have permission to access that page.")
            return redirect("user_dashboard")

        return _wrapped_view

    return decorator


principal_required = role_required("PRINCIPAL")
faculty_required = role_required("FACULTY", "PRINCIPAL")
student_required = role_required("STUDENT")
