"""
builder/ai_service.py
Core Gemini AI service layer for ResumeCraft AI.

Uses the official Google GenAI Python SDK (`google-genai`).
Features:
- Secure API key handling via environment variables (`GEMINI_API_KEY`).
- Explicitly configured with API version `v1beta` via `types.HttpOptions(api_version='v1beta')`
  to ensure full compatibility with developer instructions / system_instruction.
- Clear, anti-hallucination system instructions preventing fabrication of facts, metrics, or credentials.
- Robust error handling returning meaningful errors without displaying fake AI responses.
"""

import os
import json
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# Check if official google-genai SDK is available
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-genai SDK is not installed or importable.")

# Default supported model (can be overridden via GEMINI_MODEL env var)
DEFAULT_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')


def get_client() -> Tuple[Optional[Any], str, bool]:
    """
    Initialize and return the official Google GenAI client configured with v1beta.
    Returns: (client, model_name, is_configured)
    """
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    model_name = os.getenv('GEMINI_MODEL', DEFAULT_MODEL).strip() or DEFAULT_MODEL

    if not api_key:
        return None, model_name, False

    if not GENAI_AVAILABLE:
        return None, model_name, False

    try:
        # Explicitly configure api_version='v1beta' to enable system_instruction / developer instructions
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(api_version='v1beta')
        )
        return client, model_name, True
    except Exception as exc:
        logger.error(f"Error creating GenAI client: {exc}")
        return None, model_name, False


def clean_markdown_fences(text: str) -> str:
    """Removes ```json or ``` markdown wrapper if present."""
    text = text.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        # Drop opening ``` or ```json
        if lines[0].startswith('```'):
            lines = lines[1:]
        # Drop closing ```
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines).strip()
    return text


def clean_ai_summary_text(text: str) -> str:
    """
    Cleans raw AI response for Professional Summary:
    - Retains only ONE cohesive summary (extracts first if variations were output).
    - Removes conversational intros (e.g. 'Here is your summary:', 'Sure!').
    - Removes headings like '**Professional Summary:**' or '### Summary'.
    - Strips raw markdown asterisks, hashes, and formatting markers.
    - Returns clean, cohesive 3-4 sentence plain text ready for resume insertion.
    """
    if not text:
        return ""
    import re
    text = text.strip()

    # If the response returned multiple variations (e.g. Variation 1 ... Variation 2), isolate the first one
    var_match = re.search(
        r'(?:variation|option)\s*1\s*[:\-]*(.*?)(?:(?:\*\*|\#\#)?\s*(?:variation|option)\s*2|$)',
        text,
        re.IGNORECASE | re.DOTALL
    )
    if var_match and len(var_match.group(1).strip()) > 20:
        text = var_match.group(1).strip()

    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Plain text without markdown symbols
        plain = re.sub(r'[\*\#\_`]', '', stripped).strip()
        # Drop conversational intro phrases or option labels
        if re.match(r'^(?:here\s+(?:is|are)|sure|below\s+is|certainly|tailored\s+summary|summary\s*:|professional\s+summary|concise|detailed|option\s*\d|variation\s*\d)', plain, re.IGNORECASE):
            continue
        # Drop if line is just a title or header
        if plain.lower() in ['summary', 'summary:', 'professional summary', 'professional summary:', 'overview', 'career summary']:
            continue
        # Remove bullet markers if mistakenly present in summary
        clean_line = re.sub(r'^[•\-\*\+]\s*', '', plain)
        if clean_line:
            cleaned_lines.append(clean_line)

    result = ' '.join(cleaned_lines).strip()
    # Final check: remove any lingering markdown asterisks or double spaces
    result = re.sub(r'[\*\#\_`]', '', result)
    result = re.sub(r'\s{2,}', ' ', result).strip()
    return result


def clean_ai_bullet_text(text: str) -> str:
    """
    Cleans AI responses for bulleted experience and project descriptions:
    - Removes conversational intros and trailing advisory notes.
    - Ensures each line starts with a clean bullet marker (• ).
    - Preserves internal bold/italic markers so frontend parser can render them into HTML.
    """
    if not text:
        return ""
    import re
    lines = text.strip().split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        plain = re.sub(r'[\*\#\_`]', '', stripped).strip()
        # Drop conversational intros
        if re.match(r'^(?:here\s+(?:is|are)|sure|below\s+is|certainly|improved\s+bullet|project\s+bullet|bullet\s+points?:)', plain, re.IGNORECASE):
            continue
        # Drop trailing advisory notes like '*Note: You can add metrics...*'
        if re.match(r'^(?:note|tip|recommendation|advice)\s*[:\-]', plain, re.IGNORECASE):
            continue
        # Normalize bullet markers
        bullet_text = re.sub(r'^(?:[•\u2022]\s*|[\-\*\+]\s+|\d+[\.\)]\s+)', '', stripped).strip()
        if bullet_text:
            cleaned_lines.append(f"• {bullet_text}")
    return '\n'.join(cleaned_lines) if cleaned_lines else text.strip()


def execute_gemini_prompt(
    prompt: str,
    system_instruction: str = None,
    json_mode: bool = False,
    max_output_tokens: int = 1500
) -> Dict[str, Any]:
    """
    Executes a prompt against the Gemini API using the official SDK (v1beta).
    Returns real Gemini responses or clean, meaningful error messages.
    """
    client, configured_model, is_configured = get_client()

    if not is_configured:
        return {
            "success": False,
            "error_type": "MISSING_KEY",
            "message": (
                "Gemini API key is not configured. "
                "Please set GEMINI_API_KEY in your .env file or environment variables. "
                "You can get a free key at https://aistudio.google.com/."
            )
        }

    config_args = {
        "temperature": 0.3 if json_mode else 0.5,
        "max_output_tokens": max_output_tokens,
    }
    if system_instruction:
        config_args["system_instruction"] = system_instruction
    if json_mode:
        config_args["response_mime_type"] = "application/json"

    config = types.GenerateContentConfig(**config_args)

    # Models to attempt (starting with configured model)
    models_to_try = [configured_model]
    for alt in ['gemini-2.5-flash', 'gemini-3-flash-preview', 'gemini-3.1-pro-preview']:
        if alt not in models_to_try:
            models_to_try.append(alt)

    last_error_msg = ""
    for current_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=prompt,
                config=config
            )
            response_text = response.text or ""
            return {
                "success": True,
                "text": response_text,
                "model": current_model
            }
        except Exception as exc:
            last_error_msg = str(exc)
            logger.warning(f"Gemini API call with model '{current_model}' failed: {last_error_msg}")
            # If invalid auth, trying other models won't help
            if "API_KEY_INVALID" in last_error_msg or "403" in last_error_msg or "401" in last_error_msg:
                return {
                    "success": False,
                    "error_type": "AUTH_ERROR",
                    "message": "Invalid Gemini API key. Please check your GEMINI_API_KEY configuration."
                }
            continue

    if "RESOURCE_EXHAUSTED" in last_error_msg or "429" in last_error_msg:
        return {
            "success": False,
            "error_type": "RATE_LIMIT",
            "message": "Gemini API rate limit reached (429). Please wait a few seconds and try again."
        }

    return {
        "success": False,
        "error_type": "API_ERROR",
        "message": f"Gemini API error: {last_error_msg}"
    }


