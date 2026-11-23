# ResumeCraft AI – Build Your Professional Identity

> **An intelligent, ATS-friendly resume builder powered by Django, Google Gemini AI, and client-side browser storage. Zero database dependencies, 100% privacy, and instant PDF generation.**

---

## 📌 Project Overview

**ResumeCraft AI** is a modern, commercial-grade web application engineered to help students, freshers, and professionals create beautiful, ATS-optimized resumes. Built with a clean, database-free architecture, all personal information and resume versions are stored securely inside the user's browser `localStorage`, ensuring complete data privacy and instantaneous responsiveness.

The backend leverages **Django** and the official **Google GenAI Python SDK (`google-genai`)** to provide 8 intelligent career copilot tools that enhance resume bullet points, calculate ATS compatibility, suggest relevant technical skills, and analyze job descriptions without ever fabricating information or inventing qualifications.

---

## ✨ Key Features

### 1. 100% Database-Free & Privacy-Preserving
- **Strictly No Database**: Operates without SQLite, PostgreSQL, MySQL, MongoDB, or Django ORM models.
- **Client-Side `localStorage`**: Resumes, autosaves, and edits persist in the user's browser.
- **Zero Server Storage**: User data is never persisted on backend disks or third-party databases.
- **Offline / Demo Resilience**: Functions smoothly with intelligent fallback data even if an API key is missing or quota is exhausted.

### 2. Live Two-Column Resume Editor
- **Real-Time Synchronization**: Keystrokes in input forms immediately update the live A4 resume sheet without page refreshes.
- **Debounced Autosave**: Changes autosave within 350ms with visual status feedback (*"All changes saved"*).
- **Dynamic Repeaters**: Add, reorder, or remove Education, Experience, Projects, Certifications, and Achievements dynamically.
- **Automatic Section Hiding**: Blank sections are hidden from the live preview automatically.
- **Mobile Responsive**: Smooth tab switcher between form input and live preview on tablet and mobile viewports.

### 3. Four Recruiter-Approved Resume Templates
1. **Professional Classic**: Traditional corporate layout with serif/clean sans typography, horizontal dividers, and balanced formal hierarchy.
2. **Modern Minimal**: Left-aligned modern layout with colored left borders, generous whitespace, and contemporary aesthetics.
3. **Developer Portfolio**: Tech-forward design featuring code badges, monospace accents, and prominent GitHub/live demo links.
4. **Student Fresher**: Academic-first layout prioritizing university credentials, coursework, hackathon achievements, and certifications.
*Templates can be switched at any time without losing any entered data.*

### 4. Custom Styling & Theming
- **Accent Color Picker**: 5 pre-configured SaaS colors (Royal Purple, Ocean Blue, Emerald, Crimson, Slate) plus a native HTML5 custom color picker.
- **Typography Selection**: Inter, Poppins, Roboto, Merriweather, and JetBrains Mono.
- **Font Sizing**: Small, Regular, and Large.
- **Section Spacing**: Compact, Normal, and Spacious.

### 5. Pixel-Perfect A4 PDF Export
- Leverages native browser print rendering formatted specifically for international standard A4 paper (`210mm × 297mm`).
- Zero overlapping elements, high-contrast printing, clean page-break avoidance on section cards, and automatic hiding of all UI toolbars and navigation buttons during printing.

