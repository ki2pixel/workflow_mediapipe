import { formatElapsedTime, showNotification } from './utils.js';
import * as dom from './domElements.js';
import { appState } from './state/AppState.js';
import { scrollToActiveStep, isAutoScrollEnabled } from './scrollManager.js';

const lastProgressTextByStep = {};

const _lastAutoCenterTsByStep = {};
const _AUTO_CENTER_THROTTLE_MS = 700;

import { soundEvents } from './soundManager.js';
import { domBatcher, DOMUpdateUtils } from './utils/DOMBatcher.js';
import { performanceOptimizer } from './utils/PerformanceOptimizer.js';

let _stepDetailsPanelModulePromise = null;

const STATUS_UI_MAP = {
    running: { label: 'En cours', badgeClass: 'status-running', chipClass: 'state-running', icon: '⏱️' },
    starting: { label: 'Préparation', badgeClass: 'status-running', chipClass: 'state-running', icon: '⚙️' },
    initiated: { label: 'Initialisation', badgeClass: 'status-running', chipClass: 'state-running', icon: '⚙️' },
    completed: { label: 'Terminé', badgeClass: 'status-completed', chipClass: 'state-success', icon: '✅' },
    success: { label: 'Terminé', badgeClass: 'status-success', chipClass: 'state-success', icon: '✅' },
    failed: { label: 'Échec', badgeClass: 'status-failed', chipClass: 'state-error', icon: '❌' },
    error: { label: 'Erreur', badgeClass: 'status-error', chipClass: 'state-error', icon: '⚠️' },
    cancelled: { label: 'Annulé', badgeClass: 'status-cancelled', chipClass: 'state-error', icon: '⛔' },
    warning: { label: 'Attention', badgeClass: 'status-warning', chipClass: 'state-warning', icon: '⚠️' },
    paused: { label: 'En pause', badgeClass: 'status-warning', chipClass: 'state-warning', icon: '⏸️' },
    idle: { label: 'Prêt', badgeClass: 'status-idle', chipClass: 'state-idle', icon: '🕒' },
    pending: { label: 'En attente', badgeClass: 'status-warning', chipClass: 'state-warning', icon: '⏳' }
};

let STEPS_CONFIG_FROM_SERVER = {};
export function setStepsConfig(config) {
    STEPS_CONFIG_FROM_SERVER = config;
}

function getIsAnySequenceRunning() {
    return !!appState.getStateProperty('isAnySequenceRunning');
}

function getActiveStepKeyForLogs() {
    return appState.getStateProperty('activeStepKeyForLogsPanel');
}

function setActiveStepKeyForLogs(stepKey) {
    appState.setState({ activeStepKeyForLogsPanel: stepKey }, 'setActiveStepKeyForLogs');
}

function getSelectedStepsOrder() {
    return appState.getStateProperty('selectedStepsOrder') || [];
}

function getProcessInfo(stepKey) {
    if (!stepKey) return null;
    return appState.getStateProperty(`processInfo.${stepKey}`) || null;
}

function setProcessInfo(stepKey, info) {
    if (!stepKey) return;
    appState.setState({ processInfo: { [stepKey]: info } }, 'process_info_update');
}

function getStepTimers() {
    return appState.getStateProperty('stepTimers') || {};
}

function getStepTimer(stepKey) {
    return getStepTimers()[stepKey];
}

function setStepTimer(stepKey, timerData, source = 'setStepTimer') {
    const timers = getStepTimers();
    appState.setState({ stepTimers: { ...timers, [stepKey]: timerData } }, source);
}

function deleteStepTimer(stepKey) {
    const timers = getStepTimers();
    if (!timers || !Object.prototype.hasOwnProperty.call(timers, stepKey)) return;
    const { [stepKey]: _removed, ...remaining } = timers;
    appState.setState({ stepTimers: remaining }, 'deleteStepTimer');
}

function onWrapperTransitionEndOnce(callback, fallbackMs = 500) {
    const el = dom.workflowWrapper;
    if (!el) { callback(); return; }
    let called = false;
    const handler = (e) => {
        if (called) return;
        called = true;
        el.removeEventListener('transitionend', handler);
        callback();
    };
    el.addEventListener('transitionend', handler, { once: true });
    setTimeout(() => {
        if (called) return;
        try { el.removeEventListener('transitionend', handler); } catch (_) {}
        callback();
    }, fallbackMs);
}

function hideNonActiveSteps(activeStepKey, hidden) {
    try {
        const stepDivs = dom.getAllStepDivs();
        stepDivs.forEach(el => {
            const isActive = activeStepKey && el.id === `step-${activeStepKey}`;
            if (!isActive && hidden) {
                el.classList.add('steps-hidden');
            } else if (isActive && hidden) {
                el.classList.remove('steps-hidden');
            } else if (!hidden) {
                el.classList.remove('steps-hidden');
            }
        });
    } catch (e) {
        console.warn('[UI] hideNonActiveSteps error', e);
    }
}

let previousDownloadIds = new Set();
export function getStepsConfig() {
    return STEPS_CONFIG_FROM_SERVER;
}

function normalizeStatus(status) {
    return typeof status === 'string' ? status.toLowerCase() : 'idle';
}

function getStatusMeta(status) {
    const normalized = normalizeStatus(status);
    return STATUS_UI_MAP[normalized] || STATUS_UI_MAP.idle;
}

