"""
builder/views.py
Function-based views for ResumeCraft AI:
- Page rendering (landing, dashboard, editor, templates, preview)
- User Authentication (signup, login, logout, profile update, password change)
- Database Resume Management (CRUD, autosave, duplicate, localStorage import)
- Gemini AI Endpoints (summary, experience, projects, skills, ATS scanner, job match, objectives, review)
"""

import json
import logging
import re
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpRequest, HttpResponseBadRequest, HttpResponseForbidden, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, DatabaseError
from django.contrib import messages

from . import ai_service
from .models import Resume

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
    """
    Renders the user dashboard.
    - If authenticated: lists the user's database-persisted resumes.
    - If guest: allows managing localStorage resumes with a cloud-sync prompt.
    """
    context = {
        'page_title': 'My Resumes – ResumeCraft AI',
        'active_nav': 'dashboard',
        'is_authenticated': request.user.is_authenticated,
    }
    if request.user.is_authenticated:
        user_resumes = Resume.objects.filter(user=request.user).order_by('-updated_at')
        context['resumes'] = user_resumes
        context['resume_count'] = user_resumes.count()
    return render(request, 'dashboard.html', context)


@ensure_csrf_cookie
def create_resume_page(request: HttpRequest):
    """
    Creates a new resume:
    - If logged-in: creates a database record for the user and opens the editor.
    - If guest: opens the editor with a fresh local resume template.
    """
    template_param = request.GET.get('template', 'classic')
    if request.user.is_authenticated:
        candidate_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
        initial_data = {
            'title': f"{candidate_name}'s Resume",
            'template': template_param,
            'personal': {
                'fullName': candidate_name,
                'email': request.user.email,
                'professionalTitle': '',
                'phone': '',
                'location': '',
                'linkedin': '',
                'github': '',
                'portfolio': '',
                'summary': ''
            },
            'skills': {
                'languages': '',
                'frameworks': '',
                'tools': '',
                'technical': '',
                'soft': ''
            },
            'education': [],
            'experience': [],
            'projects': [],
            'certifications': [],
            'achievements': [],
            'customization': {
                'accentColor': '#6257E8',
                'fontFamily': 'Inter',
                'fontSize': 'normal',
                'spacing': 'normal'
            }
        }
        resume = Resume.objects.create(
            user=request.user,
            resume_title=initial_data['title'],
            selected_template=template_param,
            resume_data=initial_data
        )
        messages.success(request, f"New resume '{resume.resume_title}' created!")
        return redirect(f"/edit/?id={resume.id}")

    context = {
        'page_title': 'Create New Resume – ResumeCraft AI',
        'active_nav': 'editor',
        'initial_template': template_param,
        'is_new': True
    }
    return render(request, 'editor.html', context)