### 6. Eight Integrated Google Gemini AI Features
1. **AI Professional Summary Generator (`/ai/generate-summary/`)**: Synthesizes education, skills, and career focus into a 3-sentence executive summary.
2. **AI Experience Improver (`/ai/improve-experience/`)**: Rewrites raw bullet points using Google's XYZ action-verb framework without hallucinating numbers or facts.
3. **AI Project Description Generator (`/ai/project-description/`)**: Highlights system architecture, tech stacks, and engineering methodology.
4. **AI Skill Suggestions (`/ai/skill-suggestions/`)**: Recommends in-demand technologies categorized into Languages, Frameworks, Tools, and Concepts with 1-click addition to the resume.
5. **Simulated ATS Resume Analyzer (`/ai/ats-analysis/`)**: Compares resume text with a target job description, returning an indicative compatibility score, matching keywords, missing keywords, and formatting checks.
6. **AI Job Description Matcher (`/ai/job-match/`)**: Pinpoints exact alignment and suggests project positioning to capture recruiter attention.
7. **AI Career Objective Generator (`/ai/career-objective/`)**: Calibrated specifically for Student, Fresher, and Experienced tiers.
8. **AI Full Resume Diagnostic Review (`/ai/review-resume/`)**: End-to-end evaluation of grammar, professional tone, section organization, and actionable quick wins.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend Framework** | Python 3.10+ / 3.14, Django 5.x / 6.x |
| **AI Integration** | Google Gemini API via official `google-genai` Python SDK (`gemini-2.5-flash`) |
| **Frontend UI** | HTML5, CSS3, Vanilla JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons |
| **Typography** | Google Fonts (Inter, Plus Jakarta Sans, JetBrains Mono, Roboto, Merriweather) |
| **Client Storage** | Browser `localStorage` (JSON serialization) |
| **Static Delivery** | WhiteNoise 6.x (CompressedStaticFilesStorage) |
| **Production WSGI** | Gunicorn 23.x / 27.x |
| **Deployment Target** | Render (`render.yaml`, `build.sh`) |

---

## 🚀 Quick Local Setup

### Step 1: Clone or Navigate to the Project Directory
```bash
cd resumecraft
```

### Step 2: Create and Activate a Virtual Environment
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env     # On macOS/Linux
copy .env.example .env   # On Windows
```

Edit `.env` and insert your Gemini API Key:
```env
SECRET_KEY=your-random-django-secret-key-here
DEBUG=True
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