function getStepDisplayNameForLogPanel(stepKey) {
    if (!stepKey) return '';
    const config = getStepsConfig();
    const stepConfig = config ? config[stepKey] : null;
    if (stepConfig && stepConfig.display_name) return stepConfig.display_name;

    const stepEl = document.getElementById(`step-${stepKey}`);
    const datasetName = stepEl && stepEl.dataset ? stepEl.dataset.stepName : null;
    if (datasetName) return datasetName;

    return stepKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function updateLogPanelContextUI(stepKey) {
    const displayName = stepKey ? getStepDisplayNameForLogPanel(stepKey) : '';

    const statusEl = stepKey ? document.getElementById(`status-${stepKey}`) : null;
    const timerEl = stepKey ? document.getElementById(`timer-${stepKey}`) : null;

    if (dom.logPanelContextStep) {
        dom.logPanelContextStep.textContent = stepKey ? displayName : 'Aucune étape active';
    }
    if (dom.logPanelContextStatus) {
        dom.logPanelContextStatus.textContent = statusEl ? (statusEl.textContent || '') : '';
    }
    if (dom.logPanelContextTimer) {
        dom.logPanelContextTimer.textContent = timerEl ? (timerEl.textContent || '') : '';
    }
}

function clearLogPanelSpecificButtons() {
    const container = dom.logPanelSpecificButtonsContainer;
    if (!container) return;

    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }
}

function positionLogsPanelNearActiveStep(stepKey) {
    if (!stepKey) return;
    if (!dom.workflowWrapper || !dom.logsColumnGlobal) return;
    if (!dom.workflowWrapper.classList.contains('compact-mode')) return;

    const activeStepElement = document.getElementById(`step-${stepKey}`);
    if (!activeStepElement || typeof activeStepElement.getBoundingClientRect !== 'function') return;

    const rect = activeStepElement.getBoundingClientRect();
    const minTop = 120;
    const minHeight = 280;
    const bottomPadding = 20;

    const maxTop = Math.max(minTop, (window.innerHeight || 800) - minHeight - bottomPadding);
    const targetTop = Math.max(minTop, Math.min(Math.round(rect.top), maxTop));

    dom.logsColumnGlobal.style.top = `${targetTop}px`;
    dom.logsColumnGlobal.style.height = `${Math.max(minHeight, (window.innerHeight || 800) - targetTop - bottomPadding)}px`;
}

function updateStepStateChip(stepKey, status) {
    const chip = document.getElementById(`state-chip-${stepKey}`);
    if (!chip) return;
    const meta = getStatusMeta(status);
    chip.className = `step-state-chip ${meta.chipClass}`;
    chip.textContent = `${meta.icon} ${meta.label}`;
}

export function startStepTimer(stepKey) {
    const existingTimer = getStepTimer(stepKey);
    if (existingTimer && existingTimer.intervalId) {
        clearInterval(existingTimer.intervalId);
    }

    const startTime = Date.now();
    setStepTimer(stepKey, {
        startTime: startTime,
        startTimeDate: new Date(startTime),
        intervalId: null,
        elapsedTimeFormatted: "0s"
    }, 'startStepTimer');

    if (stepKey !== 'clear_disk_cache') {
        domBatcher.scheduleUpdate(`timer-init-${stepKey}`, () => {
            const timerEl = document.getElementById(`timer-${stepKey}`);
            if (timerEl) timerEl.textContent = "(0s)";
        });
    }

    const newIntervalId = setInterval(() => {
        const currentTimer = getStepTimer(stepKey);
        if (!currentTimer || (!currentTimer.startTime && !currentTimer.startTimeDate)) {
            if (currentTimer && currentTimer.intervalId) clearInterval(currentTimer.intervalId);
            return;
        }

        const startTimeToUse = currentTimer.startTime ? new Date(currentTimer.startTime) : currentTimer.startTimeDate;
        const elapsedTimeStr = formatElapsedTime(startTimeToUse);
        setStepTimer(stepKey, { ...currentTimer, elapsedTimeFormatted: elapsedTimeStr }, 'timer_tick');

        if (stepKey !== 'clear_disk_cache') {
            domBatcher.scheduleUpdate(`timer-update-${stepKey}`, () => {
                const timerEl = document.getElementById(`timer-${stepKey}`);
                if (timerEl) timerEl.textContent = `(${elapsedTimeStr})`;
            });
        }
    }, 1000);

    const currentTimerData = getStepTimer(stepKey);
    if (currentTimerData) {
        setStepTimer(stepKey, { ...currentTimerData, intervalId: newIntervalId }, 'timer_interval_set');
    }
}

export function stopStepTimer(stepKey) {
    const timerData = getStepTimer(stepKey);
    if (timerData && timerData.intervalId) {
        clearInterval(timerData.intervalId);
        setStepTimer(stepKey, { ...timerData, intervalId: null }, 'timer_interval_cleared');
    }
    const updatedTimerData = getStepTimer(stepKey);
    if (updatedTimerData && (updatedTimerData.startTime || updatedTimerData.startTimeDate)) {
        const startTimeToUse = updatedTimerData.startTime ? new Date(updatedTimerData.startTime) : updatedTimerData.startTimeDate;
        const elapsedTimeStr = formatElapsedTime(startTimeToUse);
        setStepTimer(stepKey, { ...updatedTimerData, elapsedTimeFormatted: elapsedTimeStr }, 'timer_stopped');
        if (stepKey !== 'clear_disk_cache') {
            const timerEl = document.getElementById(`timer-${stepKey}`);
            if (timerEl) timerEl.textContent = `(Terminé en ${elapsedTimeStr})`;
        }
    }
}

export function resetStepTimerDisplay(stepKey) {
    if (stepKey !== 'clear_disk_cache') {
        const timerEl = document.getElementById(`timer-${stepKey}`);
        if (timerEl) timerEl.textContent = "";
    }
    deleteStepTimer(stepKey);
}

