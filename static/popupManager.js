import * as dom from './domElements.js';
import { appState } from './state/AppState.js';
import { DOMUpdateUtils } from './utils/DOMBatcher.js';

function handlePopupKeydown(event) {
    const popupOverlay = event.currentTarget;
    if (event.key === 'Escape') {
        closePopupUI(popupOverlay);
    }
    if (event.key === 'Tab') {
        const focusableElements = Array.from(popupOverlay.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')).filter(el => el.offsetParent !== null);
        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (event.shiftKey) {
            if (document.activeElement === firstElement) {
                lastElement.focus();
                event.preventDefault();
            }
        } else {
            if (document.activeElement === lastElement) {
                firstElement.focus();
                event.preventDefault();
            }
        }
    }
}

export function openPopupUI(popupOverlay) {
    if (!popupOverlay) return;

    const currentFocused = document.activeElement;
    if (currentFocused &&
        currentFocused !== document.body &&
        currentFocused !== document.documentElement &&
        typeof currentFocused.focus === 'function' &&
        currentFocused.nodeType === Node.ELEMENT_NODE) {
        appState.setState({ focusedElementBeforePopup: currentFocused }, 'popup_focus_store');
        console.debug('[POPUP] Stored focusable element:', {
            tagName: currentFocused.tagName,
            id: currentFocused.id || 'no-id',
            className: currentFocused.className || 'no-class'
        });
    } else {
        appState.setState({ focusedElementBeforePopup: null }, 'popup_focus_store');
        console.debug('[POPUP] No valid focusable element to store');
    }

    popupOverlay.style.display = 'flex';
    popupOverlay.setAttribute('data-visible', 'true');
    popupOverlay.setAttribute('aria-hidden', 'false');
    const focusableElements = popupOverlay.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');

    let elementToFocus = null;
    for (let i = 0; i < focusableElements.length; i++) {
        const element = focusableElements[i];
        if (element.offsetParent !== null && typeof element.focus === 'function') {
            elementToFocus = element;
            break;
        }
    }

    if (elementToFocus) {
        try {
            elementToFocus.focus();
        } catch (error) {
            console.warn('[POPUP] Failed to focus element in popup:', error);
        }
    }

    popupOverlay.addEventListener('keydown', handlePopupKeydown);
}

export function closePopupUI(popupOverlay) {
    if (!popupOverlay) return;
    popupOverlay.removeAttribute('data-visible');
    popupOverlay.setAttribute('aria-hidden', 'true');
    popupOverlay.style.display = 'none';
    popupOverlay.removeEventListener('keydown', handlePopupKeydown);
    const prevFocused = appState.getStateProperty('focusedElementBeforePopup');

    if (prevFocused && typeof prevFocused.focus === 'function') {
        try {
            if (prevFocused.isConnected && document.hasFocus()) {
                if (document.contains(prevFocused) && prevFocused.offsetParent !== null) {
                    prevFocused.focus();
                } else {
                    console.debug('[POPUP] Previous focused element no longer focusable, skipping focus restoration');
                }
            }
        } catch (error) {
            console.warn('[POPUP] Failed to restore focus to previous element:', error);
        }
    } else if (prevFocused) {
        const elementInfo = {
            tagName: prevFocused.tagName || 'unknown',
            id: prevFocused.id || 'no-id',
            className: prevFocused.className || 'no-class',
            nodeType: prevFocused.nodeType || 'unknown',
            hasFocusMethod: typeof prevFocused.focus === 'function'
        };
        console.debug('[POPUP] Previous focused element is not focusable:', elementInfo);
    }

    appState.setState({ focusedElementBeforePopup: null }, 'popup_focus_clear');
}

function resolveSequenceSummaryElements() {
    const overlay = typeof dom.getSequenceSummaryPopupOverlay === 'function'
        ? dom.getSequenceSummaryPopupOverlay()
        : dom.sequenceSummaryPopupOverlay;
    const list = typeof dom.getSequenceSummaryList === 'function'
        ? dom.getSequenceSummaryList()
        : dom.sequenceSummaryList;
    return { overlay, list };
}

export function showSequenceSummaryUI(results, overallSuccess, sequenceName = "Séquence", overallDuration = null) {
    const { overlay, list } = resolveSequenceSummaryElements();
    if (!overlay || !list) {
        console.error("Éléments DOM pour la popup de résumé non trouvés!");
        return;
    }
    const summaryTitle = overlay.querySelector("h3");
    if (summaryTitle) summaryTitle.textContent = `Résumé: ${sequenceName}`;

    list.innerHTML = '';
    if (overallDuration && typeof overallDuration === 'string') {
        const totalItem = document.createElement('li');
        totalItem.style.fontWeight = 'bold';
        totalItem.style.marginBottom = '8px';
        totalItem.style.paddingBottom = '8px';
        totalItem.style.borderBottom = `1px solid var(--border-color)`;
        const safeDuration = DOMUpdateUtils.escapeHtml(overallDuration);
        totalItem.innerHTML = `<span class="status-icon" style="color:var(--accent-color);">⏱️</span> Durée totale: ${safeDuration}`;
        list.appendChild(totalItem);
    }
    results.forEach(result => {
        const listItem = document.createElement('li');
        const icon = result.success ? '<span class="status-icon status-completed" style="color:var(--green);">✔️</span>' : '<span class="status-icon status-failed" style="color:var(--red);">❌</span>';
        const safeName = DOMUpdateUtils.escapeHtml(String(result.name ?? ''));
        const safeDurationText = result.duration && result.duration !== "N/A" ? DOMUpdateUtils.escapeHtml(String(result.duration)) : "";
        const durationText = safeDurationText ? `<span class="duration">(${safeDurationText})</span>` : "";
        listItem.innerHTML = `${icon} ${safeName}: ${result.success ? 'Terminée avec succès' : 'Échouée ou annulée'} ${durationText}`;
        list.appendChild(listItem);
    });

    const overallStatusItem = document.createElement('li');
    overallStatusItem.style.fontWeight = 'bold';
    overallStatusItem.style.marginTop = '10px';
    overallStatusItem.style.paddingTop = '10px';
    overallStatusItem.style.borderTop = `1px solid var(--border-color)`;
    const safeSequenceName = DOMUpdateUtils.escapeHtml(String(sequenceName ?? 'Séquence'));
    if (overallSuccess) {
        overallStatusItem.innerHTML = `<span class="status-icon status-completed" style="color:var(--green);">🎉</span> ${safeSequenceName} terminée avec succès !`;
    } else {
        overallStatusItem.innerHTML = `<span class="status-icon status-failed" style="color:var(--red);">⚠️</span> ${safeSequenceName} a rencontré une ou plusieurs erreurs.`;
    }
    list.appendChild(overallStatusItem);
    openPopupUI(overlay);
}

export function showCustomSequenceConfirmUI() {
    dom.customSequenceConfirmList.innerHTML = '';
    const selectedStepsOrder = appState.getStateProperty('selectedStepsOrder') || [];
    selectedStepsOrder.forEach((stepKey, index) => {
        const stepElement = document.getElementById(`step-${stepKey}`);
        const stepName = stepElement ? stepElement.dataset.stepName : stepKey;
        const li = document.createElement('li');
        const safeStepName = DOMUpdateUtils.escapeHtml(String(stepName ?? ''));
        li.innerHTML = `<span class="order-prefix">${index + 1}.</span> ${safeStepName}`;
        dom.customSequenceConfirmList.appendChild(li);
    });
    openPopupUI(dom.customSequenceConfirmPopupOverlay);
}