# ==============================================================================
# FEATURE 1: AI PROFESSIONAL SUMMARY GENERATOR
# ==============================================================================
def generate_summary(
    education: str = "",
    skills: str = "",
    experience: str = "",
    career_goal: str = ""
) -> Dict[str, Any]:
    """
    Generates exactly ONE concise, high-impact professional resume summary (3-4 sentences)
    based on factual input provided by the user.
    Strictly forbids introductions, variations, headings, and markdown formatting.
    """
    system_instruction = (
        "You are an expert resume writer and career strategist for tech and professional roles. "
        "Your task is to write exactly ONE final, polished professional resume summary consisting of 3 to 4 concise, cohesive sentences. "
        "Strict rules: "
        "1. Generate only ONE final summary paragraph (3-4 sentences). Never provide multiple variations, options, or alternate versions. "
        "2. Do NOT include any conversational preamble, greeting, or intro (e.g. 'Here is your summary:', 'Here is a...', or 'Professional Summary:'). "
        "3. Do NOT include headings, bullet points, numbers, or section labels. "
        "4. Do NOT use Markdown formatting (no asterisks **, no hashes #, no underscores __). "
        "5. Never invent companies, unmentioned credentials, years of experience, or unmentioned skills. "
        "6. Return ONLY clean, plain resume text that is immediately ready to place directly onto a resume."
    )

    prompt = (
        f"Generate exactly ONE final professional resume summary (3–4 concise, professional sentences) based ONLY on these details:\n"
        f"- Education: {education or 'Not provided'}\n"
        f"- Core Skills: {skills or 'Not provided'}\n"
        f"- Work/Project Experience: {experience or 'Not provided'}\n"
        f"- Target Role / Career Goal: {career_goal or 'Not provided'}\n\n"
        f"IMPORTANT INSTRUCTIONS:\n"
        f"- Write only ONE single cohesive paragraph of 3-4 sentences.\n"
        f"- Do NOT include intro phrases such as 'Here is your summary' or 'Here are variations'.\n"
        f"- Do NOT include headings, bullet points, or multiple options.\n"
        f"- Do NOT use Markdown asterisks or formatting.\n"
        f"- Return only clean, professional text."
    )

    result = execute_gemini_prompt(prompt, system_instruction=system_instruction)

    if not result["success"]:
        return {
            "success": False,
            "message": result.get("message", "Failed to generate professional summary.")
        }

    cleaned_summary = clean_ai_summary_text(result["text"])

    return {
        "success": True,
        "summary": cleaned_summary,
        "model": result.get("model")
    }


# ==============================================================================
# FEATURE 2: AI EXPERIENCE IMPROVER
# ==============================================================================
def improve_experience(
    job_title: str = "",
    company: str = "",
    description: str = ""
) -> Dict[str, Any]:
    """
    Rewrites a basic job/internship description into high-impact, professional
    resume bullet points using the Action-Verb + Task + Outcome framework.
    Strictly forbids hallucinating numbers, metrics, or non-existent tools.
    """
    if not description.strip():
        return {"success": False, "message": "Please provide your initial experience description to improve."}

    system_instruction = (
        "You are an executive resume coach. "
        "Rules: Rewrite the user's raw experience into 3-4 professional, ATS-optimized bullet points. "
        "Apply the Google XYZ formula: 'Accomplished [X] as measured by [Y], by doing [Z]'. "
        "CRITICAL: Do NOT invent numbers, percentages, dollar amounts, or fabricated metrics. "
        "If a metric is missing, use placeholders like '[X%]' or '[specific metric]' so the user can fill in real numbers. "
        "Do NOT invent technologies or duties the user did not mention. "
        "Start every bullet with a clean bullet marker '• ' followed by a strong action verb (e.g., Architected, Engineered, Implemented, Streamlined, Spearheaded). "
        "Do NOT include any conversational preamble or trailing advisory notes."
    )

    prompt = (
        f"Job Title: {job_title or 'Engineer/Intern'}\n"
        f"Company/Organization: {company or 'Tech Organization'}\n"
        f"Raw Description to improve:\n{description}\n\n"
        f"Rewrite this into 3-4 polished, high-impact resume bullet points starting with '• '. "
        f"Do NOT include introductory phrases or trailing commentary."
    )

    result = execute_gemini_prompt(prompt, system_instruction=system_instruction)

    if not result["success"]:
        return {
            "success": False,
            "message": result.get("message", "Failed to improve experience description.")
        }

    cleaned_bullets = clean_ai_bullet_text(result["text"])

    return {
        "success": True,
        "improved_text": cleaned_bullets,
        "model": result.get("model")
    }


# ==============================================================================
# FEATURE 3: AI PROJECT DESCRIPTION GENERATOR
# ==============================================================================
def generate_project_description(
    project_name: str,
    technologies: str,
    functionality: str
) -> Dict[str, Any]:
    """
    Transforms project details into professional resume bullet points highlighting
    architecture, tech stack implementation, and technical problem solving.
    """
    if not project_name.strip() and not functionality.strip():
        return {"success": False, "message": "Please specify the project name and main functionality."}

    system_instruction = (
        "You are a technical hiring manager and resume expert. "
        "Strict rules: Never invent functionality that the user did not provide. "
        "Never invent performance numbers or claim unrealized scale. "
        "Structure the output into 3-4 professional resume bullet points emphasizing: "
        "1. Core architecture & purpose using the specified technologies. "
        "2. Key technical features and implementation methodology. "
        "3. Security, efficiency, and engineering best practices applied. "
        "Start each bullet point with '• '. Do NOT include conversational greetings or conclusions."
    )

    prompt = (
        f"Project Name: {project_name}\n"
        f"Technologies Used: {technologies or 'Modern Software Stack'}\n"
        f"Main Functionality & Overview:\n{functionality}\n\n"
        f"Generate 3-4 ATS-friendly resume bullet points starting with '• '. "
        f"Do NOT include introductory sentences or notes."
    )

    result = execute_gemini_prompt(prompt, system_instruction=system_instruction)

    if not result["success"]:
        return {
            "success": False,
            "message": result.get("message", "Failed to generate project description.")
        }

    cleaned_bullets = clean_ai_bullet_text(result["text"])

    return {
        "success": True,
        "description": cleaned_bullets,
        "model": result.get("model")
    }


# ==============================================================================
# FEATURE 4: AI SKILL SUGGESTIONS
# ==============================================================================
def suggest_skills(
    career_role: str,
    existing_skills: str
) -> Dict[str, Any]:
    """
    Analyzes the user's targeted career role and current skills, providing:
    - Confirmed existing skills
    - Recommended skills to learn (categorized into Languages, Frameworks, Tools, Concepts)
    Returns structured JSON.
    """
    system_instruction = (
        "You are a technical career advisor. Given a career role and a candidate's current skills, "
        "suggest relevant, industry-in-demand skills that would strengthen their profile for that specific role. "
        "You must return ONLY a valid JSON object matching this schema: "
        "{"
        "  \"current_skills\": [\"skill1\", \"skill2\"],"
        "  \"recommended_to_learn\": {"
        "    \"core_technical\": [\"skillA\", \"skillB\"],"
        "    \"frameworks_tools\": [\"toolA\", \"toolB\"],"
        "    \"domain_concepts\": [\"conceptA\", \"conceptB\"]"
        "  },"
        "  \"role_insight\": \"Short 1-sentence market demand perspective for this role.\""
        "}"
    )

    prompt = (
        f"Target Career Role: {career_role or 'Full Stack Software Engineer'}\n"
        f"Existing Skills: {existing_skills or 'Python, JavaScript, HTML, CSS'}\n"
    )

    result = execute_gemini_prompt(
        prompt,
        system_instruction=system_instruction,
        json_mode=True
    )

    if not result["success"]:
        return {
            "success": False,
            "message": result.get("message", "Failed to suggest skills.")
        }

    try:
        cleaned = clean_markdown_fences(result["text"])
        parsed = json.loads(cleaned)
        return {
            "success": True,
            "data": parsed,
            "model": result.get("model")
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"Failed to parse skill suggestions from Gemini response: {exc}"
        }