export function updateGlobalUIForSequenceState(isRunning) {
    if (dom.runAllButton) dom.runAllButton.disabled = isRunning;
    if (dom.runCustomSequenceButton) dom.runCustomSequenceButton.disabled = isRunning || getSelectedStepsOrder().length === 0;
    if (dom.clearCustomSequenceButton) dom.clearCustomSequenceButton.disabled = isRunning || getSelectedStepsOrder().length === 0;

    dom.customSequenceCheckboxes.forEach(cb => cb.disabled = isRunning);

    Object.keys(STEPS_CONFIG_FROM_SERVER).forEach(stepKeyConfig => {
        const runButton = document.querySelector(`.run-button[data-step="${stepKeyConfig}"]`);
        const cancelButton = document.querySelector(`.cancel-button[data-step="${stepKeyConfig}"]`);
        const stepInfo = getProcessInfo(stepKeyConfig);

        if (runButton) runButton.disabled = isRunning;

        if (cancelButton) {
            if (stepInfo && ['running', 'starting', 'initiated'].includes(stepInfo.status)) {
                cancelButton.disabled = false;
            } else {
                cancelButton.disabled = true;
            }
        }
    });
}

export function setActiveStepForLogPanelUI(stepKey) {
    console.log(`[UI] setActiveStepForLogPanelUI, new active step for logs: ${stepKey}`);
    setActiveStepKeyForLogs(stepKey);

    const allStepDivs = dom.getAllStepDivs();
    allStepDivs.forEach(s => {
        s.classList.remove('active-for-log-panel');
    });
    if (stepKey && stepKey !== 'clear_disk_cache') {
        const activeStepElement = document.getElementById(`step-${stepKey}`);
        if (activeStepElement) {
            activeStepElement.classList.add('active-for-log-panel');

            const logsOpen = dom.workflowWrapper && dom.workflowWrapper.classList.contains('logs-active');
            if (logsOpen) {
                hideNonActiveSteps(stepKey, true);
            }
            if (isAutoScrollEnabled() && !logsOpen) {
                console.log(`[UI] Auto-scrolling to active step: ${stepKey}`);
                scrollToActiveStep(stepKey);
            }
        }
    }

    clearLogPanelSpecificButtons();

    if (stepKey) {
        const config = getStepsConfig();
        const stepConfig = config ? config[stepKey] : null;
        const displayName = stepConfig ? stepConfig.display_name : stepKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        console.log(`[UI] setActiveStepForLogPanelUI, displayName for logs: ${displayName}`);

        if(dom.logPanelTitle) dom.logPanelTitle.textContent = `Logs: ${displayName}`;
        if(dom.currentStepLogNamePanel) dom.currentStepLogNamePanel.textContent = displayName;
        updateLogPanelContextUI(stepKey);

        if (stepConfig && stepConfig.specific_logs && stepConfig.specific_logs.length > 0 && dom.logPanelSpecificButtonsContainer) {
            stepConfig.specific_logs.forEach((logConf, index) => {
                const button = document.createElement('button');
                button.className = 'specific-log-button';
                button.textContent = logConf.name;
                button.dataset.step = stepKey;
                button.dataset.logIndex = index;
                button.addEventListener('click', async () => {
                    const apiModule = await import('./apiService.js');
                    await apiModule.fetchSpecificLogAPI(stepKey, index, logConf.name);
                });
                dom.logPanelSpecificButtonsContainer.appendChild(button);
            });
        }
    } else {
        if(dom.logPanelTitle) dom.logPanelTitle.textContent = "Logs";
        if(dom.currentStepLogNamePanel) dom.currentStepLogNamePanel.textContent = "Aucune étape active";
        updateLogPanelContextUI(null);
    }
}

async function fetchAndDisplayLogsForPanel(stepKeyToFocus) {
    console.log(`[UI] fetchAndDisplayLogsForPanel called for: ${stepKeyToFocus}. Current active log panel: ${getActiveStepKeyForLogs()}`);
    if (!stepKeyToFocus) return;

    const stepConfig = getStepsConfig()[stepKeyToFocus];
    const displayName = stepConfig ? (stepConfig.display_name || stepKeyToFocus) : stepKeyToFocus;

    if (dom.mainLogOutputPanel) {
        dom.mainLogOutputPanel.textContent = `Chargement des logs pour ${displayName}...`;
    }

    if(dom.mainLogContainerPanel) dom.mainLogContainerPanel.style.display = 'flex';
    if(dom.specificLogContainerPanel) dom.specificLogContainerPanel.style.display = 'none';

    try {
        const response = await fetch(`/status/${stepKeyToFocus}`);
        if (!response.ok) {
            console.error(`[UI] fetchAndDisplayLogsForPanel - fetch failed for ${stepKeyToFocus}: ${response.status}`);
            throw new Error(`Erreur ${response.status} lors de la récupération des logs pour ${displayName}`);
        }
        const data = await response.json();
        setProcessInfo(stepKeyToFocus, { ...(getProcessInfo(stepKeyToFocus) || {}), ...data });
        console.log(`[UI] fetchAndDisplayLogsForPanel - response for: ${stepKeyToFocus}, Log content length: ${data.log ? data.log.length : 'N/A'}`);

        if (getActiveStepKeyForLogs() === stepKeyToFocus) {
            console.log(`[UI] fetchAndDisplayLogsForPanel - Updating main log for ${stepKeyToFocus} with ${data.log ? data.log.length : 0} lines.`);
            updateMainLogOutputUI(data.log.join(''));
        } else {
            console.log(`[UI] fetchAndDisplayLogsForPanel - Log focus changed. Current: ${getActiveStepKeyForLogs()}, Fetched for: ${stepKeyToFocus}. Not updating main log panel.`);
        }
    } catch (error) {
        console.error(`[UI] fetchAndDisplayLogsForPanel - CATCH error for ${stepKeyToFocus}:`, error);
        if (getActiveStepKeyForLogs() === stepKeyToFocus && dom.mainLogOutputPanel) {
            dom.mainLogOutputPanel.textContent = `Erreur: ${error?.message || 'Erreur inconnue'}`;
        }
    }
}

