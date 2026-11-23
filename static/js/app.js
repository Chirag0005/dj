/**
 * static/js/app.js
 * ResumeCraft AI - Global Application Controller & Dashboard Manager
 */

document.addEventListener('DOMContentLoaded', async () => {
    // If on Dashboard, render saved resumes
    if (document.getElementById('savedResumesGrid')) {
        await initDashboard();
    }

    // If on Preview Page, render standalone preview
    if (document.getElementById('standalonePreviewSheet')) {
        initStandalonePreview();
    }
});

// ==============================================================================
// DASHBOARD LOGIC
// ==============================================================================
async function initDashboard() {
    // If empty, pre-populate default CSE sample resume for instant wow-factor
    await ResumeStorage.initDefaultIfEmpty();
    renderDashboardResumes();
}

function renderDashboardResumes() {
    const grid = document.getElementById('savedResumesGrid');
    const emptyState = document.getElementById('dashboardEmptyState');
    const countBadge = document.getElementById('savedResumesCount');
    if (!grid) return;

    const resumes = ResumeStorage.getAll();

    if (countBadge) {
        countBadge.textContent = `${resumes.length} ${resumes.length === 1 ? 'Resume' : 'Resumes'}`;
    }

    if (resumes.length === 0) {
        grid.innerHTML = '';
        if (emptyState) emptyState.classList.remove('d-none');
        return;
    }

    if (emptyState) emptyState.classList.add('d-none');
    grid.innerHTML = '';

    resumes.forEach(res => {
        const score = ResumeStorage.calculateCompletion(res);
        const lastMod = res.lastModified ? new Date(res.lastModified).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        }) : 'Recently';

        const tmplBadge = getTemplateBadgeName(res.template || 'classic');

        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4 mb-4';
        col.innerHTML = `
            <div class="resume-card">
                <div class="resume-card-thumb" onclick="location.href='/edit/?id=${res.id}'">
                    <div class="mini-resume-sheet">
                        <div class="mini-line accent" style="width: 50%;"></div>
                        <div class="mini-line" style="width: 80%;"></div>
                        <div class="mini-line" style="width: 70%; margin-bottom: 6px;"></div>
                        <div class="mini-line accent" style="width: 40%;"></div>
                        <div class="mini-line" style="width: 90%;"></div>
                        <div class="mini-line" style="width: 85%;"></div>
                        <div class="mini-line" style="width: 60%; margin-bottom: 6px;"></div>
                        <div class="mini-line accent" style="width: 45%;"></div>
                        <div class="mini-line" style="width: 75%;"></div>
                    </div>
                </div>
                <div class="p-3 d-flex flex-column flex-grow-1">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="fw-bold mb-0 text-truncate" style="max-width: 190px;" title="${escapeHtml(res.title || 'Untitled')}">
                            ${escapeHtml(res.title || 'Untitled Resume')}
                        </h6>
                        <span class="badge bg-light text-dark border">${tmplBadge}</span>
                    </div>

                    <div class="mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-1 small text-muted">
                            <span>Completion</span>
                            <span><strong>${score}%</strong></span>
                        </div>
                        <div class="progress progress-thin">
                            <div class="progress-bar progress-bar-custom" style="width: ${score}%"></div>
                        </div>
                    </div>

                    <div class="small text-muted mb-3">
                        <i class="bi bi-clock-history"></i> Edited ${lastMod}
                    </div>

                    <div class="mt-auto d-flex justify-content-between align-items-center pt-2 border-top">
                        <div class="btn-group">
                            <a href="/edit/?id=${res.id}" class="btn btn-sm btn-primary-custom" title="Edit Resume">
                                <i class="bi bi-pencil-square"></i> Edit
                            </a>
                            <a href="/preview/?id=${res.id}" class="btn btn-sm btn-outline-custom" title="Preview & Download">
                                <i class="bi bi-eye"></i>
                            </a>
                        </div>
                        <div class="dropdown">
                            <button class="btn btn-sm btn-icon" data-bs-toggle="dropdown" aria-expanded="false">
                                <i class="bi bi-three-dots-vertical"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end shadow-sm">
                                <li>
                                    <button class="dropdown-item" onclick="promptRenameResume('${res.id}', '${escapeJs(res.title)}')">
                                        <i class="bi bi-fonts me-2"></i> Rename
                                    </button>
                                </li>
                                <li>
                                    <button class="dropdown-item" onclick="handleDuplicateResume('${res.id}')">
                                        <i class="bi bi-copy me-2"></i> Duplicate
                                    </button>
                                </li>
                                <li><hr class="dropdown-divider"></li>
                                <li>
                                    <button class="dropdown-item text-danger" onclick="confirmDeleteResume('${res.id}', '${escapeJs(res.title)}')">
                                        <i class="bi bi-trash3 me-2"></i> Delete
                                    </button>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        `;
        grid.appendChild(col);
    });
}