> **How to get a Free Google Gemini API Key:**
> 1. Visit [Google AI Studio](https://aistudio.google.com/).
> 2. Sign in with your Google account.
> 3. Click **"Get API key"** and create a new key.
> 4. Paste the key into your `.env` file under `GEMINI_API_KEY`.
> *(Note: The application still runs smoothly in Demo Mode if no key is configured!)*

### Step 5: Run Automated Tests
```bash
python manage.py test
```
All 10 unit tests will pass in milliseconds with zero database connections attempted!

### Step 6: Start the Development Server
```bash
python manage.py runserver
```
Open your browser and navigate to: **`http://127.0.0.1:8000/`**

---

## 🌐 Render Deployment Guide

ResumeCraft AI is configured for one-click deployment on **Render** without requiring any database add-on.

### Files Included for Render:
- `render.yaml`: Blueprint definition specifying environment, build command, and start command.
- `build.sh`: Automated build script (`pip install -r requirements.txt && python manage.py collectstatic --no-input`).
- `requirements.txt`: Python package requirements.
- `resumecraft/wsgi.py`: WSGI entry point.

### Step-by-Step Render Deployment:
1. Push your project repository to **GitHub** or **GitLab**.
2. Log in to [Render Dashboard](https://dashboard.render.com/).
3. Click **"New +"** and choose **"Web Service"** (or choose **"Blueprint"** to use `render.yaml`).
4. Connect your Git repository.
5. Configure the following service settings:
   - **Environment**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn resumecraft.wsgi:application`
6. Add the following **Environment Variables** in Render's dashboard:
   - `SECRET_KEY`: `<generate-a-strong-secret-key>`
   - `DEBUG`: `False`
   - `GEMINI_API_KEY`: `<your-google-gemini-api-key>`
   - `CSRF_TRUSTED_ORIGINS`: `https://your-service-name.onrender.com`
7. Click **"Deploy Web Service"**.
8. Once the build finishes, open your live Render URL!

---

## 📁 Project Structure

```
resumecraft/
│
├── manage.py                   # Django CLI utility
├── requirements.txt            # Python dependencies (Django, google-genai, whitenoise, gunicorn)
├── render.yaml                 # Render infrastructure-as-code specification
├── build.sh                    # Render shell build script
├── .gitignore                  # Git ignore rules (.env, __pycache__, staticfiles)
├── .env.example                # Example environment variables template
├── README.md                   # Complete project documentation
├── PROJECT_EXPLANATION.md       # Architecture deep-dive & 25 Viva Questions
│
├── resumecraft/                # Project Configuration Package
│   ├── __init__.py
│   ├── settings.py             # Database-free Django settings (DATABASES = {})
│   ├── urls.py                 # Root URL configuration
│   └── wsgi.py                 # WSGI application entry point for Gunicorn
│
├── builder/                    # Core Application App
│   ├── __init__.py
│   ├── apps.py                 # App configuration
│   ├── ai_service.py           # Gemini 2.5 SDK integration & 8 AI features
│   ├── views.py                # Function-based views for pages & AI API endpoints
│   ├── urls.py                 # Application URL routing
│   └── tests.py                # Automated tests using SimpleTestCase (Database-free)
│
├── templates/                  # Django HTML Templates
│   ├── base.html               # Base layout, navbar, footer, toast container
│   ├── index.html              # High-converting SaaS landing page
│   ├── dashboard.html          # Resumes dashboard (localStorage cards, stats, empty states)
│   ├── editor.html             # Two-column resume editor with live A4 preview & AI copilot
│   ├── templates.html          # Templates showcase gallery
│   └── preview.html            # Standalone print & PDF export preview
│
└── static/                     # Static Assets
    ├── css/
    │   └── style.css           # Premium SaaS design system, A4 sheet styling, print CSS
    ├── js/
    │   ├── storage.js          # Client-side localStorage engine
    │   ├── editor.js           # Live editor sync, dynamic repeaters, Gemini AI handlers
    │   └── app.js              # Dashboard manager, toast system, delete/rename modals
    └── data/
        └── sample_resumes.json # Pre-loaded B.Tech CSE developer resume example
```

---

## 🔒 Security Best Practices Implemented

- **No Secret Leakage**: The Gemini API key is strictly maintained in the server's environment variable `GEMINI_API_KEY`. It is never delivered to client JavaScript, HTML, CSS, or Git commits.
- **CSRF Protection**: All AI endpoints (`POST`) require Django's CSRF token (`X-CSRFToken`).
- **Input Validation & Capping**: Prompts and inputs are truncated to safe bounds (max 4,000 characters) to prevent token abuse and buffer attacks.
- **Strict Anti-Hallucination Prompts**: System instructions strictly mandate that Gemini rewrite and format *only* the user's factual input and never fabricate metrics, companies, or credentials.
- **XSS Prevention**: All dynamic HTML rendering in templates and client scripts uses string escaping (`escapeHtml`).

---

## ⚠️ Known Limitations & Design Trade-offs

1. **Browser-Specific Storage**: Because resumes persist in `localStorage`, saved resumes do not automatically synchronize across different devices (e.g., from laptop to phone). Users can use the Print / PDF download to transfer their resumes.
2. **Storage Quotas**: Browser `localStorage` offers approximately 5MB of text storage per domain, which is more than sufficient for hundreds of text resumes but does not support large binary image uploads.
3. **Private Browsing Mode**: In Incognito/Private tabs, browser `localStorage` is cleared when the window is closed.

---

## 🎓 Academic Credit & Demonstration

- **Course**: B.Tech Computer Science & Engineering (Major Project)
- **Topic**: Full-Stack Web Development, Generative AI Integration, and Client-Side State Architecture.
- **Evaluation Guide**: Refer to [`PROJECT_EXPLANATION.md`](file:///c:/Users/Dharam%20Pal/OneDrive/Desktop/cra/PROJECT_EXPLANATION.md) for complete technical explanations and 25 viva questions with detailed answers.
