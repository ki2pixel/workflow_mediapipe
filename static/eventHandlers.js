import * as dom from './domElements.js';
import * as ui from './uiUpdater.js';
import * as api from './apiService.js';
import { runStepSequence } from './sequenceManager.js';
import { defaultSequenceableStepsKeys } from './constants.js';
import { showNotification } from './utils.js';
import { openPopupUI, closePopupUI, showCustomSequenceConfirmUI } from './popupManager.js';
import { scrollToStepImmediate } from './scrollManager.js';
import { soundEvents } from './soundManager.js';
import { appState } from './state/AppState.js';
import { setAutoOpenLogOverlay, getAutoOpenLogOverlay } from './state.js';

function getIsAnySequenceRunning() {
    return !!appState.getStateProperty('isAnySequenceRunning');
}

function getSelectedStepsOrder() {
    return appState.getStateProperty('selectedStepsOrder') || [];
}

function setSelectedStepsOrder(order) {
    const safeOrder = Array.isArray(order) ? [...order] : [];
    appState.setState({ selectedStepsOrder: safeOrder }, 'selected_steps_order_update');
}

function resolveElement(getterFn, legacyValue = null) {
    if (typeof getterFn === 'function') {
        try {
            return getterFn();
        } catch (_) {
            return legacyValue;
        }
    }
    return legacyValue;
}

function resolveCollection(getterFn, legacyValue = null) {
    const resolved = resolveElement(getterFn, legacyValue);
    if (!resolved) return [];
    return Array.from(resolved);
}

