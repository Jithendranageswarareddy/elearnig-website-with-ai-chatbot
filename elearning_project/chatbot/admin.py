from django.contrib import admin

from .models import (
    PDFPageChunk,
    ReferencePDF,
)


@admin.register(ReferencePDF)
class ReferencePDFAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'subject',
        'uploaded_by',
        'status',
        'is_syllabus_reference',
        'processing_status',
        'uploaded_at',
    )
    list_filter = ('status', 'processing_status', 'is_syllabus_reference', 'subject', 'uploaded_by')
    search_fields = ('title', 'subject__name', 'uploaded_by__email')
    list_select_related = ('subject', 'uploaded_by')

    def has_module_permission(self, request):
        return request.user.is_authenticated and (
            request.user.is_superuser or getattr(request.user, 'is_principal', False)
        )

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def get_list_editable(self, request):
        if request.user.is_superuser or getattr(request.user, 'is_principal', False):
            return ('status', 'is_syllabus_reference')
        return ()

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser or getattr(request.user, 'is_principal', False):
            return ()
        return ('status', 'is_syllabus_reference')

    def save_model(self, request, obj, form, change):
        if not (request.user.is_superuser or getattr(request.user, 'is_principal', False)):
            obj.status = ReferencePDF.Status.APPROVED
            obj.is_syllabus_reference = True
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        obj.delete()

    def delete_queryset(self, request, queryset):
        queryset.delete()


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


@admin.register(PDFPageChunk)
class PDFPageChunkAdmin(SuperuserOnlyAdmin):
    list_display = ('reference_pdf', 'page_number')
    search_fields = ('text_content',)