# ==============================================================================
# FEATURE 5: ATS RESUME ANALYZER (DYNAMIC DUAL-LAYER ENGINE)
# ==============================================================================

# Generic words, filler verbs, and role titles that must NEVER be classified as technical skills
GENERIC_OR_ROLE_TERMS = {
    "developer", "backend", "frontend", "full stack", "full-stack", "fullstack",
    "engineer", "software engineer", "coder", "programmer", "architect",
    "specialist", "consultant", "lead", "manager", "intern", "internship",
    "fresher", "junior", "senior", "mid-level", "staff", "principal",
    "experience", "responsible", "responsibility", "responsibilities", "team",
    "work", "role", "candidate", "looking", "skilled", "requirements",
    "qualifications", "strong", "knowledge", "years", "plus", "ability",
    "degree", "bachelor", "master", "company", "applicant", "position",
    "hands-on", "proficiency", "written", "verbal", "communication"
}

# Structured ontology of genuine technical skills, languages, frameworks,
# databases, cloud/devops tools, and core engineering competencies.
# Each entry specifies its canonical name, category, and alias patterns (regexes) for robust matching.
TECH_ONTOLOGY = [
    # Programming Languages
    {
        "canonical": "JavaScript",
        "category": "Programming Language",
        "aliases": [r"\bjavascript\b", r"\bjs\b", r"\becmascript\b"]
    },
    {
        "canonical": "TypeScript",
        "category": "Programming Language",
        "aliases": [r"\btypescript\b", r"\bts\b"]
    },
    {
        "canonical": "Python",
        "category": "Programming Language",
        "aliases": [r"\bpython(?:3)?\b"]
    },
    {
        "canonical": "Java",
        "category": "Programming Language",
        "aliases": [r"\bjava\b(?!\s*script)"]
    },
    {
        "canonical": "C++",
        "category": "Programming Language",
        "aliases": [r"\bc\+\+\b", r"\bcpp\b"]
    },
    {
        "canonical": "C#",
        "category": "Programming Language",
        "aliases": [r"\bc#\b", r"\bcsharp\b", r"\bc-sharp\b"]
    },
    {
        "canonical": "Go",
        "category": "Programming Language",
        "aliases": [r"\bgolang\b", r"\bgo\s+language\b", r"\bgo\s+programming\b"]
    },
    {
        "canonical": "Rust",
        "category": "Programming Language",
        "aliases": [r"\brust\b", r"\brustlang\b"]
    },
    {
        "canonical": "PHP",
        "category": "Programming Language",
        "aliases": [r"\bphp\b"]
    },
    {
        "canonical": "Ruby",
        "category": "Programming Language",
        "aliases": [r"\bruby\b", r"\bruby\s+on\s+rails\b"]
    },
    {
        "canonical": "Kotlin",
        "category": "Programming Language",
        "aliases": [r"\bkotlin\b"]
    },
    {
        "canonical": "Swift",
        "category": "Programming Language",
        "aliases": [r"\bswift\b", r"\bswiftui\b"]
    },
    {
        "canonical": "Dart",
        "category": "Programming Language",
        "aliases": [r"\bdart\b"]
    },
    {
        "canonical": "Scala",
        "category": "Programming Language",
        "aliases": [r"\bscala\b"]
    },
    {
        "canonical": "SQL",
        "category": "Database / Query Language",
        "aliases": [r"\bsql\b", r"\brdbms\b", r"\brelational\s+databases?\b"]
    },
    {
        "canonical": "HTML",
        "category": "Web Technology",
        "aliases": [r"\bhtml5?\b"]
    },
    {
        "canonical": "CSS",
        "category": "Web Technology",
        "aliases": [r"\bcss3?\b"]
    },
    {
        "canonical": "Bash",
        "category": "Scripting & Shell",
        "aliases": [r"\bbash\b", r"\bshell\s+scripting\b", r"\bpowershell\b"]
    },

    # Frameworks & Libraries
    {
        "canonical": "React",
        "category": "Frontend Framework",
        "aliases": [r"\breact(?:\.js|js)?\b", r"\breact\s+native\b"]
    },
    {
        "canonical": "Node.js",
        "category": "Backend Runtime",
        "aliases": [r"\bnode(?:\.js|js)?\b", r"\bnode\s+js\b"]
    },
    {
        "canonical": "Express.js",
        "category": "Backend Framework",
        "aliases": [r"\bexpress(?:\.js|js)?\b", r"\bexpress\s+js\b"]
    },
    {
        "canonical": "Next.js",
        "category": "Full Stack Framework",
        "aliases": [r"\bnext(?:\.js|js)?\b", r"\bnext\s+js\b"]
    },
    {
        "canonical": "Vue.js",
        "category": "Frontend Framework",
        "aliases": [r"\bvue(?:\.js|js)?\b", r"\bvue\s+js\b"]
    },
    {
        "canonical": "Angular",
        "category": "Frontend Framework",
        "aliases": [r"\bangular(?:js)?\b"]
    },
    {
        "canonical": "Django",
        "category": "Backend Framework",
        "aliases": [r"\bdjango\b", r"\bdrf\b", r"\bdjango\s+rest\s+framework\b"]
    },
    {
        "canonical": "Flask",
        "category": "Backend Framework",
        "aliases": [r"\bflask\b"]
    },
    {
        "canonical": "FastAPI",
        "category": "Backend Framework",
        "aliases": [r"\bfastapi\b", r"\bfast\s+api\b"]
    },
    {
        "canonical": "Spring Boot",
        "category": "Backend Framework",
        "aliases": [r"\bspring\s*boot\b", r"\bspring\s+framework\b"]
    },
    {
        "canonical": ".NET",
        "category": "Backend Framework",
        "aliases": [r"\basp\.net\b", r"\b\.net(?:\s+core)?\b", r"\bdotnet\b"]
    },
    {
        "canonical": "Laravel",
        "category": "Backend Framework",
        "aliases": [r"\blaravel\b"]
    },
    {
        "canonical": "Bootstrap",
        "category": "CSS Framework",
        "aliases": [r"\bbootstrap(?:\s+5|\s+4)?\b"]
    },
    {
        "canonical": "Tailwind CSS",
        "category": "CSS Framework",
        "aliases": [r"\btailwind(?:\s*css)?\b"]
    },
    {
        "canonical": "Redux",
        "category": "State Management",
        "aliases": [r"\bredux(?:\s+toolkit)?\b"]
    },
    {
        "canonical": "GraphQL",
        "category": "API Technology",
        "aliases": [r"\bgraphql\b", r"\bapollo\s+graphql\b"]
    },
    {
        "canonical": "REST APIs",
        "category": "API Architecture",
        "aliases": [r"\brestful?\s+apis?\b", r"\brest\s+apis?\b", r"\brestful\b", r"\brest\b(?!\s+assured)"]
    },
    {
        "canonical": "jQuery",
        "category": "Frontend Library",
        "aliases": [r"\bjquery\b"]
    },

    # Databases & Caching
    {
        "canonical": "MongoDB",
        "category": "NoSQL Database",
        "aliases": [r"\bmongodb\b", r"\bmongo\b"]
    },
    {
        "canonical": "PostgreSQL",
        "category": "Relational Database",
        "aliases": [r"\bpostgresql\b", r"\bpostgres\b"]
    },
    {
        "canonical": "MySQL",
        "category": "Relational Database",
        "aliases": [r"\bmysql\b"]
    },
    {
        "canonical": "SQLite",
        "category": "Database",
        "aliases": [r"\bsqlite3?\b"]
    },
    {
        "canonical": "Redis",
        "category": "In-Memory Database / Caching",
        "aliases": [r"\bredis\b"]
    },
    {
        "canonical": "Cassandra",
        "category": "NoSQL Database",
        "aliases": [r"\bcassandra\b", r"\bapache\s+cassandra\b"]
    },
    {
        "canonical": "Elasticsearch",
        "category": "Search & Analytics",
        "aliases": [r"\belasticsearch\b", r"\belk\s+stack\b"]
    },
    {
        "canonical": "DynamoDB",
        "category": "NoSQL Database",
        "aliases": [r"\bdynamodb\b"]
    },
    {
        "canonical": "Firebase",
        "category": "Cloud Database / BaaS",
        "aliases": [r"\bfirebase\b", r"\bfirestore\b"]
    },
    {
        "canonical": "Oracle DB",
        "category": "Relational Database",
        "aliases": [r"\boracle(?:\s+db|\s+database)?\b", r"\bpl/sql\b"]
    },

    # Cloud, DevOps & Platforms
    {
        "canonical": "AWS",
        "category": "Cloud Platform",
        "aliases": [r"\baws\b", r"\bamazon\s+web\s+services\b", r"\bec2\b", r"\bs3\b", r"\blambda\b"]
    },
    {
        "canonical": "Azure",
        "category": "Cloud Platform",
        "aliases": [r"\bazure\b", r"\bmicrosoft\s+azure\b"]
    },
    {
        "canonical": "GCP",
        "category": "Cloud Platform",
        "aliases": [r"\bgcp\b", r"\bgoogle\s+cloud(?:\s+platform)?\b"]
    },
    {
        "canonical": "Docker",
        "category": "DevOps & Containers",
        "aliases": [r"\bdocker\b", r"\bcontainerization\b", r"\bcontainers?\b", r"\bdockerfile\b", r"\bdocker\s+compose\b"]
    },
    {
        "canonical": "Kubernetes",
        "category": "DevOps & Orchestration",
        "aliases": [r"\bkubernetes\b", r"\bk8s\b"]
    },
    {
        "canonical": "Git",
        "category": "Version Control",
        "aliases": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b", r"\bversion\s+control\b"]
    },
    {
        "canonical": "CI/CD",
        "category": "DevOps & CI/CD",
        "aliases": [r"\bci/cd\b", r"\bci\s+cd\b", r"\bcontinuous\s+integration\b", r"\bcontinuous\s+deployment\b"]
    },
    {
        "canonical": "Jenkins",
        "category": "DevOps Tool",
        "aliases": [r"\bjenkins\b"]
    },
    {
        "canonical": "Linux",
        "category": "Operating System & Environment",
        "aliases": [r"\blinux\b", r"\bubuntu\b", r"\bunix\b"]
    },
    {
        "canonical": "Terraform",
        "category": "Infrastructure as Code",
        "aliases": [r"\bterraform\b", r"\biac\b"]
    },
    {
        "canonical": "Ansible",
        "category": "Configuration Management",
        "aliases": [r"\bansible\b"]
    },
    {
        "canonical": "Kafka",
        "category": "Event Streaming",
        "aliases": [r"\bkafka\b", r"\bapache\s+kafka\b"]
    },
    {
        "canonical": "RabbitMQ",
        "category": "Message Queue",
        "aliases": [r"\brabbitmq\b"]
    },
    {
        "canonical": "Nginx",
        "category": "Web Server / Reverse Proxy",
        "aliases": [r"\bnginx\b"]
    },
    {
        "canonical": "Microservices",
        "category": "System Architecture",
        "aliases": [r"\bmicroservices?\b", r"\bmicroservice\s+architecture\b"]
    },

    # Testing & Methodologies
    {
        "canonical": "Unit Testing",
        "category": "Testing & QA",
        "aliases": [r"\bunit\s+testing\b", r"\bunit\s+tests?\b", r"\btdd\b", r"\btest\s+driven\s+development\b"]
    },
    {
        "canonical": "PyTest",
        "category": "Testing Tool",
        "aliases": [r"\bpytest\b"]
    },
    {
        "canonical": "Jest",
        "category": "Testing Tool",
        "aliases": [r"\bjest\b"]
    },
    {
        "canonical": "Selenium",
        "category": "Testing Tool",
        "aliases": [r"\bselenium\b", r"\bcypress\b", r"\bplaywright\b"]
    },
    {
        "canonical": "Agile",
        "category": "Methodology",
        "aliases": [r"\bagile\b", r"\bscrum\b", r"\bkanban\b"]
    },

    # Core CS & Data Concepts
    {
        "canonical": "Data Structures & Algorithms",
        "category": "Core Computer Science",
        "aliases": [r"\bdata\s+structures\b", r"\balgorithms?\b", r"\bdsa\b"]
    },
    {
        "canonical": "OOP",
        "category": "Core Computer Science",
        "aliases": [r"\boop\b", r"\bobject[\s-]oriented\b"]
    },
    {
        "canonical": "System Design",
        "category": "System Architecture",
        "aliases": [r"\bsystem\s+design\b", r"\bdistributed\s+systems?\b", r"\bscalability\b"]
    },
    {
        "canonical": "Machine Learning",
        "category": "Data Science & AI",
        "aliases": [r"\bmachine\s+learning\b", r"\bml\b"]
    },
    {
        "canonical": "Deep Learning",
        "category": "Data Science & AI",
        "aliases": [r"\bdeep\s+learning\b", r"\bdl\b"]
    },
    {
        "canonical": "Artificial Intelligence",
        "category": "Data Science & AI",
        "aliases": [r"\bartificial\s+intelligence\b", r"\bai\b"]
    },
    {
        "canonical": "NLP",
        "category": "Data Science & AI",
        "aliases": [r"\bnatural\s+language\s+processing\b", r"\bnlp\b"]
    },
    {
        "canonical": "Pandas",
        "category": "Data Science Library",
        "aliases": [r"\bpandas\b"]
    },
    {
        "canonical": "NumPy",
        "category": "Data Science Library",
        "aliases": [r"\bnumpy\b"]
    },
    {
        "canonical": "TensorFlow",
        "category": "Machine Learning Framework",
        "aliases": [r"\btensorflow\b", r"\btf\b"]
    },
    {
        "canonical": "PyTorch",
        "category": "Machine Learning Framework",
        "aliases": [r"\bpytorch\b"]
    },
    {
        "canonical": "Scikit-Learn",
        "category": "Machine Learning Framework",
        "aliases": [r"\bscikit[\s-]learn\b", r"\bsklearn\b"]
    }
]