export function openLogPanelUI(stepKeyToFocus, forceOpen = false) {
    const currentActiveLogStep = getActiveStepKeyForLogs();
    const isPanelOpen = dom.workflowWrapper.classList.contains('logs-active');
    console.log(`[UI] openLogPanelUI called for: ${stepKeyToFocus}, forceOpen: ${forceOpen}, currentActive: ${currentActiveLogStep}, isPanelOpen: ${isPanelOpen}`);

    if (forceOpen) {
        console.log(`[UI] Forcing panel open/update for ${stepKeyToFocus}`);
        dom.workflowWrapper.classList.add('logs-entering');
        setActiveStepForLogPanelUI(stepKeyToFocus);
        hideNonActiveSteps(stepKeyToFocus, true);
        requestAnimationFrame(() => {
            dom.workflowWrapper.classList.add('logs-active');
            onWrapperTransitionEndOnce(() => {
                dom.workflowWrapper.classList.remove('logs-entering');
            }, 500);
        });
        positionLogsPanelNearActiveStep(stepKeyToFocus);
        fetchAndDisplayLogsForPanel(stepKeyToFocus);
        return;
    }

    if (isPanelOpen && currentActiveLogStep && currentActiveLogStep !== stepKeyToFocus) {
        console.log(`[UI] Log panel already open for ${currentActiveLogStep}, switching to ${stepKeyToFocus}.`);
        setActiveStepForLogPanelUI(stepKeyToFocus);
        hideNonActiveSteps(stepKeyToFocus, true);
        positionLogsPanelNearActiveStep(stepKeyToFocus);
        fetchAndDisplayLogsForPanel(stepKeyToFocus);
        return;
    }

    if (isPanelOpen && currentActiveLogStep === stepKeyToFocus) {
        console.log(`[UI] Panel already open for ${stepKeyToFocus}. Refreshing its content.`);
        fetchAndDisplayLogsForPanel(stepKeyToFocus);
        return;
    }

    console.log(`[UI] Opening panel for ${stepKeyToFocus} (or was closed/open for null).`);
    dom.workflowWrapper.classList.add('logs-entering');
    setActiveStepForLogPanelUI(stepKeyToFocus);
    hideNonActiveSteps(stepKeyToFocus, true);
    requestAnimationFrame(() => {
        dom.workflowWrapper.classList.add('logs-active');
        onWrapperTransitionEndOnce(() => {
            dom.workflowWrapper.classList.remove('logs-entering');
        }, 500);
    });
    positionLogsPanelNearActiveStep(stepKeyToFocus);
    fetchAndDisplayLogsForPanel(stepKeyToFocus);
}

export function closeLogPanelUI() {
    console.log('[CLOSE_LOG] Starting closeLogPanelUI, current classes:', dom.workflowWrapper.className);
    dom.workflowWrapper.classList.add('logs-leaving');
    console.log('[CLOSE_LOG] Added logs-leaving class, new classes:', dom.workflowWrapper.className);

    requestAnimationFrame(() => {
        console.log('[CLOSE_LOG] In RAF, removing logs-active class, current classes:', dom.workflowWrapper.className);
        dom.workflowWrapper.classList.remove('logs-active');

        onWrapperTransitionEndOnce(() => {
            console.log('[CLOSE_LOG] Cleanup - removing logs-leaving class, current classes:', dom.workflowWrapper.className);
            dom.workflowWrapper.classList.remove('logs-leaving');
            hideNonActiveSteps(null, false);
        }, 500);
    });

    setActiveStepForLogPanelUI(null);
    if(dom.mainLogOutputPanel) dom.mainLogOutputPanel.textContent = "";
    if(dom.specificLogContainerPanel) dom.specificLogContainerPanel.style.display = 'none';

    if (dom.logsColumnGlobal) {
        dom.logsColumnGlobal.style.removeProperty('top');
        dom.logsColumnGlobal.style.removeProperty('height');
    }
    clearLogPanelSpecificButtons();
}

