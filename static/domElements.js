export const workflowWrapper = document.getElementById('workflow-wrapper');
export const stepsColumn = document.getElementById('steps-column');
export const logsColumnGlobal = document.getElementById('logs-column-global');
export const logPanelTitle = document.getElementById('log-panel-title');
export const mainLogOutputPanel = document.getElementById('main-log-output-panel');
export const currentStepLogNamePanel = document.getElementById('current-step-log-name-panel');
export const specificLogContainerPanel = document.getElementById('specific-log-container-panel');
export const specificLogHeaderTextPanel = document.getElementById('specific-log-header-text-panel');
export const specificLogPathInfoPanel = document.getElementById('specific-log-path-info-panel');
export const specificLogOutputContentPanel = document.getElementById('specific-log-output-content-panel');
export const runAllButton = document.getElementById('run-all-steps-button');
export const topbarAffix = document.getElementById('topbar-affix');
export const topbarControls = document.getElementById('topbar-controls');
export const globalProgressAffix = document.getElementById('global-progress-affix');
export const globalProgressContainer = document.getElementById('global-progress-container');
export const globalProgressBar = document.getElementById('global-progress-bar');
export const globalProgressText = document.getElementById('global-progress-text');
export const sequenceSummaryPopupOverlay = document.getElementById('sequence-summary-popup-overlay');
export const sequenceSummaryList = document.getElementById('sequence-summary-list');
export const closeSummaryPopupButton = document.getElementById('close-summary-popup');
export const runCustomSequenceButton = document.getElementById('run-custom-sequence-button');
export const clearCustomSequenceButton = document.getElementById('clear-custom-sequence-button');
export const customSequenceCheckboxes = document.querySelectorAll('.custom-sequence-checkbox');
export const customSequenceConfirmPopupOverlay = document.getElementById('custom-sequence-confirm-popup-overlay');
export const customSequenceConfirmList = document.getElementById('custom-sequence-confirm-list');
export const confirmRunCustomSequenceButton = document.getElementById('confirm-run-custom-sequence-button');
export const cancelRunCustomSequenceButton = document.getElementById('cancel-run-custom-sequence-button');
export const notificationsArea = document.getElementById('notifications-area');

// Lazy DOM element getters to ensure elements are available when accessed
export function getAllStepDivs() {
    const elements = document.querySelectorAll('.step');
    console.debug(`[DOM] getAllStepDivs found ${elements.length} elements`);
    return elements;
}

export function getAllRunButtons() {
    const elements = document.querySelectorAll('.run-button');
    console.debug(`[DOM] getAllRunButtons found ${elements.length} elements`);
    return elements;
}

export function getAllCancelButtons() {
    const elements = document.querySelectorAll('.cancel-button');
    console.debug(`[DOM] getAllCancelButtons found ${elements.length} elements`);
    return elements;
}

export function getAllSpecificLogButtons() {
    const elements = document.querySelectorAll('.specific-log-button');
    console.debug(`[DOM] getAllSpecificLogButtons found ${elements.length} elements`);
    return elements;
}

// Enhanced step element getter with validation
export function getStepElement(stepKey) {
    if (!stepKey) {
        console.warn('[DOM] getStepElement called with invalid stepKey:', stepKey);
        return null;
    }

    const element = document.getElementById(`step-${stepKey}`);
    if (!element) {
        console.warn(`[DOM] Step element not found: step-${stepKey}`);
        console.debug('[DOM] Available step elements:',
            Array.from(document.querySelectorAll('[id^="step-"]')).map(el => el.id));
    }

    return element;
}

// Validate DOM structure for debugging
export function validateDOMStructure() {
    const results = {
        stepElements: getAllStepDivs().length,
        runButtons: getAllRunButtons().length,
        cancelButtons: getAllCancelButtons().length,
        workflowWrapper: !!workflowWrapper,
        stepsColumn: !!stepsColumn,
        issues: []
    };

    // Check for common issues
    if (results.stepElements === 0) {
        results.issues.push('No step elements found (.step)');
    }

    if (!results.workflowWrapper) {
        results.issues.push('Workflow wrapper not found (#workflow-wrapper)');
    }

    if (!results.stepsColumn) {
        results.issues.push('Steps column not found (#steps-column)');
    }

    console.debug('[DOM] Structure validation:', results);
    return results;
}

// Legacy exports for backward compatibility (will be deprecated)
export const allStepDivs = getAllStepDivs();
export const allRunButtons = getAllRunButtons();
export const allCancelButtons = getAllCancelButtons();
export const allSpecificLogButtons = getAllSpecificLogButtons();
export const closeLogPanelButton = document.getElementById('close-log-panel');

export const localDownloadsList = document.getElementById('local-downloads-list');



// ÉLÉMENTS POUR LE CONTRÔLE AUTO-SCROLL
export const autoScrollToggle = document.getElementById('auto-scroll-toggle');
export const autoScrollStatus = document.getElementById('auto-scroll-status');
export const autoScrollWidget = document.getElementById('auto-scroll-widget');

// ÉLÉMENTS POUR LE CONTRÔLE SONORE
export const soundToggle = document.getElementById('sound-toggle');
export const soundStatus = document.getElementById('sound-status');
export const soundControlWidget = document.getElementById('sound-control-widget');


// ÉLÉMENTS POUR LE PANNEAU DE RÉGLAGES (top bar)
export const settingsToggle = document.getElementById('settings-toggle');
export const settingsPanel = document.getElementById('settings-panel');