/**
 * Cinematic Log Mode Manager - Workflow MediaPipe v4.0
 * Matrix-style log visualization with enhanced visual effects
 */

const CINEMATIC_MODE_STORAGE_KEY = 'workflow-cinematic-logs';

class CinematicLogMode {
    constructor() {
        this.isEnabled = this.loadPreference();
        this.toggleCheckbox = null;
        this.logPanels = [];
    }

    /**
     * Initialize the cinematic log mode system
     */
    init() {
        console.log('[CinematicLogMode] Initializing...');
        
        if (this.isEnabled) {
            this.enable();
        }
        
        this.setupToggle();
        
        console.log(`[CinematicLogMode] Initialized - Mode: ${this.isEnabled ? 'ENABLED' : 'DISABLED'}`);
    }

    /**
     * Load preference from localStorage
     * @returns {boolean}
     */
    loadPreference() {
        try {
            const saved = localStorage.getItem(CINEMATIC_MODE_STORAGE_KEY);
            return saved === 'true';
        } catch (error) {
            console.error('[CinematicLogMode] Error loading preference:', error);
            return false;
        }
    }

    /**
     * Save preference to localStorage
     * @param {boolean} enabled
     */
    savePreference(enabled) {
        try {
            localStorage.setItem(CINEMATIC_MODE_STORAGE_KEY, enabled.toString());
            console.log(`[CinematicLogMode] Saved preference: ${enabled}`);
        } catch (error) {
            console.error('[CinematicLogMode] Error saving preference:', error);
        }
    }

    /**
     * Setup the toggle checkbox
     */
    setupToggle() {
        this.toggleCheckbox = document.getElementById('cinematic-mode-toggle');
        const container = document.querySelector('.cinematic-toggle-container');
        
        if (!this.toggleCheckbox) {
            console.warn('[CinematicLogMode] Toggle checkbox not found');
            return;
        }

        this.toggleCheckbox.checked = this.isEnabled;
        if (this.isEnabled && container) {
            container.classList.add('active');
        }

        this.toggleCheckbox.addEventListener('change', (e) => {
            const enabled = e.target.checked;
            console.log(`[CinematicLogMode] User toggled: ${enabled}`);
            
            if (enabled) {
                this.enable();
            } else {
                this.disable();
            }
            
            if (container) {
                container.classList.toggle('active', enabled);
            }
        });

        if (container) {
            container.addEventListener('click', (e) => {
                if (e.target === container || e.target.classList.contains('cinematic-toggle-label')) {
                    this.toggleCheckbox.checked = !this.toggleCheckbox.checked;
                    this.toggleCheckbox.dispatchEvent(new Event('change'));
                }
            });
        }

        console.log('[CinematicLogMode] Toggle setup complete');
    }

    /**
     * Get all log panel elements
     * @returns {NodeList}
     */
    getLogPanels() {
        return document.querySelectorAll('#logs-column-global, .log-panel, #log-panel');
    }

    /**
     * Enable cinematic mode
     */
    enable() {
        console.log('[CinematicLogMode] Enabling cinematic mode...');
        
        this.isEnabled = true;
        this.savePreference(true);
        
        const panels = this.getLogPanels();
        panels.forEach(panel => {
            if (!panel.classList.contains('log-panel')) {
                panel.classList.add('log-panel');
            }
            panel.setAttribute('data-cinematic-mode', 'true');
        });

        if (this.toggleCheckbox && !this.toggleCheckbox.checked) {
            this.toggleCheckbox.checked = true;
        }

        window.dispatchEvent(new CustomEvent('cinematicModeChanged', {
            detail: { enabled: true }
        }));

        console.log(`[CinematicLogMode] Enabled on ${panels.length} panel(s)`);
    }

    /**
     * Disable cinematic mode
     */
    disable() {
        console.log('[CinematicLogMode] Disabling cinematic mode...');
        
        this.isEnabled = false;
        this.savePreference(false);
        
        const panels = this.getLogPanels();
        panels.forEach(panel => {
            panel.removeAttribute('data-cinematic-mode');
        });

        if (this.toggleCheckbox && this.toggleCheckbox.checked) {
            this.toggleCheckbox.checked = false;
        }

        window.dispatchEvent(new CustomEvent('cinematicModeChanged', {
            detail: { enabled: false }
        }));

        console.log(`[CinematicLogMode] Disabled on ${panels.length} panel(s)`);
    }

    /**
     * Toggle cinematic mode
     */
    toggle() {
        if (this.isEnabled) {
            this.disable();
        } else {
            this.enable();
        }
    }

    /**
     * Apply cinematic mode to a specific element
     * Useful for dynamically created log panels
     * @param {HTMLElement} element
     */
    applyToElement(element) {
        if (!element) return;
        
        if (this.isEnabled) {
            element.setAttribute('data-cinematic-mode', 'true');
            console.log('[CinematicLogMode] Applied to new element');
        }
    }

    /**
     * Get current state
     * @returns {boolean}
     */
    getState() {
        return this.isEnabled;
    }
}

const cinematicLogMode = new CinematicLogMode();

export { cinematicLogMode };

window.cinematicLogMode = cinematicLogMode;