export function updateStepCardUI(stepKey, data) {
    console.group(`[PROGRESS DEBUG] updateStepCardUI - ${stepKey}`);
    console.log('Raw data received:', {
        progress_current: data.progress_current,
        progress_total: data.progress_total,
        progress_current_fractional: data.progress_current_fractional,
        status: data.status,
        progress_text: data.progress_text,
        timestamp: new Date().toISOString()
    });

    performanceOptimizer.measureDomUpdate(`updateStepCard-${stepKey}`, () => {
        try {
            const statusEl = document.getElementById(`status-${stepKey}`);
            const runButton = document.querySelector(`.run-button[data-step="${stepKey}"]`);
            const cancelButton = document.querySelector(`.cancel-button[data-step="${stepKey}"]`);

            const normalizedStatus = normalizeStatus(data.status || 'idle');
            const statusMeta = getStatusMeta(normalizedStatus);

            if (statusEl) {
                statusEl.textContent = statusMeta.label;
                statusEl.className = `status-badge ${statusMeta.badgeClass}`;
            }

            const stepCardEl = document.getElementById(`step-${stepKey}`);
            if (stepCardEl) {
                stepCardEl.setAttribute('data-status', normalizedStatus);
            }

            updateStepStateChip(stepKey, normalizedStatus);

            if (runButton && cancelButton) {
                const isCurrentlyRunningOrStarting = ['running', 'starting', 'initiated'].includes(normalizedStatus);
                runButton.disabled = isCurrentlyRunningOrStarting || getIsAnySequenceRunning();
                cancelButton.disabled = !isCurrentlyRunningOrStarting;
            }

            const logsOpen = dom.workflowWrapper && dom.workflowWrapper.classList.contains('logs-active');
            if (logsOpen && ['running', 'starting', 'initiated'].includes(normalizedStatus)) {
                if (getActiveStepKeyForLogs() !== stepKey) {
                    setActiveStepForLogPanelUI(stepKey);
                    hideNonActiveSteps(stepKey, true);
                }
            }

            if (logsOpen && getActiveStepKeyForLogs() === stepKey) {
                updateLogPanelContextUI(stepKey);
            }

            if (['completed', 'failed'].includes(normalizedStatus) || (normalizedStatus === 'idle' && getStepTimer(stepKey))) {
                stopStepTimer(stepKey);
            } else if (normalizedStatus === 'idle' && !getStepTimer(stepKey)) {
                resetStepTimerDisplay(stepKey);
            } else if (['running', 'starting', 'initiated'].includes(normalizedStatus) && !getStepTimer(stepKey)?.intervalId) {
                // TODO: Implement proper timer resumption after page reload
                // Date: 2026-01-19
                // Owner: kidpixel
                // Issue: startStepTimer doesn't resume from existing startTime
                // Solution needed: Backend should provide duration_str for running steps
            }

            const progressContainer = document.getElementById(`progress-container-${stepKey}`);
            const progressBar = document.getElementById(`progress-bar-${stepKey}`);
            const progressTextEl = document.getElementById(`progress-text-${stepKey}`);

            let percentage = 0;

            if (progressContainer && progressBar && progressTextEl) {
                if (data.progress_total > 0) {
                    let currentProgress = data.progress_current_fractional || data.progress_current;

                    if (data.progress_current_fractional === null && data.progress_text) {
                        const isSpecialRunning = (['STEP3','STEP4','STEP5'].includes(stepKey)) && ['running','starting','initiated'].includes(normalizedStatus);
                        if (!isSpecialRunning) {
                            const percentMatch = data.progress_text.match(/(\d+)%/);
                            if (percentMatch) {
                                const textPercent = parseInt(percentMatch[1]);
                                currentProgress = (textPercent / 100) * data.progress_total;
                                console.log(`[PROGRESS FALLBACK] ${stepKey}: Extracted ${textPercent}% from text, using fractional: ${currentProgress}`);
                            }
                        }
                    }

                    percentage = Math.round((currentProgress / data.progress_total) * 100);
                    percentage = Math.min(percentage, 100);

                    if ((['STEP3','STEP4','STEP5'].includes(stepKey)) && ['running', 'starting', 'initiated'].includes(normalizedStatus)) {
                        if (percentage >= 100) {
                            percentage = 99;
                        }
                        if (data.progress_total > 0 && data.progress_current === data.progress_total) {
                            percentage = Math.min(percentage, 99);
                        }
                    }

                    console.log(`[PROGRESS CALC] ${stepKey}:`, {
                        progress_current: data.progress_current,
                        progress_current_fractional: data.progress_current_fractional,
                        progress_total: data.progress_total,
                        currentProgress: currentProgress,
                        calculatedPercentage: (currentProgress / data.progress_total) * 100,
                        finalPercentage: percentage,
                        status: data.status,
                        progress_text: data.progress_text
                    });

                    let displayCurrent = data.progress_current;
                    if ((!displayCurrent || displayCurrent === 0) && typeof data.progress_current_fractional === 'number' && data.progress_current_fractional > 0) {
                        const frac = Math.max(0, Math.min(data.progress_total, data.progress_current_fractional));
                        displayCurrent = Math.min(data.progress_total, Math.floor(frac) + 1);
                    }

                    progressContainer.style.display = 'block';
                    progressBar.style.backgroundColor = 'var(--blue)';
                    progressBar.style.width = `${percentage}%`;
                    progressBar.textContent = `${percentage}%`;
                    progressBar.setAttribute('aria-valuenow', percentage);

                    if (['running','starting','initiated'].includes(normalizedStatus)) {
                        progressBar.setAttribute('data-active', 'true');
                    } else {
                        progressBar.removeAttribute('data-active');
                    }

                    const candidateText = (data.progress_text && data.progress_text.trim()) ? data.progress_text : (lastProgressTextByStep[stepKey] || '');
                    if (data.progress_text && data.progress_text.trim()) {
                        lastProgressTextByStep[stepKey] = data.progress_text;
                    }
                    const subText = candidateText ? `${candidateText} (${displayCurrent}/${data.progress_total})` : `${displayCurrent}/${data.progress_total}`;
                    progressTextEl.textContent = subText;

                    const shouldAutoCenter = getIsAnySequenceRunning() && ['running', 'starting', 'initiated'].includes(normalizedStatus);
                    if (shouldAutoCenter) {
                        const logsOpenNow = dom.workflowWrapper && dom.workflowWrapper.classList.contains('logs-active');
                        if (!logsOpenNow) {
                            const now = performance.now();
                            const lastTs = _lastAutoCenterTsByStep[stepKey] || 0;
                            if ((now - lastTs) > _AUTO_CENTER_THROTTLE_MS) {
                                _lastAutoCenterTsByStep[stepKey] = now;
                                requestAnimationFrame(() => {
                                    scrollToActiveStep(stepKey, { behavior: 'auto', scrollDelay: 0 });
                                });
                            }
                        }
                    }

                    if (candidateText && ['running','starting','initiated'].includes(data.status)) {
                        progressTextEl.setAttribute('data-processing', 'true');
                    } else {
                        progressTextEl.removeAttribute('data-processing');
                    }

                    if (['STEP3','STEP4','STEP5'].includes(stepKey)) {
                        const stepNames = { STEP3: 'Étape 3 — Transitions', STEP4: 'Étape 4 — Audio', STEP5: 'Étape 5 — Tracking' };
                        try { updateGlobalProgressUI(`${stepNames[stepKey] || stepKey}: ${subText}`, percentage, false); } catch (_) {}
                    }
                } else if (data.status === 'completed' && data.progress_total === 0) {
                    percentage = 0;
                    console.log(`[PROGRESS CALC] ${stepKey}: Completed with no work (0%)`);
                } else if (data.status === 'completed' && data.progress_total > 0) {
                    percentage = 100;
                    console.log(`[PROGRESS CALC] ${stepKey}: Completed with work (100%)`);
                } else if (['running', 'starting', 'initiated'].includes(data.status) && data.progress_total === 0) {
                    percentage = 0;
                    console.log(`[PROGRESS CALC] ${stepKey}: Running with no progress tracking (0%)`);
                }
            } else if (['running', 'starting', 'initiated'].includes(data.status) && data.progress_total === 0) {
                progressContainer.style.display = 'block';
                progressBar.style.backgroundColor = 'var(--blue)';
                progressBar.setAttribute('data-active', 'true');
                const runningText = (data.progress_text && data.progress_text.trim()) ? data.progress_text : (lastProgressTextByStep[stepKey] || "En cours d'exécution...");
                if (data.progress_text && data.progress_text.trim()) lastProgressTextByStep[stepKey] = data.progress_text;
                progressTextEl.textContent = runningText;

                if (['STEP3','STEP4','STEP5'].includes(stepKey)) {
                    const stepNames = { STEP3: 'Étape 3 — Transitions', STEP4: 'Étape 4 — Audio', STEP5: 'Étape 5 — Tracking' };
                    const globalText = `${stepNames[stepKey] || stepKey}: ${runningText || 'En cours...'}`;
                    try { updateGlobalProgressUI(globalText, 0, false); } catch (_) {}
                }

                if (runningText && runningText.trim()) {
                    progressTextEl.setAttribute('data-processing', 'true');
                } else {
                    progressTextEl.removeAttribute('data-processing');
                }
            } else if (data.status === 'completed') {
                progressContainer.style.display = 'block';
                progressBar.style.backgroundColor = 'var(--green)';
                progressBar.removeAttribute('data-active');

                if (data.progress_total === 0) {
                    let noWorkText = "Aucun élément à traiter";
                    if (data.progress_text && data.progress_text.trim() !== "") {
                        noWorkText = data.progress_text;
                    }
                    progressTextEl.textContent = noWorkText;
                    progressBar.style.width = '10%';
                    progressBar.textContent = '✓';
                } else {
                    let baseCompletionText = `Terminé (${data.progress_current}/${data.progress_total})`;
                    if (data.progress_text && data.progress_text.toLowerCase() !== "terminé" && data.progress_text.trim() !== "") {
                        baseCompletionText = `${data.progress_text} (${data.progress_current}/${data.progress_total})`;
                    }
                    const config = STEPS_CONFIG_FROM_SERVER[stepKey];
                    if (config && config.post_completion_message_ui) {
                        progressTextEl.textContent = `${baseCompletionText}\n${config.post_completion_message_ui}`;
                    } else {
                        progressTextEl.textContent = baseCompletionText;
                    }

                    if (['STEP3','STEP4','STEP5'].includes(stepKey)) {
                        const stepNames = { STEP3: 'Étape 3 — Transitions', STEP4: 'Étape 4 — Audio', STEP5: 'Étape 5 — Tracking' };
                        try { updateGlobalProgressUI(`${stepNames[stepKey] || stepKey}: Terminé`, 100, false); } catch (_) {}
                    }
                    delete lastProgressTextByStep[stepKey];
                }
            } else if (data.status === 'failed') {
                progressContainer.style.display = 'block';
                progressBar.style.backgroundColor = 'var(--red)';
                let failureText = `Échec`;
                if (data.progress_total > 0) failureText += ` à ${data.progress_current}/${data.progress_total}`;
                if (data.progress_text) failureText += `: ${data.progress_text}`;
                progressTextEl.textContent = failureText;
                progressBar.removeAttribute('data-active');
                progressTextEl.removeAttribute('data-processing');

                if (['STEP3','STEP4','STEP5'].includes(stepKey)) {
                    const stepNames = { STEP3: 'Étape 3 — Transitions', STEP4: 'Étape 4 — Audio', STEP5: 'Étape 5 — Tracking' };
                    try { updateGlobalProgressUI(`${stepNames[stepKey] || stepKey}: ${failureText}`, percentage, true); } catch (_) {}
                }
                delete lastProgressTextByStep[stepKey];
            } else if (data.status === 'starting' || data.status === 'initiated') {
                progressContainer.style.display = 'block';
                progressBar.style.width = `0%`;
                progressBar.textContent = `0%`;
                progressBar.style.backgroundColor = 'var(--blue)';
                progressBar.setAttribute('data-active', 'true');
                progressTextEl.textContent = "Démarrage...";
            } else {
                progressContainer.style.display = 'none';
                progressBar.setAttribute('aria-valuenow', 0);
            }

            const anyRunning = !!document.querySelector('.step[data-status="running"], .step[data-status="starting"], .step[data-status="initiated"]');
            if (dom.workflowWrapper) {
                if (anyRunning) {
                    dom.workflowWrapper.classList.add('any-step-running');
                    if (['running','starting','initiated'].includes(data.status)) {
                        dom.workflowWrapper.setAttribute('data-active-step', stepKey);
                    } else if (!document.querySelector(`.step[data-status="running"], .step[data-status="starting"], .step[data-status="initiated"]`)) {
                        dom.workflowWrapper.removeAttribute('data-active-step');
                    }
                } else {
                    dom.workflowWrapper.classList.remove('any-step-running');
                    dom.workflowWrapper.removeAttribute('data-active-step');
                }
            }

            try {
                if (!_stepDetailsPanelModulePromise) {
                    _stepDetailsPanelModulePromise = import('./stepDetailsPanel.js');
                }
                _stepDetailsPanelModulePromise
                    .then((mod) => {
                        if (mod && typeof mod.refreshStepDetailsPanelIfOpen === 'function') {
                            mod.refreshStepDetailsPanelIfOpen(stepKey);
                        }
                    })
                    .catch((e) => {
                        console.debug('[UI] Step details module not available:', e);
                    });
            } catch (_) {}
        } catch (_) {}

        console.groupEnd();
    });
}