function getTemplateBadgeName(t) {
    switch (t) {
        case 'classic': return 'Professional Classic';
        case 'modern': return 'Modern Minimal';
        case 'developer': return 'Developer Portfolio';
        case 'fresher': return 'Student Fresher';
        default: return 'Classic';
    }
}

// ==============================================================================
// RESUME MANAGEMENT ACTIONS (DELETE, DUPLICATE, RENAME, SAMPLE)
// ==============================================================================

window.handleDuplicateResume = function(id) {
    const cloned = ResumeStorage.duplicate(id);
    if (cloned) {
        showGlobalToast(`Duplicated as "${cloned.title}"`, 'success');
        renderDashboardResumes();
    }
};

window.confirmDeleteResume = function(id, title) {
    const modalEl = document.getElementById('deleteConfirmModal');
    const titleEl = document.getElementById('deleteResumeTitle');
    const deleteBtn = document.getElementById('btnConfirmDelete');

    if (titleEl) titleEl.textContent = title;
    if (deleteBtn) {
        deleteBtn.onclick = () => {
            ResumeStorage.delete(id);
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            showGlobalToast('Resume deleted successfully.', 'success');
            renderDashboardResumes();
        };
    }

    if (modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
};

window.promptRenameResume = function(id, currentTitle) {
    const newTitle = prompt('Enter new resume title:', currentTitle);
    if (newTitle !== null && newTitle.trim()) {
        ResumeStorage.rename(id, newTitle.trim());
        showGlobalToast('Resume renamed!', 'success');
        renderDashboardResumes();
    }
};

window.loadSampleResumeToDashboard = async function() {
    try {
        const resp = await fetch('/api/sample-resumes/');
        if (resp.ok) {
            const json = await resp.json();
            if (json.success && json.data && json.data.sample_developer) {
                const sample = json.data.sample_developer;
                sample.id = 'res_' + Date.now();
                sample.title = 'CS Student / Developer Sample Resume';
                ResumeStorage.save(sample);
                showGlobalToast('Sample resume added to your dashboard!', 'success');
                renderDashboardResumes();
            }
        }
    } catch (e) {
        showGlobalToast('Could not load sample resume.', 'danger');
    }
};

// ==============================================================================
// STANDALONE PREVIEW PAGE CONTROLLER
// ==============================================================================
function initStandalonePreview() {
    const urlParams = new URLSearchParams(window.location.search);
    const resumeId = urlParams.get('id');

    let resume = ResumeStorage.get(resumeId);
    if (!resume) {
        const all = ResumeStorage.getAll();
        resume = all.length > 0 ? all[0] : null;
    }

    if (!resume) {
        document.getElementById('standalonePreviewContainer').innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon"><i class="bi bi-file-earmark-x"></i></div>
                <h4>No Resume Found</h4>
                <p class="text-muted">No resume was specified or saved in your browser.</p>
                <a href="/dashboard/" class="btn btn-primary-custom mt-2">Go to Dashboard</a>
            </div>
        `;
        return;
    }

    // Set page title
    document.title = `${resume.title || 'Resume'} – Preview | ResumeCraft AI`;

    // Render into sheet
    const sheet = document.getElementById('standalonePreviewSheet');
    if (!sheet) return;

    window.currentResume = resume;
    renderLivePreview();

    // Setup edit link
    const editBtn = document.getElementById('btnBackToEditor');
    if (editBtn) {
        editBtn.href = `/edit/?id=${resume.id}`;
    }
}

// ==============================================================================
// GLOBAL TOAST NOTIFICATION HELPER
// ==============================================================================
function showGlobalToast(message, type = 'primary') {
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

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function escapeJs(str) {
    if (!str) return '';
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n').replace(/\r/g, '');
}
