// Import new immutable state management
import { appState } from './state/AppState.js';

export const PROCESS_INFO_CLIENT = new Proxy({}, {
    get(_target, prop) {
        if (typeof prop !== 'string') return undefined;
        return appState.getStateProperty(`processInfo.${prop}`);
    },
    set(_target, prop, value) {
        if (typeof prop !== 'string') return false;
        appState.setState({ processInfo: { [prop]: value } }, 'process_info_update');
        return true;
    },
    ownKeys() {
        const root = appState.getStateProperty('processInfo') || {};
        return Reflect.ownKeys(root);
    },
    getOwnPropertyDescriptor(_target, prop) {
        const root = appState.getStateProperty('processInfo') || {};
        if (Object.prototype.hasOwnProperty.call(root, prop)) {
            return { enumerable: true, configurable: true };
        }
        return undefined;
    }
});

// Legacy exports for backward compatibility (deprecated - use appState instead)
export let pollingIntervals = {};
export let activeStepKeyForLogsPanel = null;
export let stepTimers = {};
export let selectedStepsOrder = [];
export let isAnySequenceRunning = false;
export let focusedElementBeforePopup = null;
export let autoOpenLogOverlay = true;


// --- MODIFICATION: La liste des étapes est mise à jour pour correspondre au backend ---
export const REMOTE_SEQUENCE_STEP_KEYS = [
    "STEP1",
    "STEP2",
    "STEP3",
    "STEP4",
    "STEP5",
    "STEP6",
    "STEP7"
];

// Modern state management functions using AppState
export function setActiveStepKeyForLogs(key) {
    activeStepKeyForLogsPanel = key; // Legacy
    appState.setState({ activeStepKeyForLogsPanel: key }, 'setActiveStepKeyForLogs');
}
export function getActiveStepKeyForLogs() {
    return appState.getStateProperty('activeStepKeyForLogsPanel') || activeStepKeyForLogsPanel;
}

export function addStepTimer(stepKey, timerData) {
    stepTimers[stepKey] = timerData; // Legacy
    appState.setState({
        stepTimers: { ...appState.getStateProperty('stepTimers'), [stepKey]: timerData }
    }, 'addStepTimer');
}
export function getStepTimer(stepKey) {
    return appState.getStateProperty(`stepTimers.${stepKey}`) || stepTimers[stepKey];
}
export function clearStepTimerInterval(stepKey) {
    const timer = getStepTimer(stepKey);
    if (timer && timer.intervalId) {
        clearInterval(timer.intervalId);
        const updatedTimer = { ...timer, intervalId: null };
        addStepTimer(stepKey, updatedTimer);
    }
}
export function deleteStepTimer(stepKey) {
    if (getStepTimer(stepKey)) {
        clearStepTimerInterval(stepKey);
        delete stepTimers[stepKey]; // Legacy
        const currentTimers = appState.getStateProperty('stepTimers') || {};
        const { [stepKey]: removed, ...remainingTimers } = currentTimers;
        appState.setState({ stepTimers: remainingTimers }, 'deleteStepTimer');
    }
}

export function setSelectedStepsOrder(order) {
    selectedStepsOrder = order; // Legacy
    appState.setState({ selectedStepsOrder: order }, 'setSelectedStepsOrder');
}
export function getSelectedStepsOrder() {
    return appState.getStateProperty('selectedStepsOrder') || selectedStepsOrder;
}

export function setIsAnySequenceRunning(running) {
    isAnySequenceRunning = running; // Legacy
    appState.setState({ isAnySequenceRunning: running }, 'setIsAnySequenceRunning');
}
export function getIsAnySequenceRunning() {
    return appState.getStateProperty('isAnySequenceRunning') || isAnySequenceRunning;
}

export function setFocusedElementBeforePopup(element) {
    focusedElementBeforePopup = element; // Legacy
    appState.setState({ focusedElementBeforePopup: element }, 'setFocusedElementBeforePopup');
}
export function getFocusedElementBeforePopup() {
    return appState.getStateProperty('focusedElementBeforePopup') || focusedElementBeforePopup;
}

export function setAutoOpenLogOverlay(enabled) {
    autoOpenLogOverlay = !!enabled;
    const currentUI = appState.getStateProperty('ui') || {};
    appState.setState({ ui: { ...currentUI, autoOpenLogOverlay: autoOpenLogOverlay } }, 'setAutoOpenLogOverlay');
}

export function getAutoOpenLogOverlay() {
    const uiValue = appState.getStateProperty('ui.autoOpenLogOverlay');
    return typeof uiValue === 'boolean' ? uiValue : autoOpenLogOverlay;
}

export function setAutoModeLogPanelOpened(opened) {
    appState.setState({ ui: { autoModeLogPanelOpened: !!opened } }, 'setAutoModeLogPanelOpened');
}

export function getAutoModeLogPanelOpened() {
    return !!appState.getStateProperty('ui.autoModeLogPanelOpened');
}

export function addPollingInterval(stepKey, id) {
    pollingIntervals[stepKey] = id; // Legacy
    appState.setState({
        pollingIntervals: { ...appState.getStateProperty('pollingIntervals'), [stepKey]: id }
    }, 'addPollingInterval');
}
export function clearPollingInterval(stepKey) {
    if (pollingIntervals[stepKey]) {
        clearInterval(pollingIntervals[stepKey]);
        delete pollingIntervals[stepKey]; // Legacy
    }
    const currentIntervals = appState.getStateProperty('pollingIntervals') || {};
    const { [stepKey]: removed, ...remainingIntervals } = currentIntervals;
    appState.setState({ pollingIntervals: remainingIntervals }, 'clearPollingInterval');
}
export function getPollingInterval(stepKey) {
    return appState.getStateProperty(`pollingIntervals.${stepKey}`) || pollingIntervals[stepKey];
}



// Export the appState for direct access to modern state management
export { appState };