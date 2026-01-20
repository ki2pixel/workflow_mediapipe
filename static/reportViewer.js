/**
 * Report Viewer - Visual Analysis Report Generator
 * Workflow MediaPipe v4.0
 * 
 * Generates comprehensive HTML reports with statistics and infographics
 */

import { domBatcher } from './utils/DOMBatcher.js';

class ReportViewer {
    constructor() {
        this.overlay = null;
        this.isVisible = false;
        this.projects = [];
        this.currentReport = null;
        this.selectedFormat = 'html';
        this.availableMonths = new Set();
        this.prevFocusEl = null;
        this._keydownHandler = null;
    }

    _getFocusableElements(container) {
        if (!container || typeof container.querySelectorAll !== 'function') return [];
        const selectors = [
            'a[href]',
            'button:not([disabled])',
            'textarea:not([disabled])',
            'input:not([disabled])',
            'select:not([disabled])',
            '[tabindex]:not([tabindex="-1"])'
        ];
        return Array.from(container.querySelectorAll(selectors.join(',')))
            .filter(el => el && typeof el.focus === 'function' && (el.offsetParent !== null || (typeof el.getAttribute === 'function' && el.getAttribute('aria-hidden') !== 'true')));
    }

    _enableModalFocusTrap() {
        const overlay = this.overlay;
        if (!overlay) return;

        try {
            const currentFocused = document.activeElement;
            if (currentFocused && currentFocused !== document.body && currentFocused !== document.documentElement && typeof currentFocused.focus === 'function') {
                this.prevFocusEl = currentFocused;
            } else {
                this.prevFocusEl = null;
            }
        } catch {
            this.prevFocusEl = null;
        }

        if (typeof overlay.getAttribute === 'function' && overlay.getAttribute('tabindex') === null && typeof overlay.setAttribute === 'function') {
            overlay.setAttribute('tabindex', '-1');
        }

        const focusables = this._getFocusableElements(overlay);
        const first = focusables[0] || overlay;
        if (first && typeof first.focus === 'function') {
            first.focus();
        }

        this._keydownHandler = (e) => {
            if (e.key === 'Escape') {
                e.preventDefault();
                this.close();
                return;
            }
            if (e.key === 'Tab') {
                const focusEls = this._getFocusableElements(overlay);
                if (focusEls.length === 0) {
                    e.preventDefault();
                    overlay.focus && overlay.focus();
                    return;
                }
                const currentIndex = focusEls.indexOf(document.activeElement);
                let nextIndex = currentIndex;
                if (e.shiftKey) {
                    nextIndex = currentIndex <= 0 ? focusEls.length - 1 : currentIndex - 1;
                } else {
                    nextIndex = currentIndex === focusEls.length - 1 ? 0 : currentIndex + 1;
                }
                e.preventDefault();
                focusEls[nextIndex].focus();
            }
        };

        overlay.addEventListener('keydown', this._keydownHandler);
    }

    _disableModalFocusTrap() {
        const overlay = this.overlay;
        if (overlay && this._keydownHandler) {
            overlay.removeEventListener('keydown', this._keydownHandler);
        }
        this._keydownHandler = null;
        const prev = this.prevFocusEl;
        this.prevFocusEl = null;

        if (prev && typeof prev.focus === 'function') {
            try {
                prev.focus();
            } catch (_) {}
        }
    }

