from django.urls import path
from .views import (
    add_subject,
    view_subjects,
    add_lesson,
    view_lessons,
    learn_subjects,
    learn_lessons_with_progress,
    read_lesson,
    search_lessons,
    add_bookmark,
    track_lesson_view,
    view_bookmarks,
    view_history,
    delete_subject,
    delete_lesson,
)

urlpatterns = [
    path('add-subject/', add_subject, name="add_subject"),
    path('subjects/', view_subjects, name="view_subjects"),
    path('add-lesson/', add_lesson, name="add_lesson"),
    path('lessons/', view_lessons, name="view_lessons"),
    path('learn/', learn_subjects, name="learn_subjects"),
    path('learn/<int:subject_id>/', learn_lessons_with_progress, name="learn_lessons"),
    path('lesson/<int:lesson_id>/', read_lesson, name="read_lesson"),
    path('search/', search_lessons, name="search_lessons"),
    path('bookmark/<int:lesson_id>/', add_bookmark, name="add_bookmark"),
    path('lesson/<int:lesson_id>/track-view/', track_lesson_view, name="track_lesson_view"),
    path('bookmarks/', view_bookmarks, name="view_bookmarks"),
    path('history/', view_history, name="view_history"),
    path('delete-subject/<int:subject_id>/', delete_subject, name="delete_subject"),
    path('delete-lesson/<int:lesson_id>/', delete_lesson, name="delete_lesson"),
]
