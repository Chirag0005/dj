/**
 * static/js/editor.js
 * ResumeCraft AI - Live Editor & Gemini AI Controller
 *
 * Implements real-time two-way synchronization, dynamic repeaters,
 * A4 live preview rendering, template switching, and Gemini AI integrations.
 */

let currentResume = null;
let saveTimeout = null;

// ==============================================================================
// CSRF TOKEN HELPER
// ==============================================================================
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ==============================================================================
// INITIALIZATION
// ==============================================================================
document.addEventListener('DOMContentLoaded', async () => {
    // Determine active resume ID from URL or localStorage
    const urlParams = new URLSearchParams(window.location.search);
    let resumeId = urlParams.get('id');
    const initialTemplate = urlParams.get('template');

    if (resumeId) {
        currentResume = ResumeStorage.get(resumeId);
    }

    if (!currentResume) {
        currentResume = ResumeStorage.getActive();
    }

    if (!currentResume) {
        // If no resumes exist in storage yet, seed initial default CSE demo resume
        await ResumeStorage.initDefaultIfEmpty();
        currentResume = ResumeStorage.getActive();
    }

    if (!currentResume) {
        // If still empty, create fresh empty resume
        currentResume = ResumeStorage.createEmpty(initialTemplate || 'classic');
        ResumeStorage.save(currentResume);
    }

    if (initialTemplate && currentResume) {
        currentResume.template = initialTemplate;
    }

    const backBtn = document.getElementById('btnBackToEditor');
    if (backBtn && currentResume && currentResume.id) {
        backBtn.href = '/edit/?id=' + encodeURIComponent(currentResume.id);
    }

    // Populate form fields
    populateFormFromResume();

    // Render live preview
    renderLivePreview();

    // Setup input listeners for real-time reactivity
    attachInputListeners();

    // Setup UI controls
    setupTemplateSelector();
    setupCustomizationControls();
    setupMobileTabs();
    setupAiModals();

    // Set initial completion badge
    updateCompletionBadge();
});

// ==============================================================================
// FORM POPULATION & TWO-WAY BINDING
// ==============================================================================
function populateFormFromResume() {
    if (!currentResume) return;

    // Header & Title
    const titleInput = document.getElementById('resumeTitleInput');
    if (titleInput) titleInput.value = currentResume.title || 'Untitled Resume';

    // Personal details
    const p = currentResume.personal || {};
    setVal('inputFullName', p.fullName);
    setVal('inputTitle', p.professionalTitle);
    setVal('inputEmail', p.email);
    setVal('inputPhone', p.phone);
    setVal('inputLocation', p.location);
    setVal('inputLinkedin', p.linkedin);
    setVal('inputGithub', p.github);
    setVal('inputPortfolio', p.portfolio);
    setVal('inputSummary', p.summary);

    // Skills
    const s = currentResume.skills || {};
    setVal('inputSkillsLanguages', s.languages);
    setVal('inputSkillsFrameworks', s.frameworks);
    setVal('inputSkillsTools', s.tools);
    setVal('inputSkillsTechnical', s.technical);
    setVal('inputSkillsSoft', s.soft);

    // Dynamic repeaters
    renderEducationList();
    renderExperienceList();
    renderProjectsList();
    renderCertificationsList();
    renderAchievementsList();

    // Customization controls
    const c = currentResume.customization || {};
    if (c.accentColor) applyAccentColor(c.accentColor);
    if (c.fontFamily) setVal('selectFontFamily', c.fontFamily);
    if (c.fontSize) setVal('selectFontSize', c.fontSize);
    if (c.spacing) setVal('selectSpacing', c.spacing);

    // Template selector
    const tmplSelect = document.getElementById('selectTemplate');
    if (tmplSelect && currentResume.template) {
        tmplSelect.value = currentResume.template;
    }
}

function setVal(id, val) {
    const el = document.getElementById(id);
    if (el) el.value = val || '';
}

function getVal(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
}

function attachInputListeners() {
    const formContainer = document.getElementById('editorFormContainer');
    if (!formContainer) return;

    formContainer.addEventListener('input', (e) => {
        syncFormToResumeObject();
        renderLivePreview();
        triggerAutosave();
    });

    const titleInput = document.getElementById('resumeTitleInput');
    if (titleInput) {
        titleInput.addEventListener('input', () => {
            currentResume.title = titleInput.value;
            triggerAutosave();
        });
    }
}

function syncFormToResumeObject() {
    if (!currentResume) return;

    currentResume.personal = {
        fullName: getVal('inputFullName'),
        professionalTitle: getVal('inputTitle'),
        email: getVal('inputEmail'),
        phone: getVal('inputPhone'),
        location: getVal('inputLocation'),
        linkedin: getVal('inputLinkedin'),
        github: getVal('inputGithub'),
        portfolio: getVal('inputPortfolio'),
        summary: getVal('inputSummary')
    };

    currentResume.skills = {
        languages: getVal('inputSkillsLanguages'),
        frameworks: getVal('inputSkillsFrameworks'),
        tools: getVal('inputSkillsTools'),
        technical: getVal('inputSkillsTechnical'),
        soft: getVal('inputSkillsSoft')
    };
}

// ==============================================================================
// AUTOSAVE LOGIC
// ==============================================================================
function triggerAutosave() {
    const statusPill = document.getElementById('autosaveStatus');
    if (statusPill) {
        statusPill.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> Saving...';
        statusPill.className = 'save-status-pill saving';
    }

    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
        try {
            ResumeStorage.save(currentResume);
            if (statusPill) {
                statusPill.innerHTML = '<i class="bi bi-check2-circle"></i> All changes saved';
                statusPill.className = 'save-status-pill saved';
            }
            updateCompletionBadge();
        } catch (e) {
            if (statusPill) {
                statusPill.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Storage error';
                statusPill.className = 'save-status-pill text-danger';
            }
        }
    }, 350);
}

function updateCompletionBadge() {
    const badge = document.getElementById('completionBadge');
    if (!badge || !currentResume) return;
    const score = ResumeStorage.calculateCompletion(currentResume);
    badge.textContent = `${score}% Complete`;
    badge.className = score >= 80 ? 'badge bg-success' : (score >= 50 ? 'badge bg-primary' : 'badge bg-warning text-dark');
}

// ==============================================================================
// DYNAMIC REPEATERS (EDUCATION, EXPERIENCE, PROJECTS, ETC.)
// ==============================================================================

