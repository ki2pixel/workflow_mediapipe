import { domBatcher } from './utils/DOMBatcher.js';
import { appState } from './state/AppState.js';

let lastFocusedStepElement = null;

function getEl(id) {
    const el = document.getElementById(id);
    if (!el) {
        console.warn(`[StepDetails] Missing element: #${id}`);
    }
    return el;
}

export function refreshStepDetailsPanelIfOpen(stepKey) {
    const open = !!appState.getStateProperty('ui.stepDetailsOpen');
    const selectedStepKey = appState.getStateProperty('ui.selectedStepKey');
    if (!open) return;
    if (!selectedStepKey) return;
    if (stepKey && stepKey !== selectedStepKey) return;
    updatePanelFromStep(selectedStepKey);
}

function getStepKeyFromElement(el) {
    if (!el) return null;
    const stepKey = el.dataset ? el.dataset.stepKey : null;
    return stepKey || null;
}

function setStepsExpandedState(selectedStepKey, expanded) {
    const steps = document.querySelectorAll('.timeline-step');
    steps.forEach((stepEl) => {
        const stepKey = getStepKeyFromElement(stepEl);
        const isSelected = !!selectedStepKey && stepKey === selectedStepKey;
        stepEl.setAttribute('aria-expanded', expanded && isSelected ? 'true' : 'false');
        if (isSelected && expanded) {
            stepEl.classList.add('is-selected');
        } else {
            stepEl.classList.remove('is-selected');
        }
    });
}

function updatePanelFromStep(stepKey) {
    const panel = getEl('step-details-panel');
    if (!panel) return;

    const titleEl = getEl('step-details-title');
    const statusEl = getEl('step-details-status');
    const timerEl = getEl('step-details-timer');
    const progressTextEl = getEl('step-details-progress-text');

    const runBtn = getEl('step-details-run');
    const cancelBtn = getEl('step-details-cancel');
    const logsBtn = getEl('step-details-open-logs');

    const stepCard = document.getElementById(`step-${stepKey}`);
    const stepName = stepCard ? (stepCard.dataset.stepName || stepKey) : stepKey;

    const statusBadge = document.getElementById(`status-${stepKey}`);
    const timerSource = document.getElementById(`timer-${stepKey}`);
    const progressTextSource = document.getElementById(`progress-text-${stepKey}`);

    const stepRunButton = document.querySelector(`.run-button[data-step="${stepKey}"]`);
    const stepCancelButton = document.querySelector(`.cancel-button[data-step="${stepKey}"]`);

    domBatcher.scheduleUpdate(`step-details-update:${stepKey}`, () => {
        if (titleEl) {
            titleEl.textContent = `Détails — ${stepName}`;
        }

        if (statusEl) {
            if (statusBadge) {
                statusEl.textContent = statusBadge.textContent || 'Prêt';
                statusEl.className = statusBadge.className || 'status-badge status-idle';
            } else {
                statusEl.textContent = 'Prêt';
                statusEl.className = 'status-badge status-idle';
            }
        }

        if (timerEl) {
            timerEl.textContent = timerSource ? (timerSource.textContent || '') : '';
        }

        if (progressTextEl) {
            progressTextEl.textContent = progressTextSource ? (progressTextSource.textContent || '') : '';
        }

        if (runBtn) {
            runBtn.disabled = !stepRunButton || !!stepRunButton.disabled;
        }

        if (cancelBtn) {
            cancelBtn.disabled = !stepCancelButton || !!stepCancelButton.disabled;
        }

        if (logsBtn) {
            logsBtn.disabled = !stepKey;
        }

        panel.dataset.stepKey = stepKey;
    });
}

function openPanel(stepKey) {
    const wrapper = getEl('workflow-wrapper');
    const panel = getEl('step-details-panel');
    const closeBtn = getEl('close-step-details');

    if (!wrapper || !panel) return;

    lastFocusedStepElement = document.getElementById(`step-${stepKey}`);

    appState.setState({ ui: { stepDetailsOpen: true, selectedStepKey: stepKey } }, 'step_details_open');

    domBatcher.scheduleUpdate('step-details-open', () => {
        panel.hidden = false;
        wrapper.classList.add('details-active');
        setStepsExpandedState(stepKey, true);
    });

    updatePanelFromStep(stepKey);

    requestAnimationFrame(() => {
        try {
            if (closeBtn && typeof closeBtn.focus === 'function') {
                closeBtn.focus();
            }
        } catch (_) {}
    });
}

