from django.urls import path
from .views import complete_lesson

urlpatterns = [
    path('complete/<int:lesson_id>/', complete_lesson, name="complete_lesson"),
]
