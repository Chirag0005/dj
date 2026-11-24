"""
builder/models.py
Database models for ResumeCraft AI.
"""

from django.db import models
from django.contrib.auth.models import User


class Resume(models.Model):
    """
    Stores an individual resume belonging to a registered user.
    The resume_data JSONField preserves the flexible, dynamic structure
    of all resume sections (personal, skills, education, experience,
    projects, certifications, achievements, customization) without
    requiring brittle multi-table schemas.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='resumes',
        help_text="The authenticated user who owns this resume."
    )
    resume_title = models.CharField(
        max_length=255,
        default='My Resume',
        help_text="User-defined title for organizing resumes (e.g. SDE Resume, Frontend Resume)."
    )
    resume_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured JSON payload containing all resume sections and customization options."
    )
    selected_template = models.CharField(
        max_length=50,
        default='classic',
        help_text="The active visual layout template (classic, modern, minimal, executive, fresher, tech)."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the resume was first created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the resume was last updated or autosaved."
    )

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Resume'
        verbose_name_plural = 'Resumes'

    def __str__(self):
        return f"{self.resume_title} ({self.user.username})"

    @property
    def candidate_name(self):
        """Returns candidate full name from JSON data if available."""
        if isinstance(self.resume_data, dict):
            return self.resume_data.get('personal', {}).get('fullName', '')
        return ''

    @property
    def completion_score(self):
        """Calculates completion score percentage based on filled sections."""
        if not isinstance(self.resume_data, dict):
            return 25
        score = 0
        p = self.resume_data.get('personal', {})
        if p.get('fullName'):
            score += 15
        if p.get('email'):
            score += 10
        if p.get('professionalTitle'):
            score += 10
        if p.get('summary'):
            score += 15
        if self.resume_data.get('education') and len(self.resume_data.get('education', [])) > 0:
            score += 15
        if self.resume_data.get('experience') and len(self.resume_data.get('experience', [])) > 0:
            score += 15
        if self.resume_data.get('projects') and len(self.resume_data.get('projects', [])) > 0:
            score += 10
        s = self.resume_data.get('skills', {})
        if (isinstance(s, dict) and any(s.values())) or (isinstance(s, list) and len(s) > 0):
            score += 10
        return min(100, max(20, score))