function closePanel() {
    const wrapper = getEl('workflow-wrapper');
    const panel = getEl('step-details-panel');

    if (!wrapper || !panel) return;

    const selectedStepKey = appState.getStateProperty('ui.selectedStepKey');
    appState.setState({ ui: { stepDetailsOpen: false, selectedStepKey: null } }, 'step_details_close');

    domBatcher.scheduleUpdate('step-details-close', () => {
        wrapper.classList.remove('details-active');
        panel.hidden = true;
        setStepsExpandedState(selectedStepKey, false);
        panel.removeAttribute('data-step-key');
    });

    requestAnimationFrame(() => {
        try {
            if (lastFocusedStepElement && typeof lastFocusedStepElement.focus === 'function') {
                lastFocusedStepElement.focus();
            }
        } catch (_) {}
        lastFocusedStepElement = null;
    });
}

function isLogsPanelOpen() {
    const wrapper = getEl('workflow-wrapper');
    return !!(wrapper && wrapper.classList.contains('logs-active'));
}

function attachStepSelectionListeners() {
    const steps = document.querySelectorAll('.timeline-step');

    steps.forEach((stepEl) => {
        const handleSelect = () => {
            if (isLogsPanelOpen()) return;
            const stepKey = getStepKeyFromElement(stepEl);
            if (!stepKey) return;
            openPanel(stepKey);
        };

        stepEl.addEventListener('click', (e) => {
            if (e && e.target && e.target.closest) {
                const interactive = e.target.closest('button, a, input, select, textarea');
                if (interactive) return;
            }
            handleSelect();
        });

        stepEl.addEventListener('keydown', (e) => {
            if (!e) return;

            if (e.target && e.target.closest) {
                const interactive = e.target.closest('button, a, input, select, textarea');
                if (interactive) return;
            }

            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleSelect();
            }
        });
    });
}

function attachPanelListeners() {
    const closeBtn = getEl('close-step-details');
    const runBtn = getEl('step-details-run');
    const cancelBtn = getEl('step-details-cancel');
    const logsBtn = getEl('step-details-open-logs');
    const panel = getEl('step-details-panel');

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            closePanel();
        });
    }

    if (runBtn) {
        runBtn.addEventListener('click', () => {
            const stepKey = panel ? panel.dataset.stepKey : null;
            if (!stepKey) return;
            const btn = document.querySelector(`.run-button[data-step="${stepKey}"]`);
            if (btn && typeof btn.click === 'function') {
                btn.click();
            }
            updatePanelFromStep(stepKey);
        });
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            const stepKey = panel ? panel.dataset.stepKey : null;
            if (!stepKey) return;
            const btn = document.querySelector(`.cancel-button[data-step="${stepKey}"]`);
            if (btn && typeof btn.click === 'function') {
                btn.click();
            }
            updatePanelFromStep(stepKey);
        });
    }

    if (logsBtn) {
        logsBtn.addEventListener('click', async () => {
            const stepKey = panel ? panel.dataset.stepKey : null;
            if (!stepKey) return;
            closePanel();
            try {
                const mod = await import('./uiUpdater.js');
                if (mod && typeof mod.openLogPanelUI === 'function') {
                    mod.openLogPanelUI(stepKey, true);
                }
            } catch (e) {
                console.error('[StepDetails] Failed to open logs panel:', e);
            }
        });
    }

    document.addEventListener('keydown', (e) => {
        if (!e || e.key !== 'Escape') return;
        const open = !!appState.getStateProperty('ui.stepDetailsOpen');
        if (!open) return;
        closePanel();
    });
}

function attachLogsPanelObserver() {
    const wrapper = getEl('workflow-wrapper');
    if (!wrapper || typeof MutationObserver === 'undefined') return;

    const observer = new MutationObserver(() => {
        if (wrapper.classList.contains('logs-active')) {
            const open = !!appState.getStateProperty('ui.stepDetailsOpen');
            if (open) {
                closePanel();
            }
        }
    });

    observer.observe(wrapper, { attributes: true, attributeFilter: ['class'] });
}

export function initializeStepDetailsPanel() {
    attachStepSelectionListeners();
    attachPanelListeners();
    attachLogsPanelObserver();
}
