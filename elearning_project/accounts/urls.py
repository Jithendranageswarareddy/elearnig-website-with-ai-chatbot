from django.urls import path
from .views import (
    index,
    dashboard_view,
    logout_view,
    register,
    user_login,
    user_dashboard,
    user_logout,
    view_users,
    delete_user,
    audit_logs,
    student_activity_view,
)

urlpatterns = [
    path('', index, name="index"),

    # Admin
    path('dashboard/', dashboard_view, name="dashboard"),
    path('logout/', logout_view, name="logout"),

    # Learner
    path('register/', register, name="register"),
    path('login/', user_login, name="login"),
    path('user-login/', user_login, name="user_login"),
    path('user-dashboard/', user_dashboard, name="user_dashboard"),
    path('principal-dashboard/', dashboard_view, name='principal_dashboard'),
    path('faculty-dashboard/', user_dashboard, name='faculty_dashboard'),
    path('student-dashboard/', user_dashboard, name='student_dashboard'),
    path('user-logout/', user_logout, name="user_logout"),
    path('view-users/', view_users, name='view_users'),
    path('delete-user/<int:user_id>/', delete_user, name='delete_user'),
    path('audit-logs/', audit_logs, name='audit_logs'),
    path('student-activity/', student_activity_view, name='student_activity'),
]
