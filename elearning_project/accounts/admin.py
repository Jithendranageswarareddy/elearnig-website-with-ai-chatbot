from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher

from .models import SystemLog

User = get_user_model()


class SuperuserOnlyAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_authenticated and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.is_superuser


@admin.register(User)
class UserAdmin(SuperuserOnlyAdmin):
    list_display = ("email", "name", "role", "is_staff", "is_active", "is_superuser")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("email", "name")
    ordering = ("email",)
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("name", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    def save_model(self, request, obj, form, change):
        password = form.cleaned_data.get("password")
        if password:
            try:
                identify_hasher(password)
            except Exception as e:
                print("ERROR:", str(e))
                obj.set_password(password)
        super().save_model(request, obj, form, change)


@admin.register(SystemLog)
class SystemLogAdmin(SuperuserOnlyAdmin):
    list_display = ("timestamp", "user", "action_type", "object_type", "object_id")
    list_filter = ("action_type", "object_type", "timestamp")
    search_fields = ("user__email", "object_type")
    readonly_fields = ("timestamp", "user", "action_type", "object_type", "object_id", "metadata")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
