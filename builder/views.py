"""
builder/views.py
Function-based views for ResumeCraft AI.

No database models or ORM are used.
All endpoints adhere to clean JSON request parsing, validation, and safe error handling.
"""

import json
import logging
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse, HttpRequest, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie

from . import ai_service

logger = logging.getLogger(__name__)


# ==============================================================================
# PAGE RENDERING VIEWS
# ==============================================================================

@ensure_csrf_cookie
def landing_page(request: HttpRequest):
    """Renders the high-converting SaaS landing page."""
    context = {
        'page_title': 'ResumeCraft AI – Build Your Professional Identity',
        'active_nav': 'home'
    }
    return render(request, 'index.html', context)


@ensure_csrf_cookie
def dashboard_page(request: HttpRequest):
    """Renders the user dashboard listing resumes stored in browser localStorage."""
    context = {
        'page_title': 'My Resumes – ResumeCraft AI',
        'active_nav': 'dashboard'
    }
    return render(request, 'dashboard.html', context)


@ensure_csrf_cookie
def create_resume_page(request: HttpRequest):
    """Entry point to create a new resume with an optional chosen template."""
    template_param = request.GET.get('template', 'classic')
    context = {
        'page_title': 'Create New Resume – ResumeCraft AI',
        'active_nav': 'editor',
        'initial_template': template_param,
        'is_new': True
    }
    return render(request, 'editor.html', context)


@ensure_csrf_cookie
def editor_page(request: HttpRequest):
    """Renders the two-column resume editor with live preview."""
    resume_id = request.GET.get('id', '')
    template_param = request.GET.get('template', '')
    context = {
        'page_title': 'Resume Editor – ResumeCraft AI',
        'active_nav': 'editor',
        'resume_id': resume_id,
        'initial_template': template_param,
        'is_new': False
    }
    return render(request, 'editor.html', context)


@ensure_csrf_cookie
def templates_page(request: HttpRequest):
    """Renders the interactive templates gallery."""
    context = {
        'page_title': 'Resume Templates – ResumeCraft AI',
        'active_nav': 'templates'
    }
    return render(request, 'templates.html', context)


@ensure_csrf_cookie
def preview_page(request: HttpRequest):
    """Renders standalone full-screen resume preview optimized for print/PDF export."""
    resume_id = request.GET.get('id', '')
    context = {
        'page_title': 'Resume Preview & PDF Export – ResumeCraft AI',
        'active_nav': 'preview',
        'resume_id': resume_id
    }
    return render(request, 'preview.html', context)


# ==============================================================================
# SAMPLE DATA API (STATIC JSON)
# ==============================================================================