// 1. EDUCATION
function renderEducationList() {
    const container = document.getElementById('educationRepeaterList');
    if (!container) return;
    container.innerHTML = '';

    const list = currentResume.education || [];
    list.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'repeater-card';
        card.innerHTML = `
            <div class="repeater-actions">
                <button type="button" class="btn-icon" onclick="deleteEducation(${index})" title="Remove"><i class="bi bi-trash3"></i></button>
            </div>
            <div class="row g-2">
                <div class="col-md-7">
                    <label class="form-label">College / University</label>
                    <input type="text" class="form-control form-control-sm" value="${escapeHtml(item.institution || '')}" oninput="updateEducation(${index}, 'institution', this.value)">
                </div>
                <div class="col-md-5">
                    <label class="form-label">Degree</label>
                    <input type="text" class="form-control form-control-sm" placeholder="e.g. B.Tech" value="${escapeHtml(item.degree || '')}" oninput="updateEducation(${index}, 'degree', this.value)">
                </div>
                <div class="col-md-5">
                    <label class="form-label">Specialization / Stream</label>
                    <input type="text" class="form-control form-control-sm" placeholder="e.g. Computer Science" value="${escapeHtml(item.specialization || '')}" oninput="updateEducation(${index}, 'specialization', this.value)">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Year Duration</label>
                    <input type="text" class="form-control form-control-sm" placeholder="2022 – 2026" value="${escapeHtml(item.startYear ? `${item.startYear} – ${item.endYear || 'Present'}` : (item.duration || ''))}" oninput="updateEducation(${index}, 'duration', this.value)">
                </div>
                <div class="col-md-3">
                    <label class="form-label">CGPA / %</label>
                    <input type="text" class="form-control form-control-sm" placeholder="e.g. 8.9 CGPA" value="${escapeHtml(item.grade || '')}" oninput="updateEducation(${index}, 'grade', this.value)">
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

window.addEducation = function() {
    if (!currentResume.education) currentResume.education = [];
    currentResume.education.push({
        id: 'edu_' + Date.now(),
        institution: '',
        degree: '',
        specialization: '',
        duration: '',
        grade: ''
    });
    renderEducationList();
    renderLivePreview();
    triggerAutosave();
};

window.updateEducation = function(index, field, value) {
    if (currentResume.education && currentResume.education[index]) {
        currentResume.education[index][field] = value;
        renderLivePreview();
        triggerAutosave();
    }
};

window.deleteEducation = function(index) {
    if (currentResume.education) {
        currentResume.education.splice(index, 1);
        renderEducationList();
        renderLivePreview();
        triggerAutosave();
    }
};

// 2. EXPERIENCE
function renderExperienceList() {
    const container = document.getElementById('experienceRepeaterList');
    if (!container) return;
    container.innerHTML = '';

    const list = currentResume.experience || [];
    list.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'repeater-card';
        card.innerHTML = `
            <div class="repeater-actions">
                <button type="button" class="btn-icon" onclick="deleteExperience(${index})" title="Remove"><i class="bi bi-trash3"></i></button>
            </div>
            <div class="row g-2 mb-2">
                <div class="col-md-6">
                    <label class="form-label">Company / Organization</label>
                    <input type="text" class="form-control form-control-sm" value="${escapeHtml(item.company || '')}" oninput="updateExperience(${index}, 'company', this.value)">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Job Title / Role</label>
                    <input type="text" class="form-control form-control-sm" value="${escapeHtml(item.role || '')}" oninput="updateExperience(${index}, 'role', this.value)">
                </div>
                <div class="col-md-12">
                    <label class="form-label">Duration</label>
                    <input type="text" class="form-control form-control-sm" placeholder="e.g. May 2025 – July 2025" value="${escapeHtml(item.duration || '')}" oninput="updateExperience(${index}, 'duration', this.value)">
                </div>
            </div>
            <div class="d-flex justify-content-between align-items-center mb-1">
                <label class="form-label mb-0">Responsibilities & Impact</label>
                <button type="button" class="btn-ai-inline" onclick="openInlineAiExperienceModal(${index})">
                    <i class="bi bi-stars"></i> ✨ AI Improve
                </button>
            </div>
            <textarea class="form-control form-control-sm" rows="3" placeholder="• Architected feature X using Y resulting in Z..." oninput="updateExperience(${index}, 'description', this.value)">${escapeHtml(item.description || '')}</textarea>
        `;
        container.appendChild(card);
    });
}

window.addExperience = function() {
    if (!currentResume.experience) currentResume.experience = [];
    currentResume.experience.push({
        id: 'exp_' + Date.now(),
        company: '',
        role: '',
        duration: '',
        description: ''
    });
    renderExperienceList();
    renderLivePreview();
    triggerAutosave();
};

window.updateExperience = function(index, field, value) {
    if (currentResume.experience && currentResume.experience[index]) {
        currentResume.experience[index][field] = value;
        renderLivePreview();
        triggerAutosave();
    }
};

window.deleteExperience = function(index) {
    if (currentResume.experience) {
        currentResume.experience.splice(index, 1);
        renderExperienceList();
        renderLivePreview();
        triggerAutosave();
    }
};

// 3. PROJECTS
function renderProjectsList() {
    const container = document.getElementById('projectsRepeaterList');
    if (!container) return;
    container.innerHTML = '';

    const list = currentResume.projects || [];
    list.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'repeater-card';
        card.innerHTML = `
            <div class="repeater-actions">
                <button type="button" class="btn-icon" onclick="deleteProject(${index})" title="Remove"><i class="bi bi-trash3"></i></button>
            </div>
            <div class="row g-2 mb-2">
                <div class="col-md-6">
                    <label class="form-label">Project Name</label>
                    <input type="text" class="form-control form-control-sm" value="${escapeHtml(item.name || '')}" oninput="updateProject(${index}, 'name', this.value)">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Technologies Used</label>
                    <input type="text" class="form-control form-control-sm" placeholder="e.g. Python, Django, React" value="${escapeHtml(item.technologies || '')}" oninput="updateProject(${index}, 'technologies', this.value)">
                </div>
                <div class="col-md-12">
                    <label class="form-label">Live / GitHub URL</label>
                    <input type="url" class="form-control form-control-sm" placeholder="https://github.com/..." value="${escapeHtml(item.url || '')}" oninput="updateProject(${index}, 'url', this.value)">
                </div>
            </div>
            <div class="d-flex justify-content-between align-items-center mb-1">
                <label class="form-label mb-0">Project Description & Bullets</label>
                <button type="button" class="btn-ai-inline" onclick="openInlineAiProjectModal(${index})">
                    <i class="bi bi-stars"></i> ✨ AI Enhance
                </button>
            </div>
            <textarea class="form-control form-control-sm" rows="3" placeholder="• Developed end-to-end web system..." oninput="updateProject(${index}, 'description', this.value)">${escapeHtml(item.description || '')}</textarea>
        `;
        container.appendChild(card);
    });
}

window.addProject = function() {
    if (!currentResume.projects) currentResume.projects = [];
    currentResume.projects.push({
        id: 'proj_' + Date.now(),
        name: '',
        technologies: '',
        url: '',
        description: ''
    });
    renderProjectsList();
    renderLivePreview();
    triggerAutosave();
};

window.updateProject = function(index, field, value) {
    if (currentResume.projects && currentResume.projects[index]) {
        currentResume.projects[index][field] = value;
        renderLivePreview();
        triggerAutosave();
    }
};

window.deleteProject = function(index) {
    if (currentResume.projects) {
        currentResume.projects.splice(index, 1);
        renderProjectsList();
        renderLivePreview();
        triggerAutosave();
    }
};

// 4. CERTIFICATIONS
function renderCertificationsList() {
    const container = document.getElementById('certificationsRepeaterList');
    if (!container) return;
    container.innerHTML = '';

    const list = currentResume.certifications || [];
    list.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'repeater-card';
        card.innerHTML = `
            <div class="repeater-actions">
                <button type="button" class="btn-icon" onclick="deleteCertification(${index})" title="Remove"><i class="bi bi-trash3"></i></button>
            </div>
            <div class="row g-2">
                <div class="col-md-6">
                    <label class="form-label">Certificate Name</label>
                    <input type="text" class="form-control form-control-sm" value="${escapeHtml(item.name || '')}" oninput="updateCertification(${index}, 'name', this.value)">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Issuing Organization</label>
                    <input type="text" class="form-control form-control-sm" placeholder="AWS, Coursera, Meta" value="${escapeHtml(item.organization || '')}" oninput="updateCertification(${index}, 'organization', this.value)">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Year</label>
                    <input type="text" class="form-control form-control-sm" placeholder="2025" value="${escapeHtml(item.year || '')}" oninput="updateCertification(${index}, 'year', this.value)">
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

window.addCertification = function() {
    if (!currentResume.certifications) currentResume.certifications = [];
    currentResume.certifications.push({
        id: 'cert_' + Date.now(),
        name: '',
        organization: '',
        year: ''
    });
    renderCertificationsList();
    renderLivePreview();
    triggerAutosave();
};

window.updateCertification = function(index, field, value) {
    if (currentResume.certifications && currentResume.certifications[index]) {
        currentResume.certifications[index][field] = value;
        renderLivePreview();
        triggerAutosave();
    }
};

window.deleteCertification = function(index) {
    if (currentResume.certifications) {
        currentResume.certifications.splice(index, 1);
        renderCertificationsList();
        renderLivePreview();
        triggerAutosave();
    }
};

// 5. ACHIEVEMENTS
function renderAchievementsList() {
    const container = document.getElementById('achievementsRepeaterList');
    if (!container) return;
    container.innerHTML = '';

    const list = currentResume.achievements || [];
    list.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'repeater-card';
        card.innerHTML = `
            <div class="repeater-actions">
                <button type="button" class="btn-icon" onclick="deleteAchievement(${index})" title="Remove"><i class="bi bi-trash3"></i></button>
            </div>
            <div class="row g-2">
                <div class="col-md-12">
                    <label class="form-label">Achievement / Award Title</label>
                    <input type="text" class="form-control form-control-sm" value="${escapeHtml(item.title || '')}" oninput="updateAchievement(${index}, 'title', this.value)">
                </div>
                <div class="col-md-12">
                    <label class="form-label">Description</label>
                    <textarea class="form-control form-control-sm" rows="2" oninput="updateAchievement(${index}, 'description', this.value)">${escapeHtml(item.description || '')}</textarea>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

window.addAchievement = function() {
    if (!currentResume.achievements) currentResume.achievements = [];
    currentResume.achievements.push({
        id: 'ach_' + Date.now(),
        title: '',
        description: ''
    });
    renderAchievementsList();
    renderLivePreview();
    triggerAutosave();
};

window.updateAchievement = function(index, field, value) {
    if (currentResume.achievements && currentResume.achievements[index]) {
        currentResume.achievements[index][field] = value;
        renderLivePreview();
        triggerAutosave();
    }
};

window.deleteAchievement = function(index) {
    if (currentResume.achievements) {
        currentResume.achievements.splice(index, 1);
        renderAchievementsList();
        renderLivePreview();
        triggerAutosave();
    }
};

// ==============================================================================
// TEMPLATE SELECTION & CUSTOMIZATION
// ==============================================================================
function setupTemplateSelector() {
    const tmplSelect = document.getElementById('selectTemplate');
    if (!tmplSelect) return;

    tmplSelect.addEventListener('change', (e) => {
        const chosen = e.target.value;
        if (currentResume) {
            currentResume.template = chosen;
            renderLivePreview();
            triggerAutosave();
        }
    });
}

function setupCustomizationControls() {
    // Font Family
    const fontSelect = document.getElementById('selectFontFamily');
    if (fontSelect) {
        fontSelect.addEventListener('change', (e) => {
            if (!currentResume.customization) currentResume.customization = {};
            currentResume.customization.fontFamily = e.target.value;
            renderLivePreview();
            triggerAutosave();
        });
    }

    // Font Size
    const sizeSelect = document.getElementById('selectFontSize');
    if (sizeSelect) {
        sizeSelect.addEventListener('change', (e) => {
            if (!currentResume.customization) currentResume.customization = {};
            currentResume.customization.fontSize = e.target.value;
            renderLivePreview();
            triggerAutosave();
        });
    }

    // Spacing
    const spacingSelect = document.getElementById('selectSpacing');
    if (spacingSelect) {
        spacingSelect.addEventListener('change', (e) => {
            if (!currentResume.customization) currentResume.customization = {};
            currentResume.customization.spacing = e.target.value;
            renderLivePreview();
            triggerAutosave();
        });
    }

    // Color Swatches
    const swatches = document.querySelectorAll('.color-swatch');
    swatches.forEach(swatch => {
        swatch.addEventListener('click', () => {
            const color = swatch.getAttribute('data-color');
            applyAccentColor(color);
        });
    });

    const customColorInput = document.getElementById('customColorPicker');
    if (customColorInput) {
        customColorInput.addEventListener('input', (e) => {
            applyAccentColor(e.target.value);
        });
    }
}

function applyAccentColor(color) {
    if (!color) return;
    if (!currentResume.customization) currentResume.customization = {};
    currentResume.customization.accentColor = color;

    document.querySelectorAll('.color-swatch').forEach(s => {
        s.classList.toggle('active', s.getAttribute('data-color') === color);
    });

    const sheet = document.getElementById('resumeSheet');
    if (sheet) {
        sheet.style.setProperty('--resume-accent', color);
    }
    triggerAutosave();
}

function setupMobileTabs() {
    const tabEditor = document.getElementById('tabBtnEditor');
    const tabPreview = document.getElementById('tabBtnPreview');
    const colEditor = document.getElementById('editorColumn');
    const colPreview = document.getElementById('previewColumn');

    if (!tabEditor || !tabPreview || !colEditor || !colPreview) return;

    tabEditor.addEventListener('click', () => {
        tabEditor.classList.add('active');
        tabPreview.classList.remove('active');
        colEditor.classList.remove('d-none');
        colPreview.classList.add('d-none');
    });

    tabPreview.addEventListener('click', () => {
        tabPreview.classList.add('active');
        tabEditor.classList.remove('active');
        colEditor.classList.add('d-none');
        colPreview.classList.remove('d-none');
    });
}

// ==============================================================================
// LIVE RESUME PREVIEW RENDERING (A4 SHEET)
// ==============================================================================
function renderLivePreview() {
    const sheet = document.getElementById('resumeSheet') || document.getElementById('standalonePreviewSheet');
    if (!sheet || !currentResume) return;

    const t = currentResume.template || 'classic';
    const c = currentResume.customization || {};

    // Update Sheet Classes
    sheet.className = `resume-sheet template-${t} fs-${c.fontSize || 'normal'} spacing-${c.spacing || 'normal'}`;
    sheet.style.setProperty('--resume-accent', c.accentColor || '#6257E8');
    sheet.style.setProperty('--resume-font', getFontFamilyValue(c.fontFamily || 'Inter'));

    // Prepare Sections
    const p = currentResume.personal || {};
    const hasPersonal = p.fullName || p.professionalTitle || p.email || p.phone;

    let html = '';

    // HEADER
    if (hasPersonal) {
        html += renderPreviewHeader(t, p);
    }

    // SUMMARY
    if (p.summary && p.summary.trim()) {
        html += `
            <div class="resume-section">
                <div class="resume-section-title">Professional Summary</div>
                <div class="resume-summary-text">${formatSummaryHtml(p.summary)}</div>
            </div>
        `;
    }

    // Freshers place Education first, Classic/Dev place Experience first if present
    if (t === 'fresher') {
        html += renderPreviewEducation(currentResume.education);
        html += renderPreviewSkills(currentResume.skills, t);
        html += renderPreviewProjects(currentResume.projects, t);
        html += renderPreviewExperience(currentResume.experience);
    } else {
        html += renderPreviewExperience(currentResume.experience);
        html += renderPreviewProjects(currentResume.projects, t);
        html += renderPreviewEducation(currentResume.education);
        html += renderPreviewSkills(currentResume.skills, t);
    }

    // CERTIFICATIONS
    html += renderPreviewCertifications(currentResume.certifications);

    // ACHIEVEMENTS
    html += renderPreviewAchievements(currentResume.achievements);

    sheet.innerHTML = html;
}

function renderPreviewHeader(template, p) {
    const contactItems = [];
    if (p.email) contactItems.push(`<i class="bi bi-envelope"></i> <a href="mailto:${escapeHtml(p.email)}">${escapeHtml(p.email)}</a>`);
    if (p.phone) contactItems.push(`<i class="bi bi-telephone"></i> ${escapeHtml(p.phone)}`);
    if (p.location) contactItems.push(`<i class="bi bi-geo-alt"></i> ${escapeHtml(p.location)}`);
    if (p.linkedin) contactItems.push(`<i class="bi bi-linkedin"></i> <a href="${escapeHtml(p.linkedin)}" target="_blank">LinkedIn</a>`);
    if (p.github) contactItems.push(`<i class="bi bi-github"></i> <a href="${escapeHtml(p.github)}" target="_blank">GitHub</a>`);
    if (p.portfolio) contactItems.push(`<i class="bi bi-globe"></i> <a href="${escapeHtml(p.portfolio)}" target="_blank">Portfolio</a>`);

    const contactBar = `<div class="resume-contact-bar">${contactItems.join(' • ')}</div>`;

    if (template === 'modern') {
        return `
            <div class="resume-header">
                <div>
                    <div class="resume-name">${escapeHtml(p.fullName || 'Your Name')}</div>
                    <div class="resume-title">${escapeHtml(p.professionalTitle || '')}</div>
                </div>
                ${contactBar}
            </div>
        `;
    }

    return `
        <div class="resume-header">
            <div class="resume-name">${escapeHtml(p.fullName || 'Your Name')}</div>
            <div class="resume-title">${escapeHtml(p.professionalTitle || '')}</div>
            ${contactBar}
        </div>
    `;
}

function renderPreviewEducation(educationList) {
    if (!Array.isArray(educationList) || educationList.length === 0) return '';
    const valid = educationList.filter(e => e.institution || e.degree);
    if (valid.length === 0) return '';

    let out = `
        <div class="resume-section">
            <div class="resume-section-title">Education</div>
    `;

    valid.forEach(e => {
        const degreeLine = [e.degree, e.specialization].filter(Boolean).join(' in ');
        const dur = e.duration || (e.startYear ? `${e.startYear} – ${e.endYear || 'Present'}` : '');
        out += `
            <div class="resume-entry">
                <div class="resume-entry-header">
                    <span>${escapeHtml(e.institution || '')}</span>
                    <span>${escapeHtml(dur)}</span>
                </div>
                <div class="resume-entry-sub">
                    <span>${escapeHtml(degreeLine)}</span>
                    ${e.grade ? `<span class="cgpa-badge">${escapeHtml(e.grade)}</span>` : ''}
                </div>
            </div>
        `;
    });

    out += `</div>`;
    return out;
}

function renderPreviewExperience(experienceList) {
    if (!Array.isArray(experienceList) || experienceList.length === 0) return '';
    const valid = experienceList.filter(e => e.company || e.role);
    if (valid.length === 0) return '';

    let out = `
        <div class="resume-section">
            <div class="resume-section-title">Work Experience</div>
    `;

    valid.forEach(e => {
        out += `
            <div class="resume-entry">
                <div class="resume-entry-header">
                    <span>${escapeHtml(e.company || '')}</span>
                    <span>${escapeHtml(e.duration || '')}</span>
                </div>
                <div class="resume-entry-sub">
                    <span><strong>${escapeHtml(e.role || '')}</strong></span>
                </div>
                ${formatBulletsHtml(e.description)}
            </div>
        `;
    });

    out += `</div>`;
    return out;
}

function renderPreviewProjects(projectsList, template) {
    if (!Array.isArray(projectsList) || projectsList.length === 0) return '';
    const valid = projectsList.filter(p => p.name);
    if (valid.length === 0) return '';

    let out = `
        <div class="resume-section">
            <div class="resume-section-title">Key Projects</div>
    `;

    valid.forEach(p => {
        out += `
            <div class="resume-entry">
                <div class="resume-entry-header">
                    <span>
                        <strong>${escapeHtml(p.name)}</strong>
                        ${p.url ? `<a href="${escapeHtml(p.url)}" target="_blank" class="ms-2 small text-primary"><i class="bi bi-box-arrow-up-right"></i> Link</a>` : ''}
                    </span>
                    ${p.technologies ? `<span class="small ${template === 'developer' ? 'tech-pill' : 'text-muted'}">${escapeHtml(p.technologies)}</span>` : ''}
                </div>
                ${formatBulletsHtml(p.description)}
            </div>
        `;
    });

    out += `</div>`;
    return out;
}

function renderPreviewSkills(skills, template) {
    if (!skills) return '';
    const { languages, frameworks, tools, technical, soft } = skills;
    if (!languages && !frameworks && !tools && !technical && !soft) return '';

    let out = `
        <div class="resume-section">
            <div class="resume-section-title">Technical & Professional Skills</div>
    `;

    const categories = [
        { label: 'Languages', value: languages },
        { label: 'Frameworks & Libraries', value: frameworks },
        { label: 'Developer Tools', value: tools },
        { label: 'Core Technical', value: technical },
        { label: 'Soft Skills', value: soft }
    ];

    categories.forEach(cat => {
        if (cat.value && cat.value.trim()) {
            if (template === 'developer') {
                const pills = cat.value.split(',').map(s => `<span class="skill-tag-pill">${formatSafeInline(escapeHtml(s.trim()))}</span>`).join(' ');
                out += `
                    <div class="mb-1">
                        <strong>${escapeHtml(cat.label)}:</strong> ${pills}
                    </div>
                `;
            } else {
                out += `
                    <div class="mb-1">
                        <strong>${escapeHtml(cat.label)}:</strong> ${formatSafeInline(escapeHtml(cat.value))}
                    </div>
                `;
            }
        }
    });

    out += `</div>`;
    return out;
}

function renderPreviewCertifications(certList) {
    if (!Array.isArray(certList) || certList.length === 0) return '';
    const valid = certList.filter(c => c.name);
    if (valid.length === 0) return '';

    let out = `
        <div class="resume-section">
            <div class="resume-section-title">Certifications</div>
            <ul class="resume-bullet-list">
    `;

    valid.forEach(c => {
        const orgLine = [c.organization, c.year].filter(Boolean).join(' • ');
        out += `<li><strong>${formatSafeInline(escapeHtml(c.name))}</strong>${orgLine ? ` – ${formatSafeInline(escapeHtml(orgLine))}` : ''}</li>`;
    });

    out += `</ul></div>`;
    return out;
}

function renderPreviewAchievements(achList) {
    if (!Array.isArray(achList) || achList.length === 0) return '';
    const valid = achList.filter(a => a.title);
    if (valid.length === 0) return '';

    let out = `
        <div class="resume-section">
            <div class="resume-section-title">Honors & Achievements</div>
            <ul class="resume-bullet-list">
    `;

    valid.forEach(a => {
        out += `<li><strong>${formatSafeInline(escapeHtml(a.title))}</strong>${a.description ? `: ${formatSafeInline(escapeHtml(a.description))}` : ''}</li>`;
    });

    out += `</ul></div>`;
    return out;
}

// ==============================================================================
// SAFE MARKDOWN TO HTML PARSER & SANITIZER
// ==============================================================================

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/**
 * Converts inline Markdown syntax in an already-escaped string into safe HTML.
 * Handles:
 *  - Bold-Italic (***text***, ___text___) -> <strong><em>text</em></strong>
 *  - Bold (**text**, __text__) -> <strong>text</strong>
 *  - Italic (*text*, _text_) -> <em>text</em>
 *  - Inline code (`code`) -> <code class="resume-code">code</code>
 *  - Strips stray or unclosed markdown symbols (**, __, ~~, #)
 */
function formatSafeInline(text) {
    if (!text) return '';
    let s = String(text);

    // 1. Bold-italic: ***text*** or ___text___
    s = s.replace(/\*\*\*([^\*\n]+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    s = s.replace(/___([^_\n]+?)___/g, '<strong><em>$1</em></strong>');

    // 2. Bold: **text** or __text__
    s = s.replace(/\*\*([^\*\n]+?)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/__([^_\n]+?)__/g, '<strong>$1</strong>');

    // 3. Italic: *text* or _text_ (excluding bullets or mid-word underscores)
    s = s.replace(/(^|[^\*])\*([^\*\s\n](?:[^\*\n]*?[^\*\s\n])?)\*(?!\*)/g, '$1<em>$2</em>');
    s = s.replace(/(^|[^_])_([^_\s\n](?:[^_\n]*?[^_\s\n])?)_(?!_)/g, '$1<em>$2</em>');

    // 4. Inline code: `code`
    s = s.replace(/`([^`\n]+)`/g, '<code class="resume-code">$1</code>');

    // 5. Clean any unclosed or stray markdown markers
    s = s.replace(/\*\*|__|~~/g, '');
    s = s.replace(/^#{1,6}\s*/, '');

    return s;
}

/**
 * Shared, robust, and safe Markdown-to-HTML parser for AI and user resume content.
 * Raw HTML is disabled by design via strict escaping before parsing.
 * 
 * Supports:
 * - Asterisk-based (* ), dash-based (- ), plus-based (+ ), Unicode bullet (• ), and numbered lists (1. )
 * - Single and multi-paragraph text
 * - Markdown headings (#, ##, ###) converted into styled bold subheadings
 * - Automatic list grouping (no orphan <ul> tags)
 * - Safe HTML sanitization
 */
function formatSafeMarkdown(rawText, mode = 'auto') {
    if (!rawText || !String(rawText).trim()) return '';

    // Normalize line endings
    const text = String(rawText).replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    const rawLines = text.split('\n');

    // Check if text contains explicit bullet markers
    const hasExplicitBullets = rawLines.some(l => 
        /^(?:[•\u2022]\s*|[\-\*\+]\s+|\d+[\.\)]\s+)/.test(l.trim())
    );

    let html = '';
    let inList = false;

    function closeList() {
        if (inList) {
            html += '</ul>';
            inList = false;
        }
    }

    for (let i = 0; i < rawLines.length; i++) {
        const line = rawLines[i].trim();

        if (!line) {
            closeList();
            continue;
        }

        // Markdown headings: # Heading, ## Heading
        const headingMatch = line.match(/^#{1,6}\s+(.+)$/);
        if (headingMatch) {
            closeList();
            const headingContent = formatSafeInline(escapeHtml(headingMatch[1]));
            html += `<div class="resume-subheading"><strong>${headingContent}</strong></div>`;
            continue;
        }

        // Explicit bullet marker check: * or - or + or • or 1.
        const bulletMatch = line.match(/^(?:[•\u2022]\s*|[\-\*\+]\s+|\d+[\.\)]\s+)(.*)$/);

        let isBullet = false;
        let itemText = line;

        if (bulletMatch) {
            isBullet = true;
            itemText = bulletMatch[1].trim();
        } else if (mode === 'bullets' || (mode === 'auto' && !hasExplicitBullets && rawLines.length > 1 && !text.includes('\n\n'))) {
            // In bullets mode or multi-line single entry without double newlines
            isBullet = true;
            itemText = line.replace(/^[•\u2022]\s*/, '').trim();
        }

        if (isBullet) {
            if (!inList) {
                html += '<ul class="resume-bullet-list">';
                inList = true;
            }
            const formattedItem = formatSafeInline(escapeHtml(itemText));
            if (formattedItem) {
                html += `<li>${formattedItem}</li>`;
            }
        } else {
            closeList();
            const formattedPara = formatSafeInline(escapeHtml(line));
            if (formattedPara) {
                html += `<p class="resume-paragraph mb-2">${formattedPara}</p>`;
            }
        }
    }

    closeList();
    return html;
}

function formatBulletsHtml(text) {
    return formatSafeMarkdown(text, 'bullets');
}

function formatSummaryHtml(text) {
    return formatSafeMarkdown(text, 'summary');
}

function getFontFamilyValue(fontName) {
    switch (fontName) {
        case 'Roboto': return "'Roboto', sans-serif";
        case 'Merriweather': return "'Merriweather', serif";
        case 'Poppins': return "'Plus Jakarta Sans', sans-serif";
        case 'JetBrains Mono': return "'JetBrains Mono', monospace";
        case 'Inter':
        default: return "'Inter', sans-serif";
    }
}

// ==============================================================================
// GEMINI AI INTEGRATION (ALL 8 FEATURES)
// ==============================================================================

async function postAi(url, payload) {
    const csrfToken = getCookie('csrftoken');
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(payload)
    });
    return await response.json();
}