export function initializeEventHandlers() {
    const closeLogButton = resolveElement(dom.getCloseLogPanelButton, dom.closeLogPanelButton);
    if (closeLogButton) {
        closeLogButton.addEventListener('click', ui.closeLogPanelUI);
    }

    const runButtons = resolveCollection(dom.getAllRunButtons, dom.allRunButtons);
    runButtons.forEach(button => {
        button.addEventListener('click', async () => {
            try {
                if (getIsAnySequenceRunning()) {
                    showNotification("Une séquence est déjà en cours. Veuillez attendre sa fin.", 'warning');
                    return;
                }
                const stepKey = button.dataset.step;
                ui.updateMainLogOutputUI('');
                const specificLogContainer = resolveElement(dom.getSpecificLogContainerPanel, dom.specificLogContainerPanel);
                if (specificLogContainer) specificLogContainer.style.display = 'none';
                if (getAutoOpenLogOverlay()) {
                    ui.openLogPanelUI(stepKey, true);
                }

                scrollToStepImmediate(stepKey, { scrollDelay: 0 });

                soundEvents.workflowStart();

                await api.runStepAPI(stepKey);
            } catch (error) {
                console.error('[EVENT] Error in run button handler:', error);
                showNotification("Erreur lors de l'exécution de l'étape", 'error');
            }
        });
    });

    const cancelButtons = resolveCollection(dom.getAllCancelButtons, dom.allCancelButtons);
    cancelButtons.forEach(button => {
        button.addEventListener('click', async () => {
            try {
                const stepKey = button.dataset.step;
                await api.cancelStepAPI(stepKey);
            } catch (error) {
                console.error('[EVENT] Error in cancel button handler:', error);
                showNotification("Erreur lors de l'annulation de l'étape", 'error');
            }
        });
    });

    const logsAutoOpenToggle = resolveElement(dom.getLogsAutoOpenToggle, dom.logsAutoOpenToggle);
    if (logsAutoOpenToggle) {
        const savedPreference = localStorage.getItem('autoOpenLogOverlay');
        const initialValue = savedPreference === null ? getAutoOpenLogOverlay() : savedPreference === 'true';
        logsAutoOpenToggle.checked = initialValue;
        setAutoOpenLogOverlay(initialValue);
        logsAutoOpenToggle.addEventListener('change', (event) => {
            const enabled = event.target.checked;
            localStorage.setItem('autoOpenLogOverlay', enabled.toString());
            setAutoOpenLogOverlay(enabled);
            console.log(`[EVENT] Auto log overlay ${enabled ? 'enabled' : 'disabled'} by user`);
        });
    }

    const specificLogButtons = resolveCollection(dom.getAllSpecificLogButtons, dom.allSpecificLogButtons);
    specificLogButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const stepKey = button.dataset.step;
            const logIndex = button.dataset.logIndex;
            const workflowWrapper = resolveElement(dom.getWorkflowWrapper, dom.workflowWrapper);

            if (!workflowWrapper || !workflowWrapper.classList.contains('logs-active') || appState.getStateProperty('activeStepKeyForLogsPanel') !== stepKey) {
                ui.openLogPanelUI(stepKey, true);
                try {
                    const statusResponse = await fetch(`/status/${stepKey}`);
                    if (!statusResponse.ok) throw new Error(`Erreur statut: ${statusResponse.status}`);
                    const statusData = await statusResponse.json();
                    ui.updateMainLogOutputUI(statusData.log ? statusData.log.join('') : '<i>Log principal non disponible.</i>');
                } catch (error) {
                    console.error("Erreur chargement statut pour log panel:", error);
                    ui.updateMainLogOutputUI(`<i>Erreur chargement log principal: ${error.message}</i>`);
                }
            }
            // Pass the clicked button to enable loading state (spinner + disabled)
            await api.fetchSpecificLogAPI(stepKey, logIndex, button.textContent.trim(), button);
        });
    });

    const runAllButton = resolveElement(dom.getRunAllButton, dom.runAllButton);
    if (runAllButton) {
        runAllButton.addEventListener('click', async () => {
            if (getIsAnySequenceRunning()) {
                showNotification("Séquence déjà en cours.", 'warning'); return;
            }
            // Play workflow start sound for complete sequence 1-6
            soundEvents.workflowStart();
            await runStepSequence(defaultSequenceableStepsKeys, "Séquence 0-4");
        });
    }

    const customSequenceCheckboxes = resolveCollection(dom.getCustomSequenceCheckboxes, dom.customSequenceCheckboxes);
    customSequenceCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', (event) => {
            const stepKey = event.target.dataset.stepKey;
            const stepCard = document.getElementById(`step-${stepKey}`);
            const orderNumberEl = document.getElementById(`order-${stepKey}`);
            let currentOrder = getSelectedStepsOrder();

            // Play checkbox interaction sound
            soundEvents.checkboxInteraction();

            if (event.target.checked) {
                if (!currentOrder.includes(stepKey)) {
                    currentOrder.push(stepKey);
                    if (stepCard) stepCard.classList.add('custom-sequence-selected');
                }
            } else {
                const index = currentOrder.indexOf(stepKey);
                if (index > -1) currentOrder.splice(index, 1);
                if (stepCard) stepCard.classList.remove('custom-sequence-selected');
            }
            setSelectedStepsOrder(currentOrder);
            document.querySelectorAll('.step-selection-order-number').forEach(el => { el.textContent = ''; });
            getSelectedStepsOrder().forEach((sk, idx) => {
                const orderEl = document.getElementById(`order-${sk}`);
                if (orderEl) orderEl.textContent = idx + 1;
            });
            ui.updateCustomSequenceButtonsUI();
        });
    });

    const clearCustomSequenceButton = resolveElement(dom.getClearCustomSequenceButton, dom.clearCustomSequenceButton);
    if (clearCustomSequenceButton) {
        clearCustomSequenceButton.addEventListener('click', () => {
            setSelectedStepsOrder([]);
            customSequenceCheckboxes.forEach(cb => {
                cb.checked = false;
                const stepCard = document.getElementById(`step-${cb.dataset.stepKey}`);
                if (stepCard) stepCard.classList.remove('custom-sequence-selected');
                const orderEl = document.getElementById(`order-${cb.dataset.stepKey}`);
                if (orderEl) orderEl.textContent = '';
            });
            ui.updateCustomSequenceButtonsUI();
        });
    }

    const runCustomSequenceButton = resolveElement(dom.getRunCustomSequenceButton, dom.runCustomSequenceButton);
    if (runCustomSequenceButton) {
        runCustomSequenceButton.addEventListener('click', () => {
            if (getSelectedStepsOrder().length === 0) {
                showNotification("Veuillez sélectionner au moins une étape.", 'warning');
                return;
            }
            if (getIsAnySequenceRunning()) {
                showNotification("Une autre séquence est déjà en cours.", 'warning'); return;
            }
            showCustomSequenceConfirmUI();
        });
    }

    const confirmRunCustomSequenceButton = resolveElement(dom.getConfirmRunCustomSequenceButton, dom.confirmRunCustomSequenceButton);
    const customSequenceConfirmOverlay = resolveElement(dom.getCustomSequenceConfirmPopupOverlay, dom.customSequenceConfirmPopupOverlay);
    if (confirmRunCustomSequenceButton) {
        confirmRunCustomSequenceButton.addEventListener('click', async () => {
            closePopupUI(customSequenceConfirmOverlay);
            if (getIsAnySequenceRunning()) {
                showNotification("Une autre séquence est déjà en cours.", 'warning'); return;
            }
            // Loading state on confirm button and disable run-custom while executing
            try {
                confirmRunCustomSequenceButton.setAttribute('data-loading', 'true');
                confirmRunCustomSequenceButton.disabled = true;
                if (runCustomSequenceButton) runCustomSequenceButton.disabled = true;

                // Play workflow start sound for custom sequence
                soundEvents.workflowStart();
                await runStepSequence(getSelectedStepsOrder(), "Séquence Personnalisée");
            } finally {
                confirmRunCustomSequenceButton.removeAttribute('data-loading');
                confirmRunCustomSequenceButton.disabled = false;
                if (runCustomSequenceButton) runCustomSequenceButton.disabled = getIsAnySequenceRunning();
            }
        });
    }

    const cancelRunCustomSequenceButton = resolveElement(dom.getCancelRunCustomSequenceButton, dom.cancelRunCustomSequenceButton);
    if (cancelRunCustomSequenceButton) {
        cancelRunCustomSequenceButton.addEventListener('click', () => {
            closePopupUI(customSequenceConfirmOverlay);
        });
    }
    const closeSummaryPopupButton = resolveElement(dom.getCloseSummaryPopupButton, dom.closeSummaryPopupButton);
    const sequenceSummaryOverlay = resolveElement(dom.getSequenceSummaryPopupOverlay, dom.sequenceSummaryPopupOverlay);
    if (closeSummaryPopupButton) {
        closeSummaryPopupButton.addEventListener('click', () => {
            closePopupUI(sequenceSummaryOverlay);
        });
    }

    if (dom.getSoundToggle()) {
        import('./soundManager.js').then(({ isSoundEnabled, setSoundEnabled }) => {
            const isEnabled = isSoundEnabled();
            dom.getSoundToggle().checked = isEnabled;
            if (dom.getSoundStatus()) {
                dom.getSoundStatus().textContent = isEnabled ? 'Activé' : 'Désactivé';
            }

            dom.getSoundToggle().addEventListener('change', (event) => {
                const enabled = event.target.checked;
                setSoundEnabled(enabled);
                if (dom.getSoundStatus()) {
                    dom.getSoundStatus().textContent = enabled ? 'Activé' : 'Désactivé';
                }
                console.log(`[EVENT] Sound effects ${enabled ? 'enabled' : 'disabled'} by user`);
            });
        });
    }
}