    /**
     * Generate monthly archive report
     */
    async generateMonthlyReport() {
        try {
            const monthInput = document.getElementById('report-month-select');
            const previewContainer = document.getElementById('report-preview-container');
            if (!monthInput) return;

            const month = (monthInput.value || '').trim();
            if (!month) {
                this.showError('Veuillez sélectionner un mois au format YYYY-MM.');
                return;
            }

            this.showLoading(previewContainer);

            const response = await fetch('/api/reports/generate/monthly', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ month })
            });

            if (!response.ok) {
                let backendMsg = '';
                try {
                    const err = await response.json();
                    backendMsg = err && err.error ? ` — ${err.error}` : '';
                } catch {}
                const message = `HTTP ${response.status}: ${response.statusText}${backendMsg}`;
                throw new Error(message);
            }

            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }

            // Render the monthly HTML into the preview container
            this.currentReport = { ...data, project_name: null, video_name: null };
            this.renderReport({ html: data.html, format: 'html' }, previewContainer);

            // Enable download button
            const downloadButton = document.getElementById('report-download-button');
            if (downloadButton) downloadButton.disabled = false;

        } catch (error) {
            console.error('[ReportViewer] Error generating monthly report:', error);
            let hint = '';
            if (this.availableMonths && this.availableMonths.size > 0) {
                hint = `\nMois disponibles: ${Array.from(this.availableMonths).sort().join(', ')}`;
            }
            this.showError('Erreur de génération du rapport mensuel: ' + error.message + hint);
        }
    }

    /**
     * Parse a project name that may contain a timestamp suffix
     * Pattern: "<base> YYYY-MM-DD_HH-MM-SS"
     * Returns { baseName, timestampRaw, timestampPretty }
     */
    parseArchiveName(name) {
        try {
            const m = name.match(/^(.*) (\d{4}-\d{2}-\d{2}_)\b(\d{2}-\d{2}-\d{2})$/);
            if (!m) {
                return { baseName: name, timestampRaw: null, timestampPretty: null };
            }
            const base = m[1];
            const datePart = m[2].slice(0, -1); // remove trailing underscore
            const timePart = m[3].replace(/-/g, ':');
            const pretty = `${datePart} ${timePart}`; // YYYY-MM-DD HH:MM:SS
            return { baseName: base, timestampRaw: `${datePart}_${m[3]}`, timestampPretty: pretty };
        } catch {
            return { baseName: name, timestampRaw: null, timestampPretty: null };
        }
    }

    /**
     * Initialize the report viewer
     */
    init() {
        console.log('[ReportViewer] Initializing...');
        
        this.overlay = document.getElementById('report-overlay');
        
        if (!this.overlay) {
            console.warn('[ReportViewer] Report overlay not found');
            return;
        }

        this.setupEventHandlers();
        
        console.log('[ReportViewer] Initialized successfully');
    }

    /**
     * Setup event handlers
     */
    setupEventHandlers() {
        // Open button
        const openButton = document.getElementById('open-report-button');
        if (openButton) {
            openButton.addEventListener('click', () => this.open());
        }

        // Close button
        const closeButton = document.getElementById('report-close');
        if (closeButton) {
            closeButton.addEventListener('click', () => this.close());
        }

        // Close on overlay click
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.close();
            }
        });

        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isVisible) {
                this.close();
            }
        });

        // Generate button
        const generateButton = document.getElementById('report-generate-button');
        if (generateButton) {
            generateButton.addEventListener('click', () => this.generateReport());
        }

        // Download button
        const downloadButton = document.getElementById('report-download-button');
        if (downloadButton) {
            downloadButton.addEventListener('click', () => this.downloadReport());
        }

        // Project selector change
        const projectSelect = document.getElementById('report-project-select');
        if (projectSelect) {
            projectSelect.addEventListener('change', (e) => this.onProjectChange(e.target.value));
        }

        // No format radios anymore (HTML-only)

        // Optional: project-only checkbox to generate consolidated project report
        const projectOnly = document.getElementById('report-project-only');
        if (projectOnly) {
            projectOnly.addEventListener('change', () => this.updateGenerateButtonState());
        }

        // Monthly report button
        const monthlyBtn = document.getElementById('report-generate-monthly-button');
        if (monthlyBtn) {
            monthlyBtn.addEventListener('click', () => this.generateMonthlyReport());
        }

        // Analyze uploaded monthly report
        const analyzeBtn = document.getElementById('report-analyze-upload-button');
        const uploadInput = document.getElementById('monthly-report-upload');
        const resultEl = document.getElementById('report-analyze-result');
        if (analyzeBtn && uploadInput && resultEl) {
            analyzeBtn.addEventListener('click', async () => {
                try {
                    if (!uploadInput.files || uploadInput.files.length === 0) {
                        resultEl.textContent = 'Veuillez sélectionner un fichier HTML de rapport.';
                        resultEl.className = 'form-feedback error';
                        return;
                    }
                    const file = uploadInput.files[0];
                    const formData = new FormData();
                    formData.append('file', file);
                    resultEl.textContent = 'Analyse en cours...';
                    resultEl.className = 'form-feedback info';

                    const resp = await fetch('/api/reports/analyze/monthly_upload', {
                        method: 'POST',
                        body: formData
                    });
                    if (!resp.ok) {
                        let backendMsg = '';
                        try { const j = await resp.json(); backendMsg = j && j.error ? ` — ${j.error}` : ''; } catch {}
                        throw new Error(`HTTP ${resp.status}: ${resp.statusText}${backendMsg}`);
                    }
                    const data = await resp.json();
                    if (data.error) throw new Error(data.error);

                    const mp4 = data.by_extension?.[".mp4"] ?? 0;
                    const other = data.by_extension?.other ?? 0;
                    const noext = data.by_extension?.noext ?? 0;
                    const parts = [];
                    parts.push(`Total listé: ${data.total_listed}`);
                    parts.push(`.mp4: ${mp4}`);
                    parts.push(`autres: ${other}`);
                    parts.push(`sans extension: ${noext}`);
                    if (typeof data.projects === 'number') parts.push(`projets: ${data.projects}`);
                    if (data.month) parts.push(`mois: ${data.month}`);
                    if (data.build_id) parts.push(`build: ${data.build_id}`);

                    resultEl.textContent = parts.join(' · ');
                    resultEl.className = 'form-feedback success';
                } catch (err) {
                    console.error('[ReportViewer] analyze upload error:', err);
                    resultEl.textContent = `Erreur d\'analyse: ${err.message || err}`;
                    resultEl.className = 'form-feedback error';
                }
            });
        }
    }

    /**
     * Open the report viewer
     */
    async open() {
        console.log('[ReportViewer] Opening report viewer...');

        if (!this.overlay) {
            this.overlay = document.getElementById('report-overlay');
        }
        if (!this.overlay) {
            return;
        }
        
        this.isVisible = true;
        this.overlay.style.display = 'flex';
        this._enableModalFocusTrap();
        
        // Trigger reflow for animation
        setTimeout(() => {
            this.overlay.setAttribute('data-visible', 'true');
        }, 10);

        // Load projects list
        await this.loadProjects();
    }

    /**
     * Close the report viewer
     */
    close() {
        console.log('[ReportViewer] Closing report viewer...');

        if (!this.overlay) {
            this.overlay = document.getElementById('report-overlay');
        }
        if (!this.overlay) {
            this.isVisible = false;
            return;
        }
        
        this.isVisible = false;
        this.overlay.setAttribute('data-visible', 'false');
        
        setTimeout(() => {
            this.overlay.style.display = 'none';
            this._disableModalFocusTrap();
        }, 300);
    }

    /**
     * Load available projects from API
     */
    async loadProjects() {
        try {
            const response = await fetch('/api/visualization/projects');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            this.projects = data.projects || [];
            // Build available months set from archive timestamps
            this.availableMonths = new Set(
                (this.projects || [])
                    .map(p => (p.archive_timestamp || '').slice(0, 7))
                    .filter(m => /\d{4}-\d{2}/.test(m))
            );
            // Prefill month selector to current month if empty
            const monthInput = document.getElementById('report-month-select');
            if (monthInput && !monthInput.value) {
                const currentMonth = new Date().toISOString().slice(0, 7);
                monthInput.value = currentMonth;
                if (!this.availableMonths.has(monthInput.value) && this.availableMonths.size > 0) {
                    // Pick any available month to help the user
                    const first = Array.from(this.availableMonths)[0];
                    monthInput.value = first;
                }
            }
            this.renderProjectSelector();

            console.log(`[ReportViewer] Loaded ${this.projects.length} projects`);

        } catch (error) {
            console.error('[ReportViewer] Error loading projects:', error);
            this.showError('Impossible de charger les projets: ' + error.message);
        }
    }

    /**
     * Update generate button enabled/disabled state based on selections
     */
    updateGenerateButtonState() {
        const projectSelect = document.getElementById('report-project-select');
        const videoSelect = document.getElementById('report-video-select');
        const generateButton = document.getElementById('report-generate-button');
        const projectOnly = document.getElementById('report-project-only');

        if (!generateButton || !projectSelect) return;

        const hasProject = !!projectSelect.value;
        const isProjectOnly = !!(projectOnly && projectOnly.checked);
        const hasVideo = !!(videoSelect && videoSelect.value);

        generateButton.disabled = !(hasProject && (isProjectOnly || hasVideo));
    }

    /**
     * Render project selector dropdown
     */
    renderProjectSelector() {
        const projectSelect = document.getElementById('report-project-select');
        const videoSelect = document.getElementById('report-video-select');
        
        if (!projectSelect) return;

        domBatcher.scheduleUpdate('report-projects-select', () => {
            // Clear and populate project selector
            projectSelect.innerHTML = '<option value="">-- Sélectionner un projet --</option>';

            this.projects.forEach(project => {
                const option = document.createElement('option');
                option.value = project.name;
                // Prefer backend-provided fields; fallback to local parsing
                const baseLabel = project.display_base || this.parseArchiveName(project.name).baseName;
                const tsPretty = project.archive_timestamp || this.parseArchiveName(project.name).timestampPretty;
                const countLabel = `(${project.video_count} vidéo${project.video_count > 1 ? 's' : ''})`;
                const tsLabel = tsPretty ? ` — archivé le ${tsPretty}` : '';

                // Accessibility: expose full timestamp on hover
                if (tsPretty) {
                    option.title = `Archivé le ${tsPretty}`;
                }

                // Use textContent to avoid HTML injection
                option.textContent = `${baseLabel} ${countLabel}${tsLabel}`;
                projectSelect.appendChild(option);
            });
        });

        // Reset video selector
        if (videoSelect) {
            videoSelect.innerHTML = '<option value="">-- Sélectionner une vidéo --</option>';
            videoSelect.disabled = true;
        }

        // Disable generate button
        const generateButton = document.getElementById('report-generate-button');
        if (generateButton) {
            generateButton.disabled = true;
        }
    }

    /**
     * Handle project selection change
     */
    onProjectChange(projectName) {
        const videoSelect = document.getElementById('report-video-select');
        const generateButton = document.getElementById('report-generate-button');
        const projectOnly = document.getElementById('report-project-only');
        
        if (!projectName || !videoSelect) return;

        const project = this.projects.find(p => p.name === projectName);
        
        if (!project) return;

        // Populate video selector
        videoSelect.innerHTML = '<option value="">-- Sélectionner une vidéo --</option>';
        
        project.videos.forEach(video => {
            const option = document.createElement('option');
            option.value = video;
            option.textContent = video;
            videoSelect.appendChild(option);
        });

        videoSelect.disabled = false;

        // Enable generate button when video is selected (unless project-only mode)
        videoSelect.onchange = () => this.updateGenerateButtonState();
        this.updateGenerateButtonState();
    }

    /**
     * Generate report for selected project/video
     */
    async generateReport() {
        const projectSelect = document.getElementById('report-project-select');
        const videoSelect = document.getElementById('report-video-select');
        const previewContainer = document.getElementById('report-preview-container');
        const projectOnly = document.getElementById('report-project-only');
        
        if (!projectSelect || !videoSelect) return;

        const projectName = projectSelect.value;
        const videoName = videoSelect.value;

        if (!projectName) return;

        try {
            this.showLoading(previewContainer);

            const isProjectOnly = !!(projectOnly && projectOnly.checked);
            const endpoint = isProjectOnly ? '/api/reports/generate/project' : '/api/reports/generate';
            const body = isProjectOnly
                ? { project: projectName, format: 'html' }
                : { project: projectName, video: videoName, format: 'html' };

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            this.currentReport = data;
            this.renderReport(data, previewContainer);

            console.log('[ReportViewer] Report generated successfully');

        } catch (error) {
            console.error('[ReportViewer] Error generating report:', error);
            this.showError('Erreur de génération: ' + error.message);
        }
    }

    /**
     * Show loading state
     */
    showLoading(container) {
        domBatcher.scheduleUpdate('report-loading', () => {
            container.innerHTML = `
                <div class="report-loading">
                    <div class="report-loading-spinner"></div>
                    <div class="report-loading-text">Génération du rapport en cours...</div>
                </div>
            `;
        });
    }

    /**
     * Show error state
     */
    showError(message) {
        const previewContainer = document.getElementById('report-preview-container');
        if (!previewContainer) return;

        domBatcher.scheduleUpdate('report-error', () => {
            previewContainer.innerHTML = `
                <div class="report-preview-empty">
                    <div class="report-preview-icon">⚠️</div>
                    <div class="report-preview-message">Erreur</div>
                    <div class="report-preview-detail">${this.escapeHtml(message)}</div>
                </div>
            `;
        });
    }

    /**
     * Render generated report
     */
    renderReport(data, container) {
        const { html, format } = data;

        let content = '';

        if (format === 'html' && html) {
            // Create sandboxed iframe for HTML preview. We do NOT escape srcdoc to allow proper rendering.
            content = `
                <iframe class="report-preview-iframe" id="report-iframe" sandbox="allow-same-origin" srcdoc='${html.replace(/'/g, "&#39;")}'></iframe>
                <div class="report-download-info">
                    <div class="report-download-icon">✅</div>
                    <div>
                        <div style="font-weight: 600;">Rapport généré avec succès</div>
                        <div style="font-size: 14px; opacity: 0.9;">Utilisez le bouton "Télécharger" pour sauvegarder</div>
                    </div>
                </div>
            `;
        } else {
            content = `
                <div class="report-preview-empty">
                    <div class="report-preview-icon">📊</div>
                    <div class="report-preview-message">Aucun contenu disponible</div>
                </div>
            `;
        }

        domBatcher.scheduleUpdate('report-render', () => {
            container.innerHTML = content;
        });

        // Enable download button
        const downloadButton = document.getElementById('report-download-button');
        if (downloadButton) {
            downloadButton.disabled = false;
        }
    }

    /**
     * Download current report
     */
    downloadReport() {
        if (!this.currentReport) return;

        const { html, format, video_name, project_name } = this.currentReport;
        const timestamp = new Date().toISOString().split('T')[0];
        const baseName = video_name
            ? video_name.replace(/\.[^/.]+$/, "")
            : (project_name || 'projet');
        
        if (format === 'html' && html) {
            // Download HTML
            const blob = new Blob([html], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `rapport_${baseName}_${timestamp}.html`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    }

    /**
     * Update format selection UI
     */
    updateFormatSelection() {
        const formatOptions = document.querySelectorAll('.report-format-option');
        formatOptions.forEach(option => {
            const radio = option.querySelector('input[type="radio"]');
            if (radio && radio.value === this.selectedFormat) {
                option.classList.add('selected');
            } else {
                option.classList.remove('selected');
            }
        });
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Create and export singleton instance
const reportViewer = new ReportViewer();
export { reportViewer };