function setupAiModals() {
    // Top AI Assistant Shortcut button
    const openAiBtn = document.getElementById('btnOpenAiAssistant');
    if (openAiBtn) {
        openAiBtn.addEventListener('click', () => {
            const modalEl = document.getElementById('aiAssistantModal');
            if (modalEl) {
                const modal = new bootstrap.Modal(modalEl);
                modal.show();
            }
        });
    }

    // Setup direct Summary button in the form
    const formSummaryBtn = document.getElementById('btnFormAiSummary');
    if (formSummaryBtn) {
        formSummaryBtn.addEventListener('click', () => {
            openAiTab('summary');
            triggerSummaryGeneration();
        });
    }

    // Setup direct Skills button in the form
    const formSkillsBtn = document.getElementById('btnFormAiSkills');
    if (formSkillsBtn) {
        formSkillsBtn.addEventListener('click', () => {
            openAiTab('skills');
            triggerSkillsSuggestion();
        });
    }
}

window.openAiTab = function(tabName) {
    const modalEl = document.getElementById('aiAssistantModal');
    if (modalEl) {
        const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
        modal.show();
    }
    // Switch active tab
    const tabBtns = document.querySelectorAll('.ai-tab-btn');
    tabBtns.forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-tab') === tabName);
    });

    const panes = document.querySelectorAll('.ai-tab-pane');
    panes.forEach(pane => {
        pane.classList.toggle('d-none', pane.getAttribute('id') !== `aiTab_${tabName}`);
    });
};

