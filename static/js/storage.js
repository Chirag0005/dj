/**
 * static/js/storage.js
 * ResumeCraft AI - Client-side Storage Engine
 *
 * Implements persistent, privacy-preserving resume storage exclusively in browser localStorage.
 * No user data or resumes are ever sent to or stored on the backend database.
 */

const STORAGE_KEY = 'resumecraft_ai_resumes';
const ACTIVE_RESUME_KEY = 'resumecraft_active_id';

class ResumeStorage {
    /**
     * Retrieves all saved resumes from localStorage.
     * @returns {Array} List of resume objects.
     */
    static getAll() {
        try {
            const data = localStorage.getItem(STORAGE_KEY);
            return data ? JSON.parse(data) : [];
        } catch (e) {
            console.error('Failed to parse resumes from localStorage:', e);
            return [];
        }
    }

    /**
     * Retrieves a single resume by unique ID.
     * @param {string} id
     * @returns {Object|null}
     */
    static get(id) {
        if (!id) return null;
        const resumes = this.getAll();
        return resumes.find(r => r.id === id) || null;
    }

    /**
     * Retrieves the active or most recently edited resume.
     * @returns {Object|null}
     */
    static getActive() {
        try {
            const activeId = localStorage.getItem(ACTIVE_RESUME_KEY);
            if (activeId) {
                const resume = this.get(activeId);
                if (resume) return resume;
            }
            const resumes = this.getAll();
            return resumes.length > 0 ? resumes[0] : null;
        } catch (e) {
            console.error('Failed to get active resume:', e);
            return null;
        }
    }

    /**
     * Saves a resume object (creates new or updates existing).
     * @param {Object} resume
     * @returns {Object} Saved resume object
     */
    static save(resume) {
        if (!resume) return null;
        const resumes = this.getAll();

        if (!resume.id) {
            resume.id = 'res_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
        }

        resume.lastModified = new Date().toISOString();
        if (!resume.title) {
            resume.title = (resume.personal && resume.personal.fullName)
                ? `${resume.personal.fullName}'s Resume`
                : 'Untitled Resume';
        }

        const existingIndex = resumes.findIndex(r => r.id === resume.id);
        if (existingIndex >= 0) {
            resumes[existingIndex] = resume;
        } else {
            resumes.unshift(resume);
        }

        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(resumes));
            localStorage.setItem(ACTIVE_RESUME_KEY, resume.id);
            return resume;
        } catch (e) {
            console.error('Failed to save resume to localStorage:', e);
            throw new Error('Storage limit reached or localStorage disabled.');
        }
    }

    /**
     * Deletes a resume by ID.
     * @param {string} id
     * @returns {boolean}
     */
    static delete(id) {
        let resumes = this.getAll();
        const initialCount = resumes.length;
        resumes = resumes.filter(r => r.id !== id);
        if (resumes.length !== initialCount) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(resumes));
            if (localStorage.getItem(ACTIVE_RESUME_KEY) === id) {
                localStorage.removeItem(ACTIVE_RESUME_KEY);
            }
            return true;
        }
        return false;
    }

    /**
     * Duplicates an existing resume.
     * @param {string} id
     * @returns {Object|null} The newly cloned resume
     */
    static duplicate(id) {
        const original = this.get(id);
        if (!original) return null;

        const clone = JSON.parse(JSON.stringify(original));
        clone.id = 'res_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
        clone.title = `Copy of ${original.title || 'Untitled Resume'}`;
        clone.lastModified = new Date().toISOString();

        return this.save(clone);
    }

    /**
     * Renames an existing resume.
     * @param {string} id
     * @param {string} newTitle
     * @returns {boolean}
     */
    static rename(id, newTitle) {
        const resume = this.get(id);
        if (!resume) return false;
        resume.title = newTitle.trim() || 'Untitled Resume';
        this.save(resume);
        return true;
    }

    /**
     * Creates an empty template resume structure.
     * @param {string} templateName
     * @returns {Object}
     */
    static createEmpty(templateName = 'classic') {
        return {
            id: 'res_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6),
            title: 'My Professional Resume',
            template: templateName,
            lastModified: new Date().toISOString(),
            personal: {
                fullName: '',
                professionalTitle: '',
                email: '',
                phone: '',
                location: '',
                linkedin: '',
                github: '',
                portfolio: '',
                summary: ''
            },
            education: [],
            experience: [],
            projects: [],
            skills: {
                languages: '',
                frameworks: '',
                tools: '',
                technical: '',
                soft: ''
            },
            certifications: [],
            achievements: [],
            customization: {
                accentColor: '#6257E8',
                fontFamily: 'Inter',
                fontSize: 'normal',
                spacing: 'normal'
            }
        };
    }

    /**
     * Calculates the completion percentage of a resume.
     * @param {Object} resume
     * @returns {number} Score from 0 to 100
     */
    static calculateCompletion(resume) {
        if (!resume) return 0;
        let score = 0;
        const p = resume.personal || {};

        if (p.fullName && p.fullName.trim()) score += 15;
        if (p.professionalTitle && p.professionalTitle.trim()) score += 10;
        if (p.email && p.email.trim()) score += 10;
        if (p.phone && p.phone.trim()) score += 5;
        if (p.summary && p.summary.trim()) score += 15;
        if (p.linkedin || p.github) score += 5;

        if (Array.isArray(resume.education) && resume.education.length > 0) score += 15;
        if (Array.isArray(resume.experience) && resume.experience.length > 0) score += 10;
        if (Array.isArray(resume.projects) && resume.projects.length > 0) score += 10;

        const s = resume.skills || {};
        if (s.languages || s.technical || s.frameworks) score += 10;

        return Math.min(100, score);
    }

    /**
     * Initializes a sample CSE resume if no resumes exist.
     * Ensures first-time users can immediately preview all templates and AI tools.
     */
    static async initDefaultIfEmpty() {
        const resumes = this.getAll();
        if (resumes.length === 0) {
            try {
                const resp = await fetch('/api/sample-resumes/');
                if (resp.ok) {
                    const json = await resp.json();
                    if (json.success && json.data && json.data.sample_developer) {
                        this.save(json.data.sample_developer);
                        return json.data.sample_developer;
                    }
                }
            } catch (err) {
                console.warn('Could not fetch sample resume from backend:', err);
            }
        }
        return null;
    }
}

// Make globally available
window.ResumeStorage = ResumeStorage;