export function updateCustomSequenceButtonsUI() {
    const hasSelection = getSelectedStepsOrder().length > 0;
    if (dom.runCustomSequenceButton) dom.runCustomSequenceButton.disabled = !hasSelection || getIsAnySequenceRunning();
    if (dom.clearCustomSequenceButton) dom.clearCustomSequenceButton.disabled = !hasSelection || getIsAnySequenceRunning();
}

export function updateGlobalProgressUI(text, percentage, isError = false) {
    if(dom.globalProgressAffix) dom.globalProgressAffix.style.display = 'flex';
    if(dom.globalProgressContainer) dom.globalProgressContainer.style.display = 'block';
    if(dom.globalProgressText) {
        dom.globalProgressText.style.display = 'block';
        dom.globalProgressText.textContent = text;
        dom.globalProgressText.style.color = isError ? 'var(--red)' : 'var(--text-secondary)';
    }
    if(dom.globalProgressBar) {
        dom.globalProgressBar.style.width = `${percentage}%`;
        dom.globalProgressBar.textContent = `${percentage}%`;
        dom.globalProgressBar.setAttribute('aria-valuenow', percentage);
        dom.globalProgressBar.style.backgroundColor = isError ? 'var(--red)' : 'var(--green)';
    }
}

export function updateSpecificLogUI(logName, path, content, isError = false, errorMessage = '') {
    domBatcher.scheduleUpdate('specific-log-ui', () => {
        if(dom.specificLogHeaderTextPanel) dom.specificLogHeaderTextPanel.textContent = isError ? `Erreur chargement "${logName}"` : `Log Spécifique: "${logName}"`;
        if(dom.specificLogPathInfoPanel) dom.specificLogPathInfoPanel.textContent = path ? `(Source: ${path})` : "";
        if (isError) {
            if(dom.specificLogOutputContentPanel) {
                const escapedErrorMessage = DOMUpdateUtils.escapeHtml(errorMessage);
                dom.specificLogOutputContentPanel.innerHTML = `<span class="log-line log-error">${escapedErrorMessage}</span>`;
            }
        } else {
const styledContent = parseAndStyleLogContent(content);
            if(dom.specificLogOutputContentPanel) dom.specificLogOutputContentPanel.innerHTML = styledContent;
        }
        if(dom.specificLogContainerPanel) dom.specificLogContainerPanel.style.display = 'flex';
        if(dom.mainLogContainerPanel) dom.mainLogContainerPanel.style.display = 'none';
        if(dom.specificLogOutputContentPanel) dom.specificLogOutputContentPanel.scrollTop = 0;
    });
}

