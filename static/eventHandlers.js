import * as dom from './domElements.js';
import * as ui from './uiUpdater.js';
import * as api from './apiService.js';
import { runStepSequence } from './sequenceManager.js';
import { defaultSequenceableStepsKeys } from './constants.js';
import { showNotification } from './utils.js';
import { openPopupUI, closePopupUI, showCustomSequenceConfirmUI } from './popupManager.js';
import { scrollToStepImmediate, setAutoScrollEnabled, isAutoScrollEnabled } from './scrollManager.js';
import { soundEvents } from './soundManager.js';
import { appState } from './state/AppState.js';

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

export function initializeEventHandlers() {
    if (dom.closeLogPanelButton) {
        dom.closeLogPanelButton.addEventListener('click', ui.closeLogPanelUI);
    }

    dom.allRunButtons.forEach(button => {
        button.addEventListener('click', async () => {
            try {
                if (getIsAnySequenceRunning()) {
                    showNotification("Une séquence est déjà en cours. Veuillez attendre sa fin.", 'warning');
                    return;
                }
                const stepKey = button.dataset.step;
                ui.updateMainLogOutputUI('');
                dom.specificLogContainerPanel.style.display = 'none';
                ui.openLogPanelUI(stepKey);

                // Scroll to the step immediately when manually triggered
                scrollToStepImmediate(stepKey, { scrollDelay: 0 });

                // Play workflow start sound for individual step execution
                soundEvents.workflowStart();

                await api.runStepAPI(stepKey);
            } catch (error) {
                console.error('[EVENT] Error in run button handler:', error);
                showNotification("Erreur lors de l'exécution de l'étape", 'error');
            }
        });
    });

    dom.allCancelButtons.forEach(button => {
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

    dom.allSpecificLogButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const stepKey = button.dataset.step;
            const logIndex = button.dataset.logIndex;

            if (!dom.workflowWrapper.classList.contains('logs-active') || appState.getStateProperty('activeStepKeyForLogsPanel') !== stepKey) {
                ui.openLogPanelUI(stepKey);
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

    if (dom.runAllButton) {
        dom.runAllButton.addEventListener('click', async () => {
            if (getIsAnySequenceRunning()) {
                showNotification("Séquence déjà en cours.", 'warning'); return;
            }
            // Play workflow start sound for complete sequence 1-6
            soundEvents.workflowStart();
            await runStepSequence(defaultSequenceableStepsKeys, "Séquence 0-4");
        });
    }

    dom.customSequenceCheckboxes.forEach(checkbox => {
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
            document.querySelectorAll('.step-selection-order-number').forEach(el => el.textContent = '');
            getSelectedStepsOrder().forEach((sk, idx) => {
                const orderEl = document.getElementById(`order-${sk}`);
                if (orderEl) orderEl.textContent = idx + 1;
            });
            ui.updateCustomSequenceButtonsUI();
        });
    });

    if (dom.clearCustomSequenceButton) {
        dom.clearCustomSequenceButton.addEventListener('click', () => {
            setSelectedStepsOrder([]);
            dom.customSequenceCheckboxes.forEach(cb => {
                cb.checked = false;
                const stepCard = document.getElementById(`step-${cb.dataset.stepKey}`);
                if (stepCard) stepCard.classList.remove('custom-sequence-selected');
                const orderEl = document.getElementById(`order-${cb.dataset.stepKey}`);
                if (orderEl) orderEl.textContent = '';
            });
            ui.updateCustomSequenceButtonsUI();
        });
    }

    if (dom.runCustomSequenceButton) {
        dom.runCustomSequenceButton.addEventListener('click', () => {
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

    if (dom.confirmRunCustomSequenceButton) {
        dom.confirmRunCustomSequenceButton.addEventListener('click', async () => {
            closePopupUI(dom.customSequenceConfirmPopupOverlay);
            if (getIsAnySequenceRunning()) {
                showNotification("Une autre séquence est déjà en cours.", 'warning'); return;
            }
            // Loading state on confirm button and disable run-custom while executing
            try {
                dom.confirmRunCustomSequenceButton.setAttribute('data-loading', 'true');
                dom.confirmRunCustomSequenceButton.disabled = true;
                if (dom.runCustomSequenceButton) dom.runCustomSequenceButton.disabled = true;

                // Play workflow start sound for custom sequence
                soundEvents.workflowStart();
                await runStepSequence(getSelectedStepsOrder(), "Séquence Personnalisée");
            } finally {
                dom.confirmRunCustomSequenceButton.removeAttribute('data-loading');
                dom.confirmRunCustomSequenceButton.disabled = false;
                if (dom.runCustomSequenceButton) dom.runCustomSequenceButton.disabled = getIsAnySequenceRunning();
            }
        });
    }

    if (dom.cancelRunCustomSequenceButton) {
        dom.cancelRunCustomSequenceButton.addEventListener('click', () => {
            closePopupUI(dom.customSequenceConfirmPopupOverlay);
        });
    }
    if (dom.closeSummaryPopupButton) {
        dom.closeSummaryPopupButton.addEventListener('click', () => {
            closePopupUI(dom.sequenceSummaryPopupOverlay);
        });
    }

    // --- DELETION START: Suppression du gestionnaire d'événement pour le bouton de cache ---
    /*
    if (dom.clearCacheGlobalButton) {
        dom.clearCacheGlobalButton.addEventListener('click', async () => {
            const stepKey = 'clear_disk_cache'; 
            // ... (toute la logique interne est supprimée) ...
        });
    }
    */
    // --- DELETION END ---



    // Auto-scroll toggle event handler
    if (dom.autoScrollToggle) {
        // Initialize the toggle state from localStorage
        const isEnabled = isAutoScrollEnabled();
        dom.autoScrollToggle.checked = isEnabled;
        if (dom.autoScrollStatus) {
            dom.autoScrollStatus.textContent = isEnabled ? 'Activé' : 'Désactivé';
        }

        dom.autoScrollToggle.addEventListener('change', (event) => {
            const enabled = event.target.checked;
            setAutoScrollEnabled(enabled);
            if (dom.autoScrollStatus) {
                dom.autoScrollStatus.textContent = enabled ? 'Activé' : 'Désactivé';
            }
            console.log(`[EVENT] Auto-scroll ${enabled ? 'enabled' : 'disabled'} by user`);
        });
    }

    // Sound control toggle event handler
    if (dom.soundToggle) {
        // Import sound manager functions
        import('./soundManager.js').then(({ isSoundEnabled, setSoundEnabled }) => {
            // Initialize the toggle state from localStorage
            const isEnabled = isSoundEnabled();
            dom.soundToggle.checked = isEnabled;
            if (dom.soundStatus) {
                dom.soundStatus.textContent = isEnabled ? 'Activé' : 'Désactivé';
            }

            dom.soundToggle.addEventListener('change', (event) => {
                const enabled = event.target.checked;
                setSoundEnabled(enabled);
                if (dom.soundStatus) {
                    dom.soundStatus.textContent = enabled ? 'Activé' : 'Désactivé';
                }
                console.log(`[EVENT] Sound effects ${enabled ? 'enabled' : 'disabled'} by user`);
            });
        });
    }
}