def sample_resumes_api(request: HttpRequest):
    """Returns static sample resume data from static/data/sample_resumes.json."""
    try:
        sample_file = Path(__file__).resolve().parent.parent / 'static' / 'data' / 'sample_resumes.json'
        if sample_file.exists():
            with open(sample_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return JsonResponse({'success': True, 'data': data})
        else:
            return JsonResponse({'success': False, 'message': 'Sample data file not found.'}, status=404)
    except Exception as exc:
        logger.error(f"Error reading sample resumes: {exc}")
        return JsonResponse({'success': False, 'message': 'Unable to load sample data.'}, status=500)


# ==============================================================================
# HELPER: SAFE REQUEST BODY PARSER
# ==============================================================================

def parse_json_body(request: HttpRequest) -> dict:
    """Safely extracts JSON payload from request body or POST dictionary."""
    if request.body:
        try:
            return json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    # Fallback to standard POST dict
    return request.POST.dict()


# ==============================================================================
# GEMINI AI ENDPOINTS
# ==============================================================================

@require_http_methods(["POST"])
def ai_generate_summary(request: HttpRequest):
    """Generates a professional resume summary using Gemini AI."""
    payload = parse_json_body(request)
    education = str(payload.get('education', ''))[:1000]
    skills = str(payload.get('skills', ''))[:1000]
    experience = str(payload.get('experience', ''))[:1500]
    career_goal = str(payload.get('career_goal', ''))[:500]

    result = ai_service.generate_summary(
        education=education,
        skills=skills,
        experience=experience,
        career_goal=career_goal
    )
    return JsonResponse(result)


@require_http_methods(["POST"])
def ai_improve_experience(request: HttpRequest):
    """Rewrites basic work experience into professional action-oriented bullet points."""
    payload = parse_json_body(request)
    job_title = str(payload.get('job_title', ''))[:200]
    company = str(payload.get('company', ''))[:200]
    description = str(payload.get('description', ''))[:2500]

    if not description.strip():
        return JsonResponse({'success': False, 'message': 'Experience description is required.'}, status=400)

    result = ai_service.improve_experience(
        job_title=job_title,
        company=company,
        description=description
    )
    return JsonResponse(result)


@require_http_methods(["POST"])
def ai_project_description(request: HttpRequest):
    """Generates concise, technical resume bullet points for a project."""
    payload = parse_json_body(request)
    project_name = str(payload.get('project_name', ''))[:200]
    technologies = str(payload.get('technologies', ''))[:500]
    functionality = str(payload.get('functionality', ''))[:2500]

    result = ai_service.generate_project_description(
        project_name=project_name,
        technologies=technologies,
        functionality=functionality
    )
    return JsonResponse(result)


@require_http_methods(["POST"])
def ai_skill_suggestions(request: HttpRequest):
    """Recommends relevant in-demand skills based on career role and current skills."""
    payload = parse_json_body(request)
    career_role = str(payload.get('career_role', ''))[:200]
    existing_skills = str(payload.get('existing_skills', ''))[:1000]

    result = ai_service.suggest_skills(
        career_role=career_role,
        existing_skills=existing_skills
    )
    return JsonResponse(result)


@require_http_methods(["POST"])
def ai_ats_analysis(request: HttpRequest):
    """Performs simulated ATS compatibility analysis against a target job description."""
    payload = parse_json_body(request)
    job_description = str(payload.get('job_description', ''))[:4000]
    resume_data = payload.get('resume_data', {})

    if not job_description.strip():
        return JsonResponse({'success': False, 'message': 'Please paste a target Job Description first to run the ATS scan.'}, status=200)

    result = ai_service.analyze_ats(
        resume_data=resume_data,
        job_description=job_description
    )
    return JsonResponse(result)


@require_http_methods(["POST"])
def ai_job_match(request: HttpRequest):
    """Compares resume with a job description and highlights matches and skill gaps."""
    payload = parse_json_body(request)
    job_description = str(payload.get('job_description', ''))[:4000]
    resume_data = payload.get('resume_data', {})

    if not job_description.strip():
        return JsonResponse({'success': False, 'message': 'Please paste a target Job Description first to perform matching.'}, status=200)

    result = ai_service.match_job_description(
        resume_data=resume_data,
        job_description=job_description
    )
    return JsonResponse(result)


@require_http_methods(["POST"])
def ai_career_objective(request: HttpRequest):
    """Generates tailored career objectives for Student, Fresher, or Experienced levels."""
    payload = parse_json_body(request)
    education = str(payload.get('education', ''))[:500]
    skills = str(payload.get('skills', ''))[:1000]
    career_interest = str(payload.get('career_interest', ''))[:300]
    experience_level = str(payload.get('experience_level', 'Fresher'))[:50]

    result = ai_service.generate_career_objective(
        education=education,
        skills=skills,
        career_interest=career_interest,
        experience_level=experience_level
    )
    return JsonResponse(result)


@require_http_methods(["POST"])
def ai_review_resume(request: HttpRequest):
    """Performs an overall audit of resume clarity, formatting, tone, and completeness."""
    payload = parse_json_body(request)
    resume_data = payload.get('resume_data', {})

    result = ai_service.review_resume(resume_data=resume_data)
    return JsonResponse(result)