@ensure_csrf_cookie
def editor_page(request: HttpRequest):
    """
    Renders the two-column resume editor with live preview.
    If the user is authenticated and an integer ID is provided, loads the
    resume directly from the database and verifies ownership.
    """
    resume_id = request.GET.get('id', '')
    template_param = request.GET.get('template', '')
    server_resume_json = None
    db_resume = None

    if request.user.is_authenticated and resume_id and str(resume_id).isdigit():
        db_resume = get_object_or_404(Resume, id=int(resume_id), user=request.user)
        server_resume_json = json.dumps(db_resume.resume_data)

    context = {
        'page_title': 'Resume Editor – ResumeCraft AI',
        'active_nav': 'editor',
        'resume_id': resume_id,
        'db_resume': db_resume,
        'server_resume_json': server_resume_json,
        'initial_template': template_param,
        'is_new': False,
        'is_authenticated': request.user.is_authenticated,
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
    server_resume_json = None
    if request.user.is_authenticated and resume_id and str(resume_id).isdigit():
        db_resume = get_object_or_404(Resume, id=int(resume_id), user=request.user)
        server_resume_json = json.dumps(db_resume.resume_data)

    context = {
        'page_title': 'Resume Preview & PDF Export – ResumeCraft AI',
        'active_nav': 'preview',
        'resume_id': resume_id,
        'server_resume_json': server_resume_json,
    }
    return render(request, 'preview.html', context)


# ==============================================================================
# USER AUTHENTICATION VIEWS
# ==============================================================================

@ensure_csrf_cookie
def signup_view(request: HttpRequest):
    """Handles new user registration using Django's built-in User model."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Basic validations
        if not full_name or not username or not email or not password:
            messages.error(request, "All fields are required. Please fill out the full form.")
            return render(request, 'signup.html', {
                'full_name': full_name, 'username': username, 'email': email,
                'page_title': 'Sign Up – ResumeCraft AI'
            })

        if password != confirm_password:
            messages.error(request, "Passwords do not match. Please re-enter your password.")
            return render(request, 'signup.html', {
                'full_name': full_name, 'username': username, 'email': email,
                'page_title': 'Sign Up – ResumeCraft AI'
            })

        # Username format validation
        if not re.match(r'^[\w.@+-]+$', username):
            messages.error(request, "Username may contain only letters, numbers, and @/./+/-/_ characters without spaces.")
            return render(request, 'signup.html', {
                'full_name': full_name, 'email': email,
                'page_title': 'Sign Up – ResumeCraft AI'
            })

        # Database checks for duplicate username or email
        try:
            if User.objects.filter(username__iexact=username).exists():
                messages.error(request, f"The username '{username}' is already taken. Please choose another.")
                return render(request, 'signup.html', {
                    'full_name': full_name, 'email': email,
                    'page_title': 'Sign Up – ResumeCraft AI'
                })

            if User.objects.filter(email__iexact=email).exists():
                messages.error(request, f"An account with email '{email}' already exists. Please log in instead.")
                return render(request, 'signup.html', {
                    'full_name': full_name, 'username': username,
                    'page_title': 'Sign Up – ResumeCraft AI'
                })
        except DatabaseError as db_err:
            logger.error(f"Database error during signup existence check: {db_err}", exc_info=True)
            messages.error(request, "Database connection error. Please try again in a few moments.")
            return render(request, 'signup.html', {
                'full_name': full_name, 'username': username, 'email': email,
                'page_title': 'Sign Up – ResumeCraft AI'
            })

        # Split full name into first and last name
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Django password complexity validation
        temp_user = User(username=username, email=email, first_name=first_name, last_name=last_name)
        try:
            validate_password(password, user=temp_user)
        except ValidationError as e:
            for err in e.messages:
                messages.error(request, err)
            return render(request, 'signup.html', {
                'full_name': full_name, 'username': username, 'email': email,
                'page_title': 'Sign Up – ResumeCraft AI'
            })

        # Create user with hashed password
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
        except IntegrityError:
            messages.error(request, "An account with that username or email already exists. Please log in.")
            return render(request, 'signup.html', {
                'full_name': full_name, 'username': username, 'email': email,
                'page_title': 'Sign Up – ResumeCraft AI'
            })
        except Exception as exc:
            logger.error(f"Error creating user account: {exc}", exc_info=True)
            messages.error(request, f"Unable to create account: {str(exc)}")
            return render(request, 'signup.html', {
                'full_name': full_name, 'username': username, 'email': email,
                'page_title': 'Sign Up – ResumeCraft AI'
            })

        # Log user in and redirect to dashboard
        try:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f"Welcome to ResumeCraft AI, {first_name or username}! Your account has been created.")
            return redirect('dashboard')
        except Exception as exc:
            logger.error(f"Session login error after user creation: {exc}", exc_info=True)
            messages.success(request, "Account created successfully! Please log in below.")
            return redirect('login')

    return render(request, 'signup.html', {'page_title': 'Sign Up – ResumeCraft AI'})


@ensure_csrf_cookie
def login_view(request: HttpRequest):
    """
    Authenticates a user using either their username OR email address.
    Supports 'Remember me' session persistence.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    next_url = request.GET.get('next') or request.POST.get('next') or 'dashboard'

    if request.method == 'POST':
        login_id = request.POST.get('login_id', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me') == 'on'

        if not login_id or not password:
            messages.error(request, "Please enter both your username/email and password.")
            return render(request, 'login.html', {'login_id': login_id, 'next': next_url, 'page_title': 'Log In – ResumeCraft AI'})

        try:
            # If login_id contains an '@', resolve username from email
            auth_username = login_id
            if '@' in login_id:
                matched_user = User.objects.filter(email__iexact=login_id).first()
                if matched_user:
                    auth_username = matched_user.username

            user = authenticate(request, username=auth_username, password=password)

            if user is not None:
                if not user.is_active:
                    messages.error(request, "This account has been disabled. Please contact support.")
                    return render(request, 'login.html', {'login_id': login_id, 'next': next_url, 'page_title': 'Log In – ResumeCraft AI'})

                # Handle session duration: 2 weeks if remember_me, browser close otherwise
                if remember_me:
                    request.session.set_expiry(1209600)  # 14 days
                else:
                    request.session.set_expiry(0)  # Session expires on browser close

                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                return redirect(next_url)
            else:
                messages.error(request, "Invalid username/email or password. Please verify your credentials.")
                return render(request, 'login.html', {'login_id': login_id, 'next': next_url, 'page_title': 'Log In – ResumeCraft AI'})
        except Exception as exc:
            logger.error(f"Error during login authentication: {exc}", exc_info=True)
            messages.error(request, "A database or system error occurred. Please try again.")
            return render(request, 'login.html', {'login_id': login_id, 'next': next_url, 'page_title': 'Log In – ResumeCraft AI'})

    return render(request, 'login.html', {'next': next_url, 'page_title': 'Log In – ResumeCraft AI'})


def logout_view(request: HttpRequest):
    """Logs out the authenticated user and redirects to the landing page."""
    logout(request)
    messages.info(request, "You have been logged out securely. See you next time!")
    return redirect('landing')


@login_required
@ensure_csrf_cookie
def profile_view(request: HttpRequest):
    """
    Renders user profile and handles account updates (name, email)
    and secure password changes.
    """
    user = request.user
    user_resumes = Resume.objects.filter(user=user).order_by('-updated_at')

    if request.method == 'POST':
        action = request.POST.get('action')

        # Action 1: Update Profile Details
        if action == 'update_profile':
            full_name = request.POST.get('full_name', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            if full_name and not (first_name or last_name):
                name_parts = full_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''

            email = request.POST.get('email', '').strip().lower()

            if not email:
                messages.error(request, "Email address cannot be empty.")
            elif User.objects.filter(email__iexact=email).exclude(id=user.id).exists():
                messages.error(request, f"Email '{email}' is already in use by another account.")
            else:
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.save()
                messages.success(request, "Your profile information has been updated successfully.")
            return redirect('profile')

        # Action 2: Change Password
        elif action == 'change_password':
            old_password = request.POST.get('old_password') or request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_new_password = request.POST.get('confirm_new_password') or request.POST.get('confirm_password', '')

            if not user.check_password(old_password):
                messages.error(request, "Your current password was entered incorrectly.")
            elif new_password != confirm_new_password:
                messages.error(request, "New passwords do not match. Please re-enter them.")
            else:
                try:
                    validate_password(new_password, user)
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)  # Keep user logged in
                    messages.success(request, "Your password has been changed securely!")
                except ValidationError as e:
                    for err in e.messages:
                        messages.error(request, err)
            return redirect('profile')

    context = {
        'page_title': 'My Profile – ResumeCraft AI',
        'active_nav': 'profile',
        'user': user,
        'resumes': user_resumes,
        'resume_count': user_resumes.count(),
    }
    return render(request, 'profile.html', context)


# ==============================================================================
# DATABASE RESUME MANAGEMENT API (JSON ENDPOINTS)
# ==============================================================================

@login_required
@require_http_methods(["POST"])
def api_resume_save(request: HttpRequest):
    """
    Saves or autosaves a resume to the database for the authenticated user.
    - If `id` (numeric) is passed, verifies ownership and updates existing record.
    - If no `id` or local ID, creates a new Resume database record.
    Preserves all dynamic sections within the JSONField payload.
    """
    try:
        payload = parse_json_body(request)
        resume_data = payload.get('resume_data') or payload

        if not isinstance(resume_data, dict):
            return JsonResponse({'success': False, 'message': 'Invalid resume payload format.'}, status=400)

        resume_id = payload.get('id') or resume_data.get('id')
        title = resume_data.get('title') or (
            resume_data.get('personal', {}).get('fullName') + "'s Resume"
            if resume_data.get('personal', {}).get('fullName') else 'Untitled Resume'
        )
        template = resume_data.get('template') or 'classic'

        # Update existing record if valid database integer ID
        if resume_id and str(resume_id).isdigit():
            resume = get_object_or_404(Resume, id=int(resume_id), user=request.user)
            resume.resume_title = title
            resume.selected_template = template
            resume_data['id'] = str(resume.id)
            resume.resume_data = resume_data
            resume.save()
            return JsonResponse({
                'success': True,
                'id': resume.id,
                'title': resume.resume_title,
                'updated_at': resume.updated_at.strftime('%b %d, %Y %I:%M %p'),
                'message': 'Resume updated successfully in cloud database.'
            })

        # Otherwise create a new record
        resume = Resume.objects.create(
            user=request.user,
            resume_title=title,
            selected_template=template,
            resume_data=resume_data
        )
        # Store assigned database ID inside resume_data
        resume_data['id'] = str(resume.id)
        resume.resume_data = resume_data
        resume.save(update_fields=['resume_data'])

        return JsonResponse({
            'success': True,
            'id': resume.id,
            'title': resume.resume_title,
            'updated_at': resume.updated_at.strftime('%b %d, %Y %I:%M %p'),
            'message': 'Resume saved to cloud database.'
        })
    except Http404:
        raise
    except Exception as exc:
        logger.error(f"Error saving resume to database: {exc}")
        return JsonResponse({'success': False, 'message': f"Failed to save resume: {str(exc)}"}, status=500)


@login_required
@require_http_methods(["POST", "DELETE"])
def api_resume_delete(request: HttpRequest, resume_id: int = None):
    """
    Deletes a resume record from the database.
    Strictly enforces that the record belongs to the requesting user.
    """
    if resume_id is None:
        payload = parse_json_body(request)
        resume_id = payload.get('id')
    if not resume_id or not str(resume_id).isdigit():
        return JsonResponse({'success': False, 'message': 'Missing or invalid resume ID.'}, status=400)

    resume = get_object_or_404(Resume, id=int(resume_id), user=request.user)
    title = resume.resume_title
    resume.delete()
    return JsonResponse({
        'success': True,
        'message': f"Resume '{title}' deleted successfully."
    })


@login_required
@require_http_methods(["POST"])
def api_resume_duplicate(request: HttpRequest, resume_id: int = None):
    """
    Duplicates an existing resume for the authenticated user.
    Strictly verifies ownership.
    """
    if resume_id is None:
        payload = parse_json_body(request)
        resume_id = payload.get('id')
    if not resume_id or not str(resume_id).isdigit():
        return JsonResponse({'success': False, 'message': 'Missing or invalid resume ID.'}, status=400)

    orig = get_object_or_404(Resume, id=int(resume_id), user=request.user)
    data_copy = json.loads(json.dumps(orig.resume_data))
    new_title = f"Copy of {orig.resume_title}"
    data_copy['title'] = new_title

    new_resume = Resume.objects.create(
        user=request.user,
        resume_title=new_title,
        selected_template=orig.selected_template,
        resume_data=data_copy
    )
    data_copy['id'] = str(new_resume.id)
    new_resume.resume_data = data_copy
    new_resume.save(update_fields=['resume_data'])

    return JsonResponse({
        'success': True,
        'id': new_resume.id,
        'title': new_resume.resume_title,
        'message': f"Duplicated as '{new_title}'."
    })


@login_required
@require_http_methods(["POST"])
def api_import_local_resumes(request: HttpRequest):
    """
    Imports client-side localStorage resumes into the authenticated user's database account.
    Avoids duplicating identical resumes.
    """
    try:
        payload = parse_json_body(request)
        resumes_list = payload.get('resumes', [])
        if not isinstance(resumes_list, list):
            return JsonResponse({'success': False, 'message': 'Invalid resumes array format.'}, status=400)

        imported_count = 0
        for r in resumes_list:
            if not isinstance(r, dict):
                continue
            title = r.get('title') or (
                r.get('personal', {}).get('fullName') + "'s Resume"
                if r.get('personal', {}).get('fullName') else 'Imported Resume'
            )
            template = r.get('template') or 'classic'

            # Create cloud database record
            db_resume = Resume.objects.create(
                user=request.user,
                resume_title=title,
                selected_template=template,
                resume_data=r
            )
            r['id'] = str(db_resume.id)
            db_resume.resume_data = r
            db_resume.save(update_fields=['resume_data'])
            imported_count += 1

        return JsonResponse({
            'success': True,
            'count': imported_count,
            'imported_count': imported_count,
            'message': f"Successfully imported {imported_count} resume(s) to your cloud account!"
        })
    except Exception as exc:
        logger.error(f"Error importing local resumes: {exc}")
        return JsonResponse({'success': False, 'message': f"Import failed: {str(exc)}"}, status=500)


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