# Quick lookup by canonical name
TECH_BY_CANONICAL = {item["canonical"]: item for item in TECH_ONTOLOGY}

# Industry standard benchmark requirements for common engineering roles.
# If the user enters a role title (e.g., "backend developer", "frontend engineer", "full stack"),
# the ATS scanner evaluates the resume against standard competencies for that role.
ROLE_BENCHMARKS = {
    "backend": {
        "title": "Backend Developer",
        "skills": ["Python", "SQL", "PostgreSQL", "REST APIs", "Docker", "Git", "Microservices", "System Design"]
    },
    "frontend": {
        "title": "Frontend Developer",
        "skills": ["JavaScript", "React", "HTML", "CSS", "TypeScript", "Next.js", "REST APIs", "Git"]
    },
    "full stack": {
        "title": "Full Stack Developer",
        "skills": ["JavaScript", "React", "Node.js", "Express.js", "MongoDB", "SQL", "REST APIs", "Git", "Docker"]
    },
    "fullstack": {
        "title": "Full Stack Developer",
        "skills": ["JavaScript", "React", "Node.js", "Express.js", "MongoDB", "SQL", "REST APIs", "Git", "Docker"]
    },
    "python": {
        "title": "Python Developer",
        "skills": ["Python", "Django", "FastAPI", "SQL", "PostgreSQL", "REST APIs", "Git", "Docker", "Data Structures & Algorithms"]
    },
    "java": {
        "title": "Java Developer",
        "skills": ["Java", "Spring Boot", "Microservices", "SQL", "PostgreSQL", "REST APIs", "Git", "Docker", "OOP"]
    },
    "react": {
        "title": "React Frontend Developer",
        "skills": ["React", "JavaScript", "TypeScript", "Redux", "Next.js", "HTML", "CSS", "REST APIs", "Git"]
    },
    "node": {
        "title": "Node.js Backend Developer",
        "skills": ["Node.js", "Express.js", "JavaScript", "TypeScript", "MongoDB", "PostgreSQL", "REST APIs", "Docker", "Git"]
    },
    "mern": {
        "title": "MERN Stack Developer",
        "skills": ["MongoDB", "Express.js", "React", "Node.js", "JavaScript", "REST APIs", "HTML", "CSS", "Git"]
    },
    "data science": {
        "title": "Data Scientist / ML Engineer",
        "skills": ["Python", "Machine Learning", "Deep Learning", "SQL", "Pandas", "NumPy", "TensorFlow", "PyTorch", "Data Structures & Algorithms"]
    },
    "data engineer": {
        "title": "Data Engineer",
        "skills": ["Python", "SQL", "PostgreSQL", "Kafka", "Data Structures & Algorithms", "Docker", "Linux", "Git"]
    },
    "machine learning": {
        "title": "Machine Learning Engineer",
        "skills": ["Python", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Pandas", "NumPy", "NLP", "Scikit-Learn"]
    },
    "devops": {
        "title": "DevOps / Cloud Engineer",
        "skills": ["Docker", "Kubernetes", "AWS", "Linux", "CI/CD", "Terraform", "Git", "Bash", "Nginx"]
    },
    "cloud": {
        "title": "Cloud Engineer",
        "skills": ["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Linux", "CI/CD", "Microservices", "Terraform"]
    },
    "software engineer": {
        "title": "Software Engineer / SDE",
        "skills": ["Data Structures & Algorithms", "OOP", "System Design", "Git", "SQL", "REST APIs", "Unit Testing", "CI/CD"]
    },
    "sde": {
        "title": "Software Development Engineer (SDE)",
        "skills": ["Data Structures & Algorithms", "OOP", "System Design", "Git", "SQL", "REST APIs", "Unit Testing", "CI/CD"]
    },
    "web developer": {
        "title": "Web Developer",
        "skills": ["HTML", "CSS", "JavaScript", "React", "Node.js", "SQL", "REST APIs", "Git", "Bootstrap"]
    },
    "mobile": {
        "title": "Mobile App Developer",
        "skills": ["Dart", "Kotlin", "Swift", "React", "JavaScript", "REST APIs", "Git"]
    },
    "android": {
        "title": "Android Developer",
        "skills": ["Kotlin", "Java", "REST APIs", "Git", "OOP"]
    },
    "ios": {
        "title": "iOS Developer",
        "skills": ["Swift", "REST APIs", "Git", "OOP"]
    },
    "qa": {
        "title": "QA / Automation Engineer",
        "skills": ["Selenium", "PyTest", "Jest", "Unit Testing", "Python", "JavaScript", "CI/CD", "Git"]
    }
}


def is_resume_substantially_empty(resume_data: Any) -> bool:
    """Checks whether the candidate resume contains substantial content."""
    if not isinstance(resume_data, dict) or not resume_data:
        return True

    p = resume_data.get('personal', {})
    s = resume_data.get('skills', {})
    edu = resume_data.get('education', [])
    exp = resume_data.get('experience', [])
    proj = resume_data.get('projects', [])

    has_personal = bool(
        str(p.get('fullName', '')).strip() or
        str(p.get('summary', '')).strip() or
        str(p.get('professionalTitle', '')).strip()
    )
    has_skills = any(
        bool(str(s.get(k, '')).strip())
        for k in ['languages', 'frameworks', 'tools', 'technical']
    )
    has_edu = any(
        bool(str(e.get('degree', '')).strip() or str(e.get('institution', '')).strip())
        for e in edu if isinstance(e, dict)
    )
    has_exp = any(
        bool(str(x.get('company', '')).strip() or str(x.get('role', '')).strip() or str(x.get('description', '')).strip())
        for x in exp if isinstance(x, dict)
    )
    has_proj = any(
        bool(str(pr.get('name', '')).strip() or str(pr.get('technologies', '')).strip() or str(pr.get('description', '')).strip())
        for pr in proj if isinstance(pr, dict)
    )

    return not (has_personal or has_skills or has_edu or has_exp or has_proj)


def extract_meaningful_job_requirements(jd_text: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Extracts genuine technical requirements from a job description.
    Supports two modes:
    1. Explicit Requirements: Detects specific tools, languages, and frameworks in the text.
    2. Role Benchmark Expansion: If only a target role title was entered (e.g., 'backend developer',
       'frontend engineer', 'full stack'), it maps the role to industry standard technical competencies.
    Returns: (list_of_req_items, detected_role_title_or_None)
    """
    import re
    if not jd_text or not isinstance(jd_text, str):
        return [], None

    jd_lower = jd_text.lower().strip()
    seen = set()
    matches_with_pos = []

    # 1. Scan for explicit technical competencies in the JD
    for item in TECH_ONTOLOGY:
        canonical = item["canonical"]
        if canonical in seen:
            continue

        best_pos = -1
        for alias in item["aliases"]:
            m = re.search(alias, jd_lower)
            if m:
                if best_pos == -1 or m.start() < best_pos:
                    best_pos = m.start()

        if best_pos != -1:
            seen.add(canonical)
            matches_with_pos.append((best_pos, item))

    # If explicit technologies were found, use them
    if matches_with_pos:
        matches_with_pos.sort(key=lambda x: x[0])
        return [item for _, item in matches_with_pos], None

    # 2. If no explicit technologies found, check if a target role was entered (e.g. 'backend developer')
    detected_role_title = None
    for role_key, role_info in ROLE_BENCHMARKS.items():
        pattern = r'(?<![a-z0-9])' + re.escape(role_key) + r'(?![a-z0-9])'
        if re.search(pattern, jd_lower):
            detected_role_title = role_info["title"]
            for skill_name in role_info["skills"]:
                if skill_name in TECH_BY_CANONICAL and skill_name not in seen:
                    seen.add(skill_name)
                    matches_with_pos.append((len(matches_with_pos), TECH_BY_CANONICAL[skill_name]))
            break

    if matches_with_pos and detected_role_title:
        return [item for _, item in matches_with_pos], detected_role_title

    return [], None


def check_skill_match_in_text(item: Dict[str, Any], text: str) -> bool:
    """Checks whether any alias of a technical skill appears in the given text."""
    import re
    if not text:
        return False
    text_lower = text.lower()
    for alias in item["aliases"]:
        if re.search(alias, text_lower):
            return True
    return False


def calculate_dynamic_ats_score(resume_data: Any, job_description: str) -> Dict[str, Any]:
    """
    Evaluates candidate resume data against the job description using a 5-pillar weighted model:
    1. Required Technical Skills: 40% (40 points max)
    2. Relevant Experience and Projects: 25% (25 points max)
    3. Education and Qualifications: 15% (15 points max)
    4. Relevant Keywords and Competencies: 10% (10 points max)
    5. Resume Completeness and Formatting: 10% (10 points max)

    Total score is normalized strictly between 0 and 100 with full explanations for every point.
    Never returns hardcoded or arbitrary scores.
    """
    import re

    # 1. Validation: Job description must be provided
    if not job_description or not str(job_description).strip():
        return {
            "success": False,
            "message": "Please paste a target Job Description first to run the ATS scan."
        }

    # 2. Validation: Resume must contain substantial content
    if is_resume_substantially_empty(resume_data):
        return {
            "success": False,
            "message": "Your resume appears to be empty. Please enter your skills, work experience, projects, or education in the editor before running the ATS scan."
        }

    p = resume_data.get('personal', {})
    s = resume_data.get('skills', {})
    edu = resume_data.get('education', [])
    exp = resume_data.get('experience', [])
    proj = resume_data.get('projects', [])
    cert = resume_data.get('certifications', [])
    ach = resume_data.get('achievements', [])

    # Extract all resume content sections
    resume_full_parts = [
        p.get('fullName', ''),
        p.get('professionalTitle', ''),
        p.get('summary', ''),
        p.get('location', ''),
        s.get('languages', ''),
        s.get('frameworks', ''),
        s.get('tools', ''),
        s.get('technical', ''),
        s.get('soft', ''),
    ]

    for e in edu:
        if isinstance(e, dict):
            resume_full_parts.extend([e.get('institution', ''), e.get('degree', ''), e.get('specialization', '')])
    for x in exp:
        if isinstance(x, dict):
            resume_full_parts.extend([x.get('company', ''), x.get('role', ''), x.get('description', '')])
    for pr in proj:
        if isinstance(pr, dict):
            resume_full_parts.extend([pr.get('name', ''), pr.get('technologies', ''), pr.get('description', '')])
    for c in cert:
        if isinstance(c, dict):
            resume_full_parts.extend([c.get('name', ''), c.get('organization', '')])
    for a in ach:
        if isinstance(a, dict):
            resume_full_parts.extend([a.get('title', ''), a.get('description', '')])

    resume_full_text = ' '.join(resume_full_parts).lower()

    resume_skills_text = ' '.join([
        s.get('languages', ''),
        s.get('frameworks', ''),
        s.get('tools', ''),
        s.get('technical', '')
    ]).lower()

    resume_exp_proj_text = ' '.join([
        ' '.join([f"{x.get('company', '')} {x.get('role', '')} {x.get('description', '')}" for x in exp if isinstance(x, dict)]),
        ' '.join([f"{pr.get('name', '')} {pr.get('technologies', '')} {pr.get('description', '')}" for pr in proj if isinstance(pr, dict)])
    ]).lower()

    # 3. Extract meaningful job requirements (excluding generic words & roles)
    extracted_reqs, detected_role = extract_meaningful_job_requirements(str(job_description))

    # If no meaningful technical requirements were found in the job description:
    if not extracted_reqs:
        return {
            "success": True,
            "data": {
                "ats_score": 0,
                "no_meaningful_keywords": True,
                "target_role": None,
                "matching_skills": [],
                "missing_skills": [],
                "matching_keywords": [],
                "missing_keywords": [],
                "relevant_experience": [],
                "strengths": [],
                "actionable_improvements": [
                    "Paste a job description containing technical requirements, or type a target role (e.g., 'Backend Developer', 'Frontend Engineer', 'Full Stack Developer') to calculate your ATS match."
                ],
                "score_breakdown": {
                    "technical_skills": {"score": 0, "max": 40, "weight": "40%", "label": "Required Technical Skills"},
                    "experience_projects": {"score": 0, "max": 25, "weight": "25%", "label": "Relevant Experience & Projects"},
                    "education": {"score": 0, "max": 15, "weight": "15%", "label": "Education & Qualifications"},
                    "competencies": {"score": 0, "max": 10, "weight": "10%", "label": "Keywords & Competencies"},
                    "completeness_formatting": {"score": 0, "max": 10, "weight": "10%", "label": "Resume Completeness & Formatting"}
                },
                "explanations": [
                    "No specific technical skills or recognized target roles were identified. Tip: Type a role name (like 'Backend Developer' or 'Full Stack Developer') or paste a job posting."
                ],
                "disclaimer": "This score is an indicative simulation based on standard ATS keyword indexing algorithms."
            }
        }

    # 4. Compare both datasets properly
    matched_reqs = []
    missing_reqs = []

    for req in extracted_reqs:
        if check_skill_match_in_text(req, resume_full_text):
            matched_reqs.append(req)
        else:
            missing_reqs.append(req)

    matching_display = [r["canonical"] for r in matched_reqs]
    missing_display = [r["canonical"] for r in missing_reqs]

    total_req_count = len(extracted_reqs)
    matched_count = len(matched_reqs)
    skill_ratio = matched_count / total_req_count if total_req_count > 0 else 0

    # --------------------------------------------------------------------------
    # PILLAR 1: Required Technical Skills (Max 40 points - 40%)
    # --------------------------------------------------------------------------
    base_skill_pts = round(skill_ratio * 32)
    matched_in_skills_section = [r for r in matched_reqs if check_skill_match_in_text(r, resume_skills_text)]
    skills_section_bonus = round((len(matched_in_skills_section) / max(1, matched_count)) * 8) if matched_count > 0 else 0
    pillar_skills = min(40, base_skill_pts + skills_section_bonus)

    # --------------------------------------------------------------------------
    # PILLAR 2: Relevant Experience and Projects (Max 25 points - 25%)
    # --------------------------------------------------------------------------
    matched_in_exp_proj = [r for r in matched_reqs if check_skill_match_in_text(r, resume_exp_proj_text)]
    exp_tech_ratio = len(matched_in_exp_proj) / max(1, total_req_count)
    exp_tech_pts = round(exp_tech_ratio * 14)

    action_verbs = ['architected', 'engineered', 'developed', 'implemented', 'designed', 'optimized', 'spearheaded', 'built', 'reduced', 'increased', 'scaled', 'automated', 'streamlined', 'deployed']
    verbs_found = [v for v in action_verbs if v in resume_exp_proj_text]
    action_verb_pts = 5 if len(verbs_found) >= 2 else (3 if len(verbs_found) == 1 else 0)

    has_metrics = bool(re.search(r'\d+%|\d+\s*(?:ms|k|m|users|requests|queries|tps|reduction|growth)', resume_exp_proj_text))
    metrics_pts = 4 if has_metrics else 0

    has_entries = bool((exp and len(exp) > 0) or (proj and len(proj) > 0))
    entry_presence_pts = 2 if has_entries else 0

    pillar_exp = min(25, exp_tech_pts + action_verb_pts + metrics_pts + entry_presence_pts)

    # --------------------------------------------------------------------------
    # PILLAR 3: Education and Qualifications (Max 15 points - 15%)
    # --------------------------------------------------------------------------
    edu_text = ' '.join([f"{e.get('degree', '')} {e.get('specialization', '')} {e.get('institution', '')}" for e in edu if isinstance(e, dict)]).lower()
    edu_degree_pts = 0
    if any(deg in edu_text for deg in ['b.tech', 'b.e.', 'bachelor', 'b.s.', 'm.tech', 'master', 'm.s.', 'computer science', 'information technology', 'software engineering', 'mca', 'bca']):
        edu_degree_pts = 11
    elif edu:
        edu_degree_pts = 7

    has_grade = any('cgpa' in str(e.get('grade', '')).lower() or re.search(r'\d', str(e.get('grade', ''))) for e in edu if isinstance(e, dict))
    edu_grade_pts = 4 if has_grade else (2 if edu else 0)
    pillar_edu = min(15, edu_degree_pts + edu_grade_pts)

    # --------------------------------------------------------------------------
    # PILLAR 4: Relevant Keywords and Competencies (Max 10 points - 10%)
    # --------------------------------------------------------------------------
    user_title = str(p.get('professionalTitle', '')).lower()
    user_summary = str(p.get('summary', '')).lower()
    role_terms = ['developer', 'engineer', 'architect', 'programmer', 'full stack', 'frontend', 'backend', 'data', 'cloud']
    title_align_pts = 4 if any(r in user_title or r in user_summary for r in role_terms) else 1

    competencies = ['agile', 'scrum', 'git', 'collaboration', 'problem solving', 'teamwork', 'communication', 'code review', 'ci/cd', 'rest']
    comp_matches = [c for c in competencies if c in resume_full_text]
    comp_pts = 3 if len(comp_matches) >= 2 else (2 if len(comp_matches) == 1 else 0)

    has_cert_ach = bool((cert and len(cert) > 0) or (ach and len(ach) > 0))
    cert_pts = 3 if has_cert_ach else 0
    pillar_competencies = min(10, title_align_pts + comp_pts + cert_pts)

    # --------------------------------------------------------------------------
    # PILLAR 5: Resume Completeness and Formatting (Max 10 points - 10%)
    # --------------------------------------------------------------------------
    comp_score = 0
    if p.get('fullName') and p.get('professionalTitle'): comp_score += 2
    if p.get('email') and p.get('phone'): comp_score += 2
    if p.get('summary', '').strip(): comp_score += 2
    if p.get('linkedin') or p.get('github') or p.get('portfolio'): comp_score += 2
    if has_entries: comp_score += 2
    pillar_completeness = min(10, comp_score)

    total_ats_score = max(0, min(100, pillar_skills + pillar_exp + pillar_edu + pillar_competencies + pillar_completeness))

    # Relevant Experience highlights
    relevant_experience = []
    if matched_in_exp_proj:
        relevant_experience.append(
            f"Demonstrated practical application of {', '.join([r['canonical'] for r in matched_in_exp_proj[:4]])} across project or work experience."
        )
    if has_metrics:
        relevant_experience.append("Project descriptions incorporate quantified impact metrics and measurable scale.")
    if verbs_found:
        relevant_experience.append(f"Strong engineering action verbs utilized ({', '.join(verbs_found[:3])}).")
    if not relevant_experience:
        relevant_experience.append("Consider integrating required technologies directly into project bullet descriptions to raise project relevance.")

    # Strengths
    strengths = []
    if matched_count >= 3:
        strengths.append(f"Strong core tech stack alignment: successfully matched {matched_count} primary requirements ({', '.join(matching_display[:4])}).")
    if pillar_skills >= 25:
        strengths.append("Technical skills section directly reflects critical competencies demanded by the job posting.")
    if pillar_edu >= 12:
        strengths.append("Academic background closely aligns with computer science and engineering qualifications.")
    if pillar_completeness >= 8:
        strengths.append("High profile completeness with contact info, professional links, and structured sections.")
    if not strengths:
        strengths.append("Foundational resume structure is ready for skill enhancement and keyword tuning.")

    # Actionable Improvements
    actionable_improvements = []
    if missing_reqs:
        top_missing = missing_display[:5]
        actionable_improvements.append(
            f"Incorporate missing target technologies into your skills and project descriptions: {', '.join(top_missing)}."
        )
    if not has_metrics:
        actionable_improvements.append(
            "Quantify your project and work impact with specific metrics (e.g. 'reduced latency by 35%', 'handled 5,000 requests')."
        )
    if not verbs_found:
        actionable_improvements.append(
            "Start project bullet points with active engineering verbs (e.g., Architected, Engineered, Implemented, Deployed)."
        )
    if not p.get('summary'):
        actionable_improvements.append(
            "Add a concise 3-4 sentence professional summary tailored to this position."
        )

    # Itemized Explanations for Awarded & Deducted Points
    explanations = []
    if detected_role:
        explanations.append(f"Target Role Profile ({detected_role}): Evaluated against industry-standard requirements for {detected_role} positions.")

    explanations.extend([
        f"Required Technical Skills ({pillar_skills}/40 pts - 40%): Matched {matched_count} of {total_req_count} technical requirements ({', '.join(matching_display) if matching_display else 'None'})." +
        (f" Deducted {40 - pillar_skills} pts for missing competencies: {', '.join(missing_display[:4])}." if missing_display else ""),
        f"Relevant Experience & Projects ({pillar_exp}/25 pts - 25%): {len(matched_in_exp_proj)} target skills substantiated in project/experience descriptions." +
        (" Validated action verbs and metrics." if has_metrics else " Add quantifiable metrics to gain up to 4 more points."),
        f"Education & Qualifications ({pillar_edu}/15 pts - 15%): Academic credentials evaluated against technical degree criteria.",
        f"Keywords & Competencies ({pillar_competencies}/10 pts - 10%): Professional title alignment, soft skills, and engineering practices.",
        f"Resume Completeness & Formatting ({pillar_completeness}/10 pts - 10%): ATS layout, essential contact info, and section completeness."
    ])

    return {
        "success": True,
        "data": {
            "ats_score": total_ats_score,
            "target_role": detected_role,
            "matching_skills": matching_display,
            "missing_skills": missing_display,
            "matching_keywords": matching_display,  # For backwards compatibility
            "missing_keywords": missing_display,   # For backwards compatibility
            "relevant_experience": relevant_experience,
            "strengths": strengths,
            "actionable_improvements": actionable_improvements,
            "score_breakdown": {
                "technical_skills": {
                    "score": pillar_skills,
                    "max": 40,
                    "weight": "40%",
                    "label": "Required Technical Skills"
                },
                "experience_projects": {
                    "score": pillar_exp,
                    "max": 25,
                    "weight": "25%",
                    "label": "Relevant Experience & Projects"
                },
                "education": {
                    "score": pillar_edu,
                    "max": 15,
                    "weight": "15%",
                    "label": "Education & Qualifications"
                },
                "competencies": {
                    "score": pillar_competencies,
                    "max": 10,
                    "weight": "10%",
                    "label": "Keywords & Competencies"
                },
                "completeness_formatting": {
                    "score": pillar_completeness,
                    "max": 10,
                    "weight": "10%",
                    "label": "Resume Completeness & Formatting"
                }
            },
            "explanations": explanations,
            "is_indicative": True,
            "disclaimer": "This score is an indicative simulation based on standard ATS keyword indexing algorithms and does not guarantee results with any proprietary ATS system."
        }
    }


def analyze_ats(
    resume_data: Any,
    job_description: str
) -> Dict[str, Any]:
    """
    Evaluates the resume against a target job description dynamically.
    Combines deterministic algorithmic ATS parsing with optional AI qualitative advice.
    Never returns a hardcoded score like 42 or 32.
    """
    if not job_description or not str(job_description).strip():
        return {
            "success": False,
            "message": "Job description is required for ATS analysis. Please paste a target job posting."
        }

    # 1. Deterministic algorithmic ATS scoring
    base_eval = calculate_dynamic_ats_score(resume_data, job_description)
    if not base_eval.get("success"):
        return base_eval

    # If no meaningful keywords found, return base result directly
    if base_eval.get("data", {}).get("no_meaningful_keywords"):
        return base_eval

    # 2. Optional AI qualitative augmentation if Gemini API is available
    client, configured_model, is_configured = get_client()
    if is_configured:
        try:
            resume_summary = json.dumps(resume_data)[:2500] if isinstance(resume_data, (dict, list)) else str(resume_data)[:2500]
            system_instruction = (
                "You are an expert technical recruiter and ATS specialist. "
                "Review the candidate's ATS match details and provide 2-3 concise, high-value actionable improvement tips. "
                "Return ONLY a JSON object: {\"actionable_improvements\": [\"tip1\", \"tip2\"], \"strengths\": [\"str1\"]}"
            )
            prompt = (
                f"TARGET JOB POSTING:\n{str(job_description)[:1500]}\n\n"
                f"MATCHED KEYWORDS: {base_eval['data']['matching_skills']}\n"
                f"MISSING KEYWORDS: {base_eval['data']['missing_skills']}\n"
                f"CANDIDATE RESUME SUMMARY:\n{resume_summary}\n\n"
                f"Provide tailored suggestions to boost their ATS compatibility."
            )
            ai_res = execute_gemini_prompt(prompt, system_instruction=system_instruction, json_mode=True, max_output_tokens=600)
            if ai_res.get("success") and ai_res.get("text"):
                cleaned = clean_markdown_fences(ai_res["text"])
                parsed = json.loads(cleaned)
                if parsed.get("actionable_improvements"):
                    base_eval["data"]["actionable_improvements"] = parsed["actionable_improvements"] + [
                        tip for tip in base_eval["data"]["actionable_improvements"] if tip not in parsed["actionable_improvements"]
                    ]
                if parsed.get("strengths"):
                    base_eval["data"]["strengths"] = parsed["strengths"] + [
                        s for s in base_eval["data"]["strengths"] if s not in parsed["strengths"]
                    ]
                base_eval["model"] = ai_res.get("model")
        except Exception as exc:
            logger.info(f"Gemini ATS qualitative enhancement skipped: {exc}")

    return base_eval


# ==============================================================================
# FEATURE 6: AI JOB DESCRIPTION MATCHER
# ==============================================================================
def match_job_description(
    resume_data: Any,
    job_description: str
) -> Dict[str, Any]:
    """
    Compares the user's resume against a job description, identifying alignment,
    highlighting relevant projects, and recommending targeted tweaks.
    """
    if not job_description or not str(job_description).strip():
        return {
            "success": False,
            "message": "Job description is required for matching. Please paste a target job posting."
        }

    # Deterministic base matching
    base_eval = calculate_dynamic_ats_score(resume_data, job_description)
    if not base_eval.get("success"):
        return base_eval

    matching_skills = base_eval.get("data", {}).get("matching_skills", [])
    missing_skills = base_eval.get("data", {}).get("missing_skills", [])
    match_percentage = base_eval.get("data", {}).get("ats_score", 50)

    result_data = {
        "match_percentage": match_percentage,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "relevant_project_recommendations": [
            f"Highlight projects demonstrating hands-on experience with {', '.join(matching_skills[:3]) if matching_skills else 'core full-stack skills'}."
        ],
        "keyword_integration_tips": [
            f"Integrate missing target keywords into your bullet points: {', '.join(missing_skills[:4]) if missing_skills else 'key performance metrics'}."
        ]
    }

    # Optional AI enhancement
    client, configured_model, is_configured = get_client()
    if is_configured:
        try:
            resume_str = json.dumps(resume_data)[:3000] if isinstance(resume_data, (dict, list)) else str(resume_data)[:3000]
            system_instruction = (
                "You are an executive talent recruiter. Compare the candidate's resume with the job description. "
                "Provide targeted recommendations on which candidate projects to elevate and specific keyword integration tips. "
                "Return ONLY a valid JSON object matching: "
                "{"
                "  \"relevant_project_recommendations\": [\"rec1\"],"
                "  \"keyword_integration_tips\": [\"tip1\"]"
                "}"
            )
            prompt = (
                f"JOB DESCRIPTION:\n{job_description[:1500]}\n\n"
                f"RESUME DATA:\n{resume_str}\n\n"
                f"MATCHED: {matching_skills}\nMISSING: {missing_skills}"
            )
            ai_res = execute_gemini_prompt(prompt, system_instruction=system_instruction, json_mode=True, max_output_tokens=600)
            if ai_res.get("success") and ai_res.get("text"):
                cleaned = clean_markdown_fences(ai_res["text"])
                parsed = json.loads(cleaned)
                if parsed.get("relevant_project_recommendations"):
                    result_data["relevant_project_recommendations"] = parsed["relevant_project_recommendations"]
                if parsed.get("keyword_integration_tips"):
                    result_data["keyword_integration_tips"] = parsed["keyword_integration_tips"]
        except Exception as exc:
            logger.info(f"Gemini job match enhancement skipped: {exc}")

    return {
        "success": True,
        "data": result_data
    }


# ==============================================================================
# FEATURE 7: AI CAREER OBJECTIVE GENERATOR
# ==============================================================================
def generate_career_objective(
    education: str,
    skills: str,
    career_interest: str,
    experience_level: str = "Fresher"
) -> Dict[str, Any]:
    """
    Generates a tailored career objective specifically calibrated for:
    - Student (internships, academic focus)
    - Fresher (entry-level, enthusiasm, fast learner, foundational skills)
    - Experienced Professional (value delivery, scaling, team collaboration)
    """
    system_instruction = (
        "You are an expert career consultant. "
        "Craft 3 high-impact career objective statements tailored specifically for the candidate's experience level: "
        "Student, Fresher, or Experienced Professional. "
        "Rules: Strictly avoid empty buzzwords ('hardworking', 'go-getter'). "
        "Focus on what value they bring, their real skills, and how they aim to contribute to team objectives. "
        "Return the options clearly labeled: Option 1 (Direct & Technical), Option 2 (Impact & Growth), Option 3 (Collaborative)."
    )

    prompt = (
        f"Experience Level: {experience_level}\n"
        f"Education: {education or 'B.Tech in Computer Science and Engineering'}\n"
        f"Key Skills: {skills or 'Python, JavaScript, Web Development, Databases'}\n"
        f"Target Career Interest: {career_interest or 'Software Development Engineer'}\n\n"
        f"Generate 3 distinct career objective options."
    )

    result = execute_gemini_prompt(prompt, system_instruction=system_instruction)

    if not result["success"]:
        return {
            "success": False,
            "message": result.get("message", "Failed to generate career objectives.")
        }

    return {
        "success": True,
        "objectives": result["text"].strip(),
        "model": result.get("model")
    }


# ==============================================================================
# FEATURE 8: AI RESUME REVIEW
# ==============================================================================
def review_resume(resume_data: Any) -> Dict[str, Any]:
    """
    Performs an end-to-end audit of the resume:
    - Tone, grammar, and clarity
    - Section organization and completeness
    - Repetitive phrases or weak verbs
    - Recommendations for immediate elevation
    """
    resume_str = json.dumps(resume_data) if isinstance(resume_data, (dict, list)) else str(resume_data)

    system_instruction = (
        "You are a senior tech recruiter and resume auditor. "
        "Perform a comprehensive review of this resume. "
        "Evaluate: Clarity, Professional Tone, Impact, Section Balance, and Redundancy. "
        "Return ONLY a valid JSON object matching: "
        "{"
        "  \"overall_verdict\": \"Strong foundations with high technical relevance.\","
        "  \"strengths\": [\"Strength 1\", \"Strength 2\"],"
        "  \"areas_to_improve\": [\"Area 1\", \"Area 2\"],"
        "  \"grammar_and_tone\": \"Excellent tone; avoid repetitive starting verbs like 'Worked on'.\","
        "  \"section_by_section_feedback\": {"
        "    \"summary\": \"Concise and focused.\","
        "    \"experience_and_projects\": \"Ensure every project includes a live link or repo.\","
        "    \"skills\": \"Well grouped by category.\""
        "  },"
        "  \"quick_wins\": ["
        "    \"Add GitHub/Live links for all technical projects.\","
        "    \"Ensure CGPA and graduation year are explicitly stated.\""
        "  ]"
        "}"
    )

    prompt = f"RESUME FOR AUDIT:\n{resume_str[:4000]}"

    result = execute_gemini_prompt(
        prompt,
        system_instruction=system_instruction,
        json_mode=True
    )

    if not result["success"]:
        return {
            "success": False,
            "message": result.get("message", "Failed to audit resume.")
        }

    try:
        cleaned = clean_markdown_fences(result["text"])
        parsed = json.loads(cleaned)
        return {
            "success": True,
            "data": parsed,
            "model": result.get("model")
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"Failed to parse resume audit from Gemini response: {exc}"
        }
