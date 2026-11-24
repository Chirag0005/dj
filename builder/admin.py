"""
builder/admin.py
Django Admin integration for ResumeCraft AI models.
"""

from django.contrib import admin
from .models import Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('resume_title', 'user', 'candidate_name', 'selected_template', 'updated_at', 'created_at')
    list_filter = ('selected_template', 'created_at', 'updated_at')
    search_fields = ('resume_title', 'user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('user',)
    ordering = ('-updated_at',)

    def candidate_name(self, obj):
        return obj.candidate_name or "—"
    candidate_name.short_description = "Candidate Name"