const _LOG_LINE_EMPTY_OR_WHITESPACE_PATTERN = /^\s*$/;

const _LOG_TIMESTAMP_PATTERN = /^(?:\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2})/;
const _LOG_ERROR_PATTERN = /(?:erreur|error|échec|failed|exception|critical|fatal|crash)/i;
const _LOG_WARNING_PATTERN = /(?:warning|attention|avertissement|warn|caution|deprecated)/i;
const _LOG_SUCCESS_PATTERN = /(?:success|réussi|terminé|completed|finished|done|✓|✔|ok\b)/i;
const _LOG_INFO_PATTERN = /(?:info|information|démarrage|starting|lancement|initiated|status)/i;
const _LOG_DEBUG_PATTERN = /(?:debug|trace|verbose|détail)/i;
const _LOG_COMMAND_PATTERN = /^(?:commande:|command:|executing:|exécution:|\$|>)/i;
const _LOG_PROGRESS_PATTERN = /(?:\d+%|\d+\/\d+|progress|progression|chargement|loading|téléchargement|downloading)/i;

const _LOG_PATTERNS = [
    {
        regex: _LOG_ERROR_PATTERN,
        type: 'error'
    },
    {
        regex: _LOG_WARNING_PATTERN,
        type: 'warning'
    },
    {
        regex: _LOG_SUCCESS_PATTERN,
        type: 'success'
    },
    {
        regex: _LOG_PROGRESS_PATTERN,
        type: 'progress'
    },
    {
        regex: _LOG_COMMAND_PATTERN,
        type: 'command'
    },
    {
        regex: _LOG_INFO_PATTERN,
        type: 'info'
    },
    {
        regex: _LOG_TIMESTAMP_PATTERN,
        type: 'info'
    },
    {
        regex: _LOG_DEBUG_PATTERN,
        type: 'debug'
    }
];

const _COMPILED_LOG_PATTERNS = _LOG_PATTERNS.map(p => ({
    ...p,
    regex: new RegExp(p.regex.source, p.regex.flags)
}));

/**
 * Parse and style log content with CSS classes for different log types.
 * Escapes all HTML to prevent XSS.
 * 
 * @param {string} rawContent - Raw log content
 * @returns {string} - Styled HTML content
 */
export function parseAndStyleLogContent(rawContent) {
    if (!rawContent || typeof rawContent !== 'string') {
        return rawContent || '';
    }

const lines = rawContent.split('\n');
    const styledLines = new Array(lines.length);

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line === '' || _LOG_LINE_EMPTY_OR_WHITESPACE_PATTERN.test(line)) {
            styledLines[i] = line;
            continue;
        }

        const escapedLine = DOMUpdateUtils.escapeHtml(line);

        let logType = 'default';
        for (let j = 0; j < _COMPILED_LOG_PATTERNS.length; j++) {
            const pattern = _COMPILED_LOG_PATTERNS[j];
            if (pattern.regex.test(line)) {
                logType = pattern.type;
                break;
            }
        }

        styledLines[i] = logType !== 'default'
            ? `<span class="log-line log-${logType}">${escapedLine}</span>`
            : escapedLine;
    }

    return styledLines.join('\n');
}