// FEATURE 1: SUMMARY GENERATOR
window.triggerSummaryGeneration = async function() {
    const targetEl = document.getElementById('aiSummaryResult');
    const btn = document.getElementById('btnRunAiSummary');
    if (btn) btn.disabled = true;
    if (targetEl) targetEl.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div><div class="mt-2 text-muted">Gemini is crafting your professional summary...</div></div>';

    const p = currentResume.personal || {};
    const s = currentResume.skills || {};
    const edu = (currentResume.education || []).map(e => `${e.degree || ''} at ${e.institution || ''}`).join(', ');
    const allSkills = [s.languages, s.frameworks, s.technical].filter(Boolean).join(', ');

    try {
        const res = await postAi('/ai/generate-summary/', {
            education: edu,
            skills: allSkills,
            experience: p.professionalTitle || '',
            career_goal: p.professionalTitle || 'Software Engineer'
        });

        if (res.success && res.summary) {
            targetEl.innerHTML = `
                <div class="p-3 bg-light rounded border mb-3">
                    <div class="mb-0 text-dark resume-summary-text" id="generatedSummaryPreview">${formatSummaryHtml(res.summary)}</div>
                    <textarea class="d-none" id="generatedSummaryRaw">${escapeHtml(res.summary)}</textarea>
                </div>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-primary" onclick="applySummaryToResume()">
                        <i class="bi bi-check2"></i> Use This Summary
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="copyToClipboard('${escapeJs(res.summary)}')">
                        <i class="bi bi-clipboard"></i> Copy
                    </button>
                </div>
            `;
        } else {
            targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> ${escapeHtml(res.message || 'Generation failed')}</div>`;
        }
    } catch (e) {
        targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> Error contacting AI service.</div>`;
    } finally {
        if (btn) btn.disabled = false;
    }
};

window.applySummaryToResume = function() {
    const rawEl = document.getElementById('generatedSummaryRaw');
    const textEl = document.getElementById('generatedSummaryPreview');
    const text = rawEl ? rawEl.value : (textEl ? textEl.innerText.trim() : '');
    if (text && currentResume) {
        setVal('inputSummary', text);
        currentResume.personal.summary = text;
        renderLivePreview();
        triggerAutosave();
        showToast('Summary applied to your resume!', 'success');
        const modalEl = document.getElementById('aiAssistantModal');
        if (modalEl) bootstrap.Modal.getInstance(modalEl).hide();
    }
};

// FEATURE 2: EXPERIENCE IMPROVER (INLINE)
let currentEditingExpIndex = null;
window.openInlineAiExperienceModal = function(index) {
    currentEditingExpIndex = index;
    const item = currentResume.experience[index];
    if (!item) return;

    openAiTab('experience');
    setVal('aiExpTitle', item.role || '');
    setVal('aiExpCompany', item.company || '');
    setVal('aiExpDesc', item.description || '');
    document.getElementById('aiExperienceResult').innerHTML = '';
};

window.triggerExperienceImprovement = async function() {
    const targetEl = document.getElementById('aiExperienceResult');
    const btn = document.getElementById('btnRunAiExperience');
    if (btn) btn.disabled = true;
    if (targetEl) targetEl.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div><div class="mt-2 text-muted">Optimizing bullet points with action verbs...</div></div>';

    try {
        const res = await postAi('/ai/improve-experience/', {
            job_title: getVal('aiExpTitle'),
            company: getVal('aiExpCompany'),
            description: getVal('aiExpDesc')
        });

        if (res.success && res.improved_text) {
            targetEl.innerHTML = `
                <div class="p-3 bg-light rounded border mb-3">
                    <div class="mb-0 text-dark" id="generatedExpPreview">${formatBulletsHtml(res.improved_text)}</div>
                    <textarea class="d-none" id="generatedExpRaw">${escapeHtml(res.improved_text)}</textarea>
                </div>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-primary" onclick="applyExperienceToResume()">
                        <i class="bi bi-check2"></i> Apply to Experience
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="copyToClipboard('${escapeJs(res.improved_text)}')">
                        <i class="bi bi-clipboard"></i> Copy
                    </button>
                </div>
            `;
        } else {
            targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> ${escapeHtml(res.message || 'Improvement failed')}</div>`;
        }
    } catch (e) {
        targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> Error contacting AI service.</div>`;
    } finally {
        if (btn) btn.disabled = false;
    }
};

window.applyExperienceToResume = function() {
    const rawEl = document.getElementById('generatedExpRaw');
    const textEl = document.getElementById('generatedExpPreview');
    const text = rawEl ? rawEl.value : (textEl ? textEl.innerText.trim() : '');
    if (text && currentResume) {
        if (currentEditingExpIndex !== null && currentResume.experience[currentEditingExpIndex]) {
            currentResume.experience[currentEditingExpIndex].description = text;
            renderExperienceList();
        }
        renderLivePreview();
        triggerAutosave();
        showToast('Experience updated with AI improvements!', 'success');
        const modalEl = document.getElementById('aiAssistantModal');
        if (modalEl) bootstrap.Modal.getInstance(modalEl).hide();
    }
};

// FEATURE 3: PROJECT DESCRIPTION (INLINE)
let currentEditingProjIndex = null;
window.openInlineAiProjectModal = function(index) {
    currentEditingProjIndex = index;
    const item = currentResume.projects[index];
    if (!item) return;

    openAiTab('projects');
    setVal('aiProjName', item.name || '');
    setVal('aiProjTech', item.technologies || '');
    setVal('aiProjFunc', item.description || '');
    document.getElementById('aiProjectResult').innerHTML = '';
};

window.triggerProjectEnhancement = async function() {
    const targetEl = document.getElementById('aiProjectResult');
    const btn = document.getElementById('btnRunAiProject');
    if (btn) btn.disabled = true;
    if (targetEl) targetEl.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div><div class="mt-2 text-muted">Architecting technical bullet points...</div></div>';

    try {
        const res = await postAi('/ai/project-description/', {
            project_name: getVal('aiProjName'),
            technologies: getVal('aiProjTech'),
            functionality: getVal('aiProjFunc')
        });

        if (res.success && res.description) {
            targetEl.innerHTML = `
                <div class="p-3 bg-light rounded border mb-3">
                    <div class="mb-0 text-dark" id="generatedProjPreview">${formatBulletsHtml(res.description)}</div>
                    <textarea class="d-none" id="generatedProjRaw">${escapeHtml(res.description)}</textarea>
                </div>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-primary" onclick="applyProjectToResume()">
                        <i class="bi bi-check2"></i> Apply to Project
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="copyToClipboard('${escapeJs(res.description)}')">
                        <i class="bi bi-clipboard"></i> Copy
                    </button>
                </div>
            `;
        } else {
            targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> ${escapeHtml(res.message || 'Generation failed')}</div>`;
        }
    } catch (e) {
        targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> Error contacting AI service.</div>`;
    } finally {
        if (btn) btn.disabled = false;
    }
};

window.applyProjectToResume = function() {
    const rawEl = document.getElementById('generatedProjRaw');
    const textEl = document.getElementById('generatedProjPreview');
    const text = rawEl ? rawEl.value : (textEl ? textEl.innerText.trim() : '');
    if (text && currentResume) {
        if (currentEditingProjIndex !== null && currentResume.projects[currentEditingProjIndex]) {
            currentResume.projects[currentEditingProjIndex].description = text;
            renderProjectsList();
        }
        renderLivePreview();
        triggerAutosave();
        showToast('Project updated with AI bullet points!', 'success');
        const modalEl = document.getElementById('aiAssistantModal');
        if (modalEl) bootstrap.Modal.getInstance(modalEl).hide();
    }
};

// FEATURE 4: SKILL SUGGESTIONS
window.triggerSkillsSuggestion = async function() {
    const targetEl = document.getElementById('aiSkillsResult');
    const btn = document.getElementById('btnRunAiSkills');
    if (btn) btn.disabled = true;
    if (targetEl) targetEl.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div><div class="mt-2 text-muted">Analyzing target role and skill matrix...</div></div>';

    const p = currentResume.personal || {};
    const s = currentResume.skills || {};
    const existing = [s.languages, s.frameworks, s.tools, s.technical].filter(Boolean).join(', ');

    try {
        const res = await postAi('/ai/skill-suggestions/', {
            career_role: p.professionalTitle || 'Software Engineer',
            existing_skills: existing
        });

        if (res.success && res.data) {
            const d = res.data;
            const rec = d.recommended_to_learn || {};

            let recPills = '';
            const allRec = [
                ...(rec.core_technical || []),
                ...(rec.frameworks_tools || []),
                ...(rec.domain_concepts || [])
            ];

            allRec.forEach(skill => {
                recPills += `
                    <button type="button" class="btn btn-sm btn-outline-primary m-1" onclick="appendSkillToResume('${escapeJs(skill)}')">
                        + ${escapeHtml(skill)}
                    </button>
                `;
            });

            targetEl.innerHTML = `
                ${d.role_insight ? `<div class="mb-2 small text-muted fst-italic">${escapeHtml(d.role_insight)}</div>` : ''}
                <div class="card p-3 bg-light border mb-3">
                    <h6 class="fw-bold mb-2">Recommended In-Demand Skills to Learn:</h6>
                    <p class="small text-muted mb-2">Click any skill to add it directly to your technical skills section:</p>
                    <div>${recPills || '<span class="text-muted">No additional suggestions.</span>'}</div>
                </div>
            `;
        } else {
            targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> ${escapeHtml(res.message || 'Skills analysis failed')}</div>`;
        }
    } catch (e) {
        targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> Error contacting AI service.</div>`;
    } finally {
        if (btn) btn.disabled = false;
    }
};

window.appendSkillToResume = function(skill) {
    if (!currentResume) return;
    const currentTech = getVal('inputSkillsTechnical');
    const updated = currentTech ? `${currentTech}, ${skill}` : skill;
    setVal('inputSkillsTechnical', updated);
    currentResume.skills.technical = updated;
    renderLivePreview();
    triggerAutosave();
    showToast(`Added "${skill}" to Technical Skills!`, 'success');
};

// FEATURE 5: ATS RESUME ANALYZER
window.loadSampleJd = function(roleType) {
    const samples = {
        backend: "Seeking a Backend Developer with experience in Python or Node.js, REST APIs, SQL/PostgreSQL database design, Docker, Git, and Microservices architecture. Responsible for architecting scalable APIs and optimizing queries.",
        fullstack: "Looking for a Full Stack Developer skilled in React, JavaScript, Node.js, MongoDB, REST APIs, Git, and Docker. Responsible for building responsive user interfaces and robust backend services.",
        frontend: "Seeking a Frontend Developer proficient in React, JavaScript, TypeScript, HTML, CSS, Next.js, Redux, and REST APIs. Responsible for delivering modern, performant web applications."
    };
    const text = samples[roleType] || samples.backend;
    setVal('aiAtsJobDescription', text);
    showToast(`Loaded ${roleType} job description! Click 'Run ATS Scan'.`, 'info');
};

window.triggerAtsAnalysis = async function() {
    // 1. Ensure latest form values are synced into currentResume
    syncFormToResumeObject();

    const jd = getVal('aiAtsJobDescription');
    const targetEl = document.getElementById('aiAtsResult');
    const btn = document.getElementById('btnRunAiAts');

    // Validation: Empty Job Description
    if (!jd || !jd.trim()) {
        targetEl.innerHTML = `<div class="alert alert-warning py-3 small mb-0"><i class="bi bi-exclamation-circle-fill me-1"></i> Please paste a target Job Description to analyze your resume's ATS match.</div>`;
        return;
    }

    // Validation: Empty Resume
    const p = currentResume?.personal || {};
    const s = currentResume?.skills || {};
    const hasAnyContent = currentResume && (
        (p.fullName && p.fullName.trim()) ||
        (p.summary && p.summary.trim()) ||
        (p.professionalTitle && p.professionalTitle.trim()) ||
        (s.languages && s.languages.trim()) ||
        (s.frameworks && s.frameworks.trim()) ||
        (s.tools && s.tools.trim()) ||
        (s.technical && s.technical.trim()) ||
        (currentResume.education && currentResume.education.length > 0) ||
        (currentResume.experience && currentResume.experience.length > 0) ||
        (currentResume.projects && currentResume.projects.length > 0)
    );

    if (!hasAnyContent) {
        targetEl.innerHTML = `<div class="alert alert-warning py-3 small mb-0"><i class="bi bi-exclamation-circle-fill me-1"></i> Your resume appears to be empty. Please fill in your skills, work experience, projects, or education in the editor before running the ATS scan.</div>`;
        return;
    }

    if (btn) btn.disabled = true;
    targetEl.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div><div class="mt-2 text-muted">Analyzing resume content, parsing technical keywords, and computing weighted ATS match...</div></div>';

    try {
        const res = await postAi('/ai/ats-analysis/', {
            job_description: jd,
            resume_data: currentResume
        });

        if (res.success && res.data) {
            const d = res.data;

            // Handle condition when no meaningful technical keywords were found in JD
            if (d.no_meaningful_keywords) {
                targetEl.innerHTML = `
                    <div class="alert alert-warning py-3 mb-0">
                        <h6 class="fw-bold mb-1"><i class="bi bi-info-circle me-1"></i> No Meaningful Technical Requirements Identified</h6>
                        <p class="small mb-0 text-secondary">${escapeHtml(d.message || d.explanations?.[0] || 'Please provide a job posting that specifies required technologies, tools, or qualifications.')}</p>
                    </div>
                `;
                return;
            }

            const score = typeof d.ats_score === 'number' ? d.ats_score : 0;

            let scoreColor = '#dc2626'; // red
            let scoreClass = 'text-danger border-danger';
            let matchLabel = 'Needs Improvement';
            if (score >= 75) {
                scoreColor = '#16a34a'; // green
                scoreClass = 'text-success border-success';
                matchLabel = 'Strong Match';
            } else if (score >= 50) {
                scoreColor = '#d97706'; // amber
                scoreClass = 'text-warning border-warning';
                matchLabel = 'Moderate Match';
            }

            const matchingSkills = d.matching_skills || d.matching_keywords || [];
            const missingSkills = d.missing_skills || d.missing_keywords || [];

            let matchBadges = matchingSkills.map(k => `<span class="badge bg-success-subtle text-success border border-success me-1 mb-1"><i class="bi bi-check-circle me-1"></i>${escapeHtml(k)}</span>`).join('');
            let missBadges = missingSkills.map(k => `<span class="badge bg-danger-subtle text-danger border border-danger me-1 mb-1"><i class="bi bi-x-circle me-1"></i>${escapeHtml(k)}</span>`).join('');
            
            let relExp = (d.relevant_experience || []).map(e => `<li class="mb-1">${escapeHtml(e)}</li>`).join('');
            let strengths = (d.strengths || []).map(s => `<li class="mb-1 text-success-emphasis">${escapeHtml(s)}</li>`).join('');
            let improvements = (d.actionable_improvements || []).map(a => `<li class="mb-1">${escapeHtml(a)}</li>`).join('');
            let explanations = (d.explanations || []).map(e => `<li class="mb-1">${escapeHtml(e)}</li>`).join('');

            const sb = d.score_breakdown || {};
            const sk = sb.technical_skills || { score: 0, max: 40, weight: '40%' };
            const exp = sb.experience_projects || { score: 0, max: 25, weight: '25%' };
            const edu = sb.education || { score: 0, max: 15, weight: '15%' };
            const comp = sb.competencies || { score: 0, max: 10, weight: '10%' };
            const cpl = sb.completeness_formatting || { score: 0, max: 10, weight: '10%' };

            targetEl.innerHTML = `
                ${d.target_role ? `
                <div class="alert alert-primary py-2 px-3 small mb-3 border-0 bg-primary-subtle text-primary-emphasis d-flex align-items-center gap-2">
                    <i class="bi bi-bullseye fs-5 text-primary"></i>
                    <div>
                        <strong class="d-block">Target Role Benchmark: ${escapeHtml(d.target_role)}</strong>
                        <span class="text-secondary" style="font-size:0.75rem;">Evaluated against industry-standard engineering competencies for this position.</span>
                    </div>
                </div>` : ''}

                <!-- SCORE OVERVIEW CARD -->
                <div class="card p-3 bg-white border shadow-sm mb-3">
                    <div class="row align-items-center">
                        <div class="col-sm-4 text-center border-end">
                            <div class="score-circle ${scoreClass} mx-auto" style="border-color:${scoreColor} !important; color:${scoreColor} !important;">
                                ${score}
                                <span style="font-size:0.75rem;">/ 100</span>
                            </div>
                            <span class="badge mt-2" style="background:${scoreColor}; color:#fff; font-size:0.8rem;">${matchLabel}</span>
                        </div>
                        <div class="col-sm-8 ps-sm-3">
                            <div class="mb-2">
                                <h6 class="fw-bold mb-1 small text-dark"><i class="bi bi-check2-all text-success"></i> Matched Technical Skills (${matchingSkills.length}):</h6>
                                <div>${matchBadges || '<span class="text-muted small">None matched directly</span>'}</div>
                            </div>
                            <div>
                                <h6 class="fw-bold mb-1 small text-dark"><i class="bi bi-exclamation-octagon text-danger"></i> Missing Technical Skills (${missingSkills.length}):</h6>
                                <div>${missBadges || '<span class="text-success small fw-semibold">All required technical skills matched!</span>'}</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 5-PILLAR WEIGHTED SCORE BREAKDOWN -->
                <div class="card p-3 bg-light border mb-3">
                    <h6 class="fw-bold mb-2 text-dark small"><i class="bi bi-bar-chart-fill text-primary"></i> Score Breakdown (Weighted Pillars):</h6>
                    <div class="row g-2 small">
                        <div class="col-6 col-md-4">
                            <div class="p-2 bg-white rounded border">
                                <div class="text-muted text-truncate" style="font-size:0.75rem;">Technical Skills (40%)</div>
                                <div class="fw-bold text-dark">${sk.score} / ${sk.max} pts</div>
                                <div class="progress" style="height:4px;"><div class="progress-bar bg-primary" style="width:${Math.round((sk.score / (sk.max || 1)) * 100)}%;"></div></div>
                            </div>
                        </div>
                        <div class="col-6 col-md-4">
                            <div class="p-2 bg-white rounded border">
                                <div class="text-muted text-truncate" style="font-size:0.75rem;">Experience & Projects (25%)</div>
                                <div class="fw-bold text-dark">${exp.score} / ${exp.max} pts</div>
                                <div class="progress" style="height:4px;"><div class="progress-bar bg-success" style="width:${Math.round((exp.score / (exp.max || 1)) * 100)}%;"></div></div>
                            </div>
                        </div>
                        <div class="col-6 col-md-4">
                            <div class="p-2 bg-white rounded border">
                                <div class="text-muted text-truncate" style="font-size:0.75rem;">Education (15%)</div>
                                <div class="fw-bold text-dark">${edu.score} / ${edu.max} pts</div>
                                <div class="progress" style="height:4px;"><div class="progress-bar bg-info" style="width:${Math.round((edu.score / (edu.max || 1)) * 100)}%;"></div></div>
                            </div>
                        </div>
                        <div class="col-6 col-md-6">
                            <div class="p-2 bg-white rounded border">
                                <div class="text-muted text-truncate" style="font-size:0.75rem;">Keywords & Competencies (10%)</div>
                                <div class="fw-bold text-dark">${comp.score} / ${comp.max} pts</div>
                                <div class="progress" style="height:4px;"><div class="progress-bar bg-warning" style="width:${Math.round((comp.score / (comp.max || 1)) * 100)}%;"></div></div>
                            </div>
                        </div>
                        <div class="col-12 col-md-6">
                            <div class="p-2 bg-white rounded border">
                                <div class="text-muted text-truncate" style="font-size:0.75rem;">Completeness & Formatting (10%)</div>
                                <div class="fw-bold text-dark">${cpl.score} / ${cpl.max} pts</div>
                                <div class="progress" style="height:4px;"><div class="progress-bar bg-secondary" style="width:${Math.round((cpl.score / (cpl.max || 1)) * 100)}%;"></div></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- RELEVANT EXPERIENCE -->
                ${relExp ? `
                <div class="card p-3 bg-white border mb-3">
                    <h6 class="fw-bold mb-2 text-dark small"><i class="bi bi-briefcase text-primary"></i> Relevant Experience & Applications:</h6>
                    <ul class="mb-0 small ps-3 text-secondary">${relExp}</ul>
                </div>` : ''}

                <!-- STRENGTHS -->
                ${strengths ? `
                <div class="card p-3 bg-white border mb-3">
                    <h6 class="fw-bold mb-2 text-success small"><i class="bi bi-trophy text-success"></i> Candidate Strengths:</h6>
                    <ul class="mb-0 small ps-3">${strengths}</ul>
                </div>` : ''}

                <!-- ACTIONABLE IMPROVEMENTS -->
                ${improvements ? `
                <div class="card p-3 bg-white border mb-3">
                    <h6 class="fw-bold mb-2 text-dark small"><i class="bi bi-lightbulb text-warning"></i> Actionable Improvements:</h6>
                    <ul class="mb-0 small ps-3 text-secondary">${improvements}</ul>
                </div>` : ''}

                <!-- EXPLANATIONS & POINT AUDIT -->
                ${explanations ? `
                <div class="card p-3 bg-light border mb-2">
                    <h6 class="fw-bold mb-2 text-dark small"><i class="bi bi-card-checklist text-secondary"></i> Scoring Audit & Point Details:</h6>
                    <ul class="mb-0 small ps-3 text-secondary" style="font-size:0.8rem;">${explanations}</ul>
                </div>` : ''}

                <div class="mt-2 text-muted fst-italic" style="font-size:0.75rem;">
                    <i class="bi bi-info-circle"></i> ${escapeHtml(d.disclaimer || 'Indicative estimate based on standard ATS keyword indexing algorithms.')}
                </div>
            `;
        } else {
            const isWarn = (res.message || '').toLowerCase().includes('empty') || (res.message || '').toLowerCase().includes('paste');
            const alertClass = isWarn ? 'alert-warning' : 'alert-danger';
            const iconClass = isWarn ? 'bi-exclamation-circle-fill' : 'bi-exclamation-triangle-fill';
            targetEl.innerHTML = `<div class="alert ${alertClass} py-3 small mb-0"><i class="bi ${iconClass} me-1"></i> ${escapeHtml(res.message || 'ATS analysis failed')}</div>`;
        }
    } catch (e) {
        targetEl.innerHTML = `<div class="alert alert-danger py-3 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> Error contacting ATS service.</div>`;
    } finally {
        if (btn) btn.disabled = false;
    }
};

// FEATURE 6: JOB DESCRIPTION MATCHER
window.triggerJobMatch = async function() {
    const jd = getVal('aiMatchJobDescription');
    const targetEl = document.getElementById('aiMatchResult');
    const btn = document.getElementById('btnRunAiMatch');

    if (!jd) {
        targetEl.innerHTML = `<div class="alert alert-warning py-2 small mb-0"><i class="bi bi-exclamation-circle me-1"></i> Please paste the target Job Description.</div>`;
        return;
    }

    if (btn) btn.disabled = true;
    targetEl.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div><div class="mt-2 text-muted">Comparing resume credentials with role expectations...</div></div>';

    try {
        const res = await postAi('/ai/job-match/', {
            job_description: jd,
            resume_data: currentResume
        });

        if (res.success && res.data) {
            const d = res.data;
            const tips = (d.keyword_integration_tips || []).map(t => `<li>${escapeHtml(t)}</li>`).join('');
            const projRec = (d.relevant_project_recommendations || []).map(r => `<li>${escapeHtml(r)}</li>`).join('');

            targetEl.innerHTML = `
                <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded border mb-3">
                    <span class="fw-bold">Job Alignment Match:</span>
                    <span class="badge bg-primary fs-6">${d.match_percentage || 0}%</span>
                </div>
                ${projRec ? `
                <div class="card p-3 bg-light border mb-2">
                    <h6 class="fw-bold mb-1">Tailored Project Recommendations:</h6>
                    <ul class="mb-0 small ps-3">${projRec}</ul>
                </div>` : ''}
                ${tips ? `
                <div class="card p-3 bg-light border">
                    <h6 class="fw-bold mb-1">Keyword Integration Strategy:</h6>
                    <ul class="mb-0 small ps-3">${tips}</ul>
                </div>` : ''}
            `;
        } else {
            targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> ${escapeHtml(res.message || 'Job match failed')}</div>`;
        }
    } catch (e) {
        targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> Error contacting AI service.</div>`;
    } finally {
        if (btn) btn.disabled = false;
    }
};

// FEATURE 7: CAREER OBJECTIVE GENERATOR
window.triggerObjectiveGeneration = async function(level) {
    const targetEl = document.getElementById('aiObjectiveResult');
    const btn = document.getElementById('btnRunAiObjective');
    if (btn) btn.disabled = true;
    if (targetEl) targetEl.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div><div class="mt-2 text-muted">Generating tailored career objectives...</div></div>';

    const p = currentResume.personal || {};
    const s = currentResume.skills || {};
    const edu = (currentResume.education || []).map(e => `${e.degree || ''} at ${e.institution || ''}`).join(', ');

    try {
        const res = await postAi('/ai/career-objective/', {
            education: edu,
            skills: [s.languages, s.frameworks, s.technical].filter(Boolean).join(', '),
            career_interest: p.professionalTitle || 'Software Engineer',
            experience_level: level || getVal('aiObjectiveLevel') || 'Fresher'
        });

        if (res.success && res.objectives) {
            targetEl.innerHTML = `
                <div class="p-3 bg-light rounded border mb-3">
                    <pre class="mb-0 text-wrap font-sans" style="font-size:0.9rem;" id="generatedObjectiveText">${escapeHtml(res.objectives)}</pre>
                </div>
                <button class="btn btn-sm btn-outline-secondary" onclick="copyToClipboard('${escapeJs(res.objectives)}')">
                    <i class="bi bi-clipboard"></i> Copy All Options
                </button>
            `;
        } else {
            targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> ${escapeHtml(res.message || 'Generation failed')}</div>`;
        }
    } catch (e) {
        targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> Error contacting AI service.</div>`;
    } finally {
        if (btn) btn.disabled = false;
    }
};

// FEATURE 8: RESUME REVIEW
window.triggerResumeReview = async function() {
    const targetEl = document.getElementById('aiReviewResult');
    const btn = document.getElementById('btnRunAiReview');
    if (btn) btn.disabled = true;
    if (targetEl) targetEl.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div><div class="mt-2 text-muted">Auditing resume for clarity, tone, and ATS structure...</div></div>';

    try {
        const res = await postAi('/ai/review-resume/', {
            resume_data: currentResume
        });

        if (res.success && res.data) {
            const d = res.data;
            const strengths = (d.strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join('');
            const improvements = (d.areas_to_improve || []).map(i => `<li>${escapeHtml(i)}</li>`).join('');
            const quickWins = (d.quick_wins || []).map(q => `<li>${escapeHtml(q)}</li>`).join('');

            targetEl.innerHTML = `
                <div class="alert alert-success py-2 mb-3">
                    <strong>Verdict:</strong> ${escapeHtml(d.overall_verdict || 'Evaluation completed.')}
                </div>
                <div class="row g-2 mb-3">
                    <div class="col-md-6">
                        <div class="card p-3 bg-light border h-100">
                            <h6 class="fw-bold text-success mb-1"><i class="bi bi-check-circle"></i> Strengths:</h6>
                            <ul class="mb-0 small ps-3">${strengths}</ul>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card p-3 bg-light border h-100">
                            <h6 class="fw-bold text-primary mb-1"><i class="bi bi-arrow-up-circle"></i> Quick Wins:</h6>
                            <ul class="mb-0 small ps-3">${quickWins}</ul>
                        </div>
                    </div>
                </div>
                <div class="card p-3 bg-light border">
                    <h6 class="fw-bold text-warning mb-1"><i class="bi bi-pencil-square"></i> Areas to Refine:</h6>
                    <ul class="mb-0 small ps-3">${improvements}</ul>
                </div>
            `;
        } else {
            targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> ${escapeHtml(res.message || 'Review failed')}</div>`;
        }
    } catch (e) {
        targetEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i> Error contacting AI service.</div>`;
    } finally {
        if (btn) btn.disabled = false;
    }
};

// ==============================================================================
// PDF DOWNLOAD / PRINTING
// ==============================================================================
window.downloadPdf = async function() {
    // 1. Sync latest changes into resume model and preview DOM
    syncFormToResumeObject();
    renderLivePreview();
    if (currentResume) {
        ResumeStorage.save(currentResume);
    }

    // 2. Ensure preview column is visible in DOM (e.g. if on mobile tab)
    const colPreview = document.getElementById('previewColumn');
    const hadDNone = colPreview && colPreview.classList.contains('d-none');
    if (hadDNone) {
        colPreview.classList.remove('d-none');
    }

    // 3. Set clean document title so the saved PDF defaults to a professional filename (prevents browser URL or raw path)
    const origTitle = document.title;
    const candidateName = (currentResume && currentResume.personal && currentResume.personal.fullName)
        ? currentResume.personal.fullName.trim()
        : 'Resume';
    document.title = `${candidateName} - Resume`;

    // 4. Wait for web fonts (Inter, Plus Jakarta Sans, etc.) to load completely
    if (document.fonts && document.fonts.ready) {
        try {
            await document.fonts.ready;
        } catch (e) {
            console.warn('Font loading wait warning:', e);
        }
    }

    // 5. Slight delay to guarantee browser layout calculation before print dialog opens
    setTimeout(() => {
        window.print();
        document.title = origTitle;
        // Restore mobile tab state after print dialog closes
        if (hadDNone && colPreview) {
            colPreview.classList.add('d-none');
        }
    }, 150);
};

// ==============================================================================
// UTILITIES
// ==============================================================================
function escapeJs(str) {
    if (!str) return '';
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n').replace(/\r/g, '');
}

window.copyToClipboard = function(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy', 'danger');
    });
};

function showToast(message, type = 'primary') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container-custom';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast-custom border-${type}`;
    toast.innerHTML = `
        <i class="bi bi-${type === 'success' ? 'check-circle-fill text-success' : 'info-circle-fill text-primary'} fs-5"></i>
        <span>${escapeHtml(message)}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 2800);
}
