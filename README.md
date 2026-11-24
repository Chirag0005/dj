# ResumeCraft AI – Build Your Professional Identity

> **An intelligent, ATS-friendly resume builder powered by Django, Google Gemini AI, User Authentication, and Dual-Database Storage (SQLite & PostgreSQL).**

---

## 📌 Project Overview

**ResumeCraft AI** is a modern, commercial-grade SaaS web application engineered to help students, freshers, and professionals create beautiful, ATS-optimized resumes. It features a complete user authentication system and dual-database architecture:
- **Local Development**: Built-in SQLite (`db.sqlite3`) for instant, zero-setup testing.
- **Production Deployment**: Cloud PostgreSQL on Render via `dj-database-url` and `psycopg2-binary`.
- **Hybrid Guest Mode**: Unauthenticated visitors can create resumes stored in browser `localStorage`, with 1-click cloud sync once they register or log in.

The backend leverages **Django** and the official **Google GenAI Python SDK (`google-genai`)** to provide 8 intelligent career copilot tools that enhance resume bullet points, calculate ATS compatibility, suggest relevant technical skills, and analyze job descriptions without ever fabricating information or inventing qualifications.

---

## ✨ Key Features

### 1. Robust User Authentication & Profile Management
- **Django Built-in Auth**: Relies on industry-standard Django authentication and secure PBKDF2/SHA-256 password hashing (plain-text passwords are never stored).
- **Flexible Login**: Sign in using either **Username** or **Email Address**.
- **Sign Up with Validation**: Duplicate username/email checks, password matching, and Django password complexity rules.
- **User Profile Dashboard**: View account details, edit full name and email, and change passwords securely.
- **Session Management**: "Remember Me" support for persistent login sessions and clean logout redirect.

### 2. Dual Database & Cloud Resume Management
- **Django ORM & `Resume` Model**: Resumes belong to authenticated users via ForeignKey with automatic timestamp tracking (`created_at`, `updated_at`).
- **Flexible JSONField Payload**: Preserves dynamic resume sections (personal info, education, experience, projects, skills, certifications, styling) without brittle multi-table schemas.
- **User Isolation**: Strict server-side ownership checks ensure users can only access, edit, duplicate, or delete their own resumes.
- **Instant Cloud Sync & Autosave**: Real-time autosaving directly to the database with visual status indicators.
- **LocalStorage Import**: When a user registers or logs in, any existing resumes created as a guest in browser storage are detected with an optional 1-click cloud import banner.

### 3. Live Two-Column Resume Editor
- **Real-Time Synchronization**: Keystrokes in input forms immediately update the live A4 resume sheet without page refreshes.
- **Debounced Autosave**: Changes autosave within 400ms with visual status feedback (*"Cloud saved"*).
- **Dynamic Repeaters**: Add, reorder, or remove Education, Experience, Projects, Certifications, and Achievements dynamically.
- **Automatic Section Hiding**: Blank sections are hidden from the live preview automatically.
- **Mobile Responsive**: Smooth tab switcher between form input and live preview on tablet and mobile viewports.

### 4. Four Recruiter-Approved Resume Templates
1. **Professional Classic**: Traditional corporate layout with serif/clean sans typography, horizontal dividers, and balanced formal hierarchy.
2. **Modern Minimal**: Left-aligned modern layout with colored left borders, generous whitespace, and contemporary aesthetics.
3. **Developer Portfolio**: Tech-forward design featuring code badges, monospace accents, and prominent GitHub/live demo links.
4. **Student Fresher**: Academic-first layout prioritizing university credentials, coursework, hackathon achievements, and certifications.
*Templates can be switched at any time without losing any entered data.*

### 5. Custom Styling & Theming
- **Accent Color Picker**: 5 pre-configured SaaS colors (Royal Purple, Ocean Blue, Emerald, Crimson, Slate) plus a native HTML5 custom color picker.
- **Typography Selection**: Inter, Poppins, Roboto, Merriweather, and JetBrains Mono.
- **Font Sizing**: Small, Regular, and Large.
- **Section Spacing**: Compact, Normal, and Spacious.

### 6. Pixel-Perfect A4 PDF Export
- Leverages native browser print rendering formatted specifically for international standard A4 paper (`210mm × 297mm`).
- Zero overlapping elements, high-contrast printing, clean page-break avoidance on section cards, and automatic hiding of all UI toolbars and navigation buttons during printing.

### 7. Eight Integrated Google Gemini AI Features
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
| **Database Engine** | SQLite (local development) / PostgreSQL (production on Render) |
| **Database Connector** | `dj-database-url` (>=2.1.0), `psycopg2-binary` (>=2.9.9) |
| **Authentication** | Django built-in Auth (PBKDF2 password hashing, session cookies) |
| **AI Integration** | Google Gemini API via official `google-genai` Python SDK (`gemini-2.5-flash`) |
| **Frontend UI** | HTML5, CSS3, Vanilla JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons |
| **Typography** | Google Fonts (Inter, Plus Jakarta Sans, JetBrains Mono, Roboto, Merriweather) |
| **Client Storage** | Browser `localStorage` (Guest Mode & local cache fallback) |
| **Static Delivery** | WhiteNoise 6.x (CompressedStaticFilesStorage) |
| **Production WSGI** | Gunicorn 23.x / 27.x |
| **Deployment Target** | Render (`render.yaml`, `build.sh`) |

---

## 🚀 Quick Local Setup

### Step 1: Clone or Navigate to the Project Directory
```bash
git clone https://github.com/Chirag0005/dj.git
cd dj
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

Edit `.env` to include your free Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
SECRET_KEY=your-django-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
# DATABASE_URL is optional: leave empty for local SQLite, or provide postgres://... for PostgreSQL
```

### Step 5: Run Database Migrations
```bash
python manage.py migrate
```

### Step 6: Create Admin Superuser (Optional)
```bash
python manage.py createsuperuser
```

### Step 7: Run Automated Tests (36 Tests)
```bash
python manage.py test
```

### Step 8: Start the Local Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 🌐 Production Deployment on Render

1. Create a **Web Service** on Render and connect your GitHub repository (`https://github.com/Chirag0005/dj.git`).
2. Set the build and start commands:
   - **Build Command**: `pip install -r requirements.txt && python manage.py migrate --no-input && python manage.py collectstatic --no-input`
   - **Start Command**: `gunicorn resumecraft.wsgi:application`
3. Add Environment Variables in Render Dashboard:
   - `GEMINI_API_KEY`: Your Google Gemini API Key
   - `SECRET_KEY`: Random 50-character string
   - `ALLOWED_HOSTS`: `*`
   - `DEBUG`: `False`
   - `DATABASE_URL`: (Optional) Attach a free Render PostgreSQL database URL for persistent cloud storage. If omitted, SQLite operates automatically.

---

## 📜 License
MIT License. Built for educational and professional demonstration purposes.
