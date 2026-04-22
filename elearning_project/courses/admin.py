from django.contrib import admin
from .models import Semester, Subject, Lesson, Bookmark, History


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('number', 'regulation', 'is_active')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject_code', 'semester', 'is_active')
    list_filter = ('semester', 'is_active')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'order', 'is_active')
    list_filter = ('is_active', 'subject')


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson')


@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'viewed_at')

