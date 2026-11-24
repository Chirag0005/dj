"""
builder/urls.py
URL routing for ResumeCraft AI.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Page routes
    path('', views.landing_page, name='landing'),
    path('dashboard/', views.dashboard_page, name='dashboard'),
    path('create/', views.create_resume_page, name='create_resume'),
    path('edit/', views.editor_page, name='editor'),
    path('templates/', views.templates_page, name='templates'),
    path('preview/', views.preview_page, name='preview'),

    # Static sample resumes API
    path('api/sample-resumes/', views.sample_resumes_api, name='api_sample_resumes'),

    # User Authentication routes
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # Database Resume Management API
    path('api/resumes/save/', views.api_resume_save, name='api_resume_save'),
    path('api/resumes/delete/', views.api_resume_delete, name='api_resume_delete_post'),
    path('api/resumes/<int:resume_id>/delete/', views.api_resume_delete, name='api_resume_delete'),
    path('api/resumes/duplicate/', views.api_resume_duplicate, name='api_resume_duplicate_post'),
    path('api/resumes/<int:resume_id>/duplicate/', views.api_resume_duplicate, name='api_resume_duplicate'),
    path('api/resumes/import/', views.api_import_local_resumes, name='api_import_resumes'),
    path('api/resumes/import-local/', views.api_import_local_resumes, name='api_import_local_resumes'),

    # Gemini AI endpoints
    path('ai/generate-summary/', views.ai_generate_summary, name='ai_generate_summary'),
    path('ai/improve-experience/', views.ai_improve_experience, name='ai_improve_experience'),
    path('ai/project-description/', views.ai_project_description, name='ai_project_description'),
    path('ai/skill-suggestions/', views.ai_skill_suggestions, name='ai_skill_suggestions'),
    path('ai/ats-analysis/', views.ai_ats_analysis, name='ai_ats_analysis'),
    path('ai/job-match/', views.ai_job_match, name='ai_job_match'),
    path('ai/career-objective/', views.ai_career_objective, name='ai_career_objective'),
    path('ai/review-resume/', views.ai_review_resume, name='ai_review_resume'),
]