export function updateMainLogOutputUI(htmlContent) {
    if(dom.mainLogOutputPanel) {
const styledContent = parseAndStyleLogContent(htmlContent);
        dom.mainLogOutputPanel.innerHTML = styledContent;
    }
    if(dom.mainLogOutputPanel) dom.mainLogOutputPanel.scrollTop = dom.mainLogOutputPanel.scrollHeight;

    if(dom.mainLogContainerPanel) dom.mainLogContainerPanel.style.display = 'flex';
    if(dom.specificLogContainerPanel) dom.specificLogContainerPanel.style.display = 'none';
}

export function updateLocalDownloadsListUI(downloadsData) {
    if (!dom.getLocalDownloadsList()) return;
    dom.getLocalDownloadsList().innerHTML = '';
    if (!downloadsData || downloadsData.length === 0) {
        const li = document.createElement('li');
        li.textContent = 'Aucune activité de téléchargement locale récente.';
        li.classList.add('placeholder');
        dom.getLocalDownloadsList().appendChild(li);
        return;
    }

const currentDownloadIds = new Set();
    downloadsData.forEach(download => {
        if (download.id) {
            currentDownloadIds.add(download.id);
if (!previousDownloadIds.has(download.id) &&
                (download.status === 'pending' || download.status === 'downloading')) {
                console.log(`[SOUND] New CSV download detected: ${download.filename}`);
                soundEvents.csvDownloadInitiation();

const filename = download.filename && download.filename !== 'Détermination en cours...'
                    ? download.filename.substring(0, 30) + (download.filename.length > 30 ? '...' : '')
                    : 'nouveau fichier';
                showNotification(`Mode Auto: Téléchargement démarré - ${filename}`, "info", 5000);
            }
        }
    });

previousDownloadIds = currentDownloadIds;

    downloadsData.forEach(download => {
        const li = document.createElement('li');
        li.classList.add(`download-status-${download.status}`);

        const escapedOriginalUrl = DOMUpdateUtils.escapeHtml(download.original_url || '');
        const escapedFilename = DOMUpdateUtils.escapeHtml(download.filename || 'Nom inconnu');
        const escapedStatus = DOMUpdateUtils.escapeHtml(download.status || '');
        const escapedDisplayTimestamp = DOMUpdateUtils.escapeHtml(download.display_timestamp || 'N/A');

        const timestampSpan = `<span class="timestamp">${escapedDisplayTimestamp}</span>`;
        const filenameSpan = `<span class="filename" title="${escapedOriginalUrl}">${escapedFilename}</span>`;
        let statusText = `Statut: <span class="status-text">${escapedStatus}</span>`;
        let progressText = '';
        if (download.status === 'downloading' && typeof download.progress === 'number') {
            progressText = ` <span class="progress-percentage">(${download.progress}%)</span>`;
        }
        if (download.message) {
            const escapedMessage = DOMUpdateUtils.escapeHtml(download.message);
            const messagePreview = escapedMessage.substring(0, 50) + (escapedMessage.length > 50 ? '...' : '');
            statusText += ` <span class="message" title="${escapedMessage}">${messagePreview}</span>`;
        }
        li.innerHTML = `${timestampSpan} - ${filenameSpan} - ${statusText}${progressText}`;
        dom.getLocalDownloadsList().appendChild(li);
    });
}

export function updateClearCacheGlobalButtonState(status, message = '') {
    if (!dom.clearCacheGlobalButton) return;

    dom.clearCacheGlobalButton.classList.remove('idle', 'running', 'completed', 'failed');
    const textSpan = dom.clearCacheGlobalButton.querySelector('.button-text');
    const currentStepInfo = getProcessInfo('clear_disk_cache');

const isOtherSequenceRunning = getIsAnySequenceRunning() && currentStepInfo?.status !== 'running';


    switch (status) {
        case 'idle':
            dom.clearCacheGlobalButton.disabled = isOtherSequenceRunning;
            if (textSpan) textSpan.textContent = "Vider le Cache";
            dom.clearCacheGlobalButton.classList.add('idle');
            break;
        case 'starting':
        case 'initiated':
            dom.clearCacheGlobalButton.disabled = true;
            if (textSpan) textSpan.textContent = "Lancement...";
            dom.clearCacheGlobalButton.classList.add('running');
            break;
        case 'running':
            dom.clearCacheGlobalButton.disabled = true;
            if (textSpan) textSpan.textContent = "Nettoyage...";
            dom.clearCacheGlobalButton.classList.add('running');
            break;
        case 'completed':
            dom.clearCacheGlobalButton.disabled = isOtherSequenceRunning;
            if (textSpan) textSpan.textContent = "Cache Vidé";
            dom.clearCacheGlobalButton.classList.add('completed');
            showNotification("Nettoyage du cache disque terminé avec succès.", "success");
            setTimeout(() => updateClearCacheGlobalButtonState('idle'), 5000);
            break;
        case 'failed':
            dom.clearCacheGlobalButton.disabled = isOtherSequenceRunning;
            if (textSpan) textSpan.textContent = "Échec Nettoyage";
            dom.clearCacheGlobalButton.classList.add('failed');
            let notifMessage = "Échec du nettoyage du cache disque.";
            if (message && typeof message === 'string' && message.trim() !== '' && !message.startsWith('<')) {
                notifMessage += ` Détail: ${message.substring(0,100)}`;
            }
            showNotification(notifMessage, "error");
            setTimeout(() => updateClearCacheGlobalButtonState('idle'), 8000);
            break;
        default:
            dom.clearCacheGlobalButton.disabled = isOtherSequenceRunning;
            if (textSpan) textSpan.textContent = "Vider le Cache";
            dom.clearCacheGlobalButton.classList.add('idle');
    }
}
