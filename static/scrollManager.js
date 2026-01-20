/**
 * Scroll Manager Module
 * Handles automatic scrolling to active workflow steps with smooth animations
 * and intelligent viewport positioning.
 */

import * as dom from './domElements.js';


const SCROLL_CONFIG = {
    behavior: 'smooth',
    block: 'center',
    inline: 'nearest',
    topOffset: 100,
    minScrollDistance: 50,
    scrollDelay: 150,
    topbarHeight: 68, // Hauteur de la topbar depuis variables.css
    bottomMargin: 40   // Marge inférieure pour éviter le débordement
};

/**
 * Checks if an element is currently visible in the viewport
 * @param {HTMLElement} element - The element to check
 * @returns {boolean} True if element is fully or partially visible
 */
function isElementInViewport(element) {
    if (!element) return false;
    
    const rect = element.getBoundingClientRect();
    const windowHeight = window.innerHeight || document.documentElement.clientHeight;
    const windowWidth = window.innerWidth || document.documentElement.clientWidth;
    
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= windowHeight &&
        rect.right <= windowWidth
    );
}

/**
 * Checks if an element is partially visible in the viewport
 * @param {HTMLElement} element - The element to check
 * @returns {boolean} True if element is at least partially visible
 */
function isElementPartiallyVisible(element) {
    if (!element) return false;
    
    const rect = element.getBoundingClientRect();
    const windowHeight = window.innerHeight || document.documentElement.clientHeight;
    const windowWidth = window.innerWidth || document.documentElement.clientWidth;
    
    return (
        rect.bottom > 0 &&
        rect.right > 0 &&
        rect.top < windowHeight &&
        rect.left < windowWidth
    );
}

/**
 * Calculates the optimal scroll position for an element with perfect centering
 * @param {HTMLElement} element - The target element
 * @returns {number} The optimal scroll top position
 */
function calculateOptimalScrollPosition(element) {
    if (!element) return 0;
    
    const rect = element.getBoundingClientRect();
    const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const windowHeight = window.innerHeight || document.documentElement.clientHeight;
    
    // Zone visible effective : topbar + margin inférieure
    const effectiveViewportHeight = windowHeight - SCROLL_CONFIG.topbarHeight - SCROLL_CONFIG.bottomMargin;
    const elementTop = rect.top + currentScrollTop;
    const elementHeight = rect.height;
    
    // Centrage agressif dans la zone effective (pas de contraintes min/max)
    const viewportCenter = SCROLL_CONFIG.topbarHeight + (effectiveViewportHeight / 2);
    const targetScrollTop = elementTop + (elementHeight / 2) - viewportCenter;
    
    // Contrainte simple : ne pas aller en négatif
    const finalScrollTop = Math.max(0, targetScrollTop);
    
    console.log('[SCROLL] Position calculation:', {
        elementTop,
        elementHeight,
        windowHeight,
        effectiveViewportHeight,
        viewportCenter,
        targetScrollTop,
        finalScrollTop
    });
    
    return finalScrollTop;
}

/**
 * Determines if scrolling is necessary based on current element visibility
 * @param {HTMLElement} element - The target element
 * @returns {boolean} True if scrolling should be performed
 */
function shouldScroll(element) {
    if (!element) return false;
    
    // Pour les séquences, toujours autoriser le scroll pour garantir le repositionnement
    console.log('[SCROLL] shouldScroll: allowing scroll for sequence positioning');
    return true;
}

/**
 * Smoothly scrolls to bring the target element into optimal view
 * @param {HTMLElement} element - The element to scroll to
 * @param {Object} options - Additional scroll options
 */
function scrollToElement(element, options = {}) {
    if (!element) {
        console.warn('[SCROLL] No element provided for scrolling');
        return;
    }
    
    const config = { ...SCROLL_CONFIG, ...options };
    
    if (!shouldScroll(element)) {
        return;
    }
    
    console.log(`[SCROLL] Scrolling to element: ${element.id || element.className}`);

    const behavior = config.behavior === 'smooth' ? 'smooth' : 'auto';
    const targetScrollTop = calculateOptimalScrollPosition(element);
    window.scrollTo({
        top: targetScrollTop,
        behavior
    });
}

/**
 * Scrolls to the active workflow step with a delay to allow UI transitions
 * @param {string} stepKey - The key of the step to scroll to
 * @param {Object} options - Additional options for scrolling
 */
export function scrollToActiveStep(stepKey, options = {}) {
    if (!stepKey) {
        console.warn('[SCROLL] No stepKey provided for scrollToActiveStep');
        return;
    }
    
    const stepElement = document.getElementById(`step-${stepKey}`);
    if (!stepElement) {
        console.warn(`[SCROLL] Step element not found: step-${stepKey}`);
        return;
    }
    
    const config = { ...SCROLL_CONFIG, ...options };
    
    setTimeout(() => {
        scrollToElement(stepElement, config);
    }, config.scrollDelay);
}

/**
 * Scrolls to a step immediately without delay (for manual triggers)
 * @param {string} stepKey - The key of the step to scroll to
 * @param {Object} options - Additional options for scrolling
 */
export function scrollToStepImmediate(stepKey, options = {}) {
    if (!stepKey) return;
    
    const stepElement = document.getElementById(`step-${stepKey}`);
    if (!stepElement) return;
    
    scrollToElement(stepElement, { ...SCROLL_CONFIG, ...options });
}

/**
 * Scrolls to a step with forced repositioning for sequences (ignores current position)
 * @param {string} stepKey - The key of the step to scroll to
 * @param {Object} options - Additional options for scrolling
 */
export function scrollToStepForced(stepKey, options = {}) {
    if (!stepKey) {
        console.warn('[SCROLL] No stepKey provided for scrollToStepForced');
        return;
    }
    
    const stepElement = document.getElementById(`step-${stepKey}`);
    if (!stepElement) {
        console.warn(`[SCROLL] Step element not found: step-${stepKey}`);
        return;
    }
    
    const config = { ...SCROLL_CONFIG, ...options };
    
    // Forcer le scroll avec scrollIntoView direct (plus efficace pour les grids)
    console.log(`[SCROLL] Forced scrolling to step: ${stepKey}`);
    
    try {
        // Utiliser scrollIntoView avec block 'center' pour forcer le positionnement
        stepElement.scrollIntoView({
            behavior: config.behavior,
            block: 'center',
            inline: 'nearest'
        });
        
        console.log(`[SCROLL] Applied scrollIntoView with block: center`);
        
        // Backup : forcer avec window.scrollTo si scrollIntoView ne fonctionne pas
        setTimeout(() => {
            const rect = stepElement.getBoundingClientRect();
            const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const windowHeight = window.innerHeight || document.documentElement.clientHeight;
            
            // Calcul simple : centrer l'élément dans le viewport
            const elementCenter = rect.top + currentScrollTop + (rect.height / 2);
            const viewportCenter = windowHeight / 2;
            const targetScrollTop = elementCenter - viewportCenter;
            
            console.log(`[SCROLL] Backup scroll calculation:`, {
                rectTop: rect.top,
                currentScrollTop,
                windowHeight,
                elementCenter,
                viewportCenter,
                targetScrollTop
            });
            
            window.scrollTo({
                top: Math.max(0, targetScrollTop),
                behavior: 'instant' // instant pour le backup
            });
        }, 50);
        
    } catch (error) {
        console.warn('[SCROLL] scrollIntoView failed, using manual calculation:', error);
        
        // Fallback manuel
        const optimalScrollTop = calculateOptimalScrollPosition(stepElement);
        window.scrollTo({
            top: optimalScrollTop,
            behavior: config.behavior
        });
    }
}

/**
 * Checks if auto-scroll should be enabled based on user preferences and context
 * @returns {boolean} True if auto-scroll should be active
 */
export function isAutoScrollEnabled() {
    const userPreference = localStorage.getItem('workflow-auto-scroll');
    if (userPreference === 'disabled') {
        return false;
    }

    if (userPreference === 'enabled') {
        return true;
    }

    const isLogsActive = dom.workflowWrapper && dom.workflowWrapper.classList.contains('logs-active');
    return isLogsActive;
}

/**
 * Enables or disables auto-scroll functionality
 * @param {boolean} enabled - Whether to enable auto-scroll
 */
export function setAutoScrollEnabled(enabled) {
    localStorage.setItem('workflow-auto-scroll', enabled ? 'enabled' : 'disabled');
    console.log(`[SCROLL] Auto-scroll ${enabled ? 'enabled' : 'disabled'}`);
}

/**
 * Checks if auto-scroll for sequences should be enabled based on user preferences
 * @returns {boolean} True if sequence auto-scroll should be active
 */
export function isSequenceAutoScrollEnabled() {
    const sequencePreference = localStorage.getItem('workflow-sequence-auto-scroll');
    if (sequencePreference === 'disabled') {
        return false;
    }
    
    if (sequencePreference === 'enabled') {
        return true;
    }
    
    // Par défaut, activer l'auto-scroll pour les séquences
    return true;
}

/**
 * Enables or disables auto-scroll for sequences specifically
 * @param {boolean} enabled - Whether to enable sequence auto-scroll
 */
export function setSequenceAutoScrollEnabled(enabled) {
    localStorage.setItem('workflow-sequence-auto-scroll', enabled ? 'enabled' : 'disabled');
    console.log(`[SCROLL] Sequence auto-scroll ${enabled ? 'enabled' : 'disabled'}`);
}

/**
 * Scrolls to a step with ultra-aggressive repositioning (instant scroll)
 * @param {string} stepKey - The key of the step to scroll to
 * @param {Object} options - Additional options for scrolling
 */
export function scrollToStepUltraAggressive(stepKey, options = {}) {
    if (!stepKey) {
        console.warn('[SCROLL] No stepKey provided for scrollToStepUltraAggressive');
        return;
    }
    
    const stepElement = document.getElementById(`step-${stepKey}`);
    if (!stepElement) {
        console.warn(`[SCROLL] Step element not found: step-${stepKey}`);
        return;
    }
    
    console.log(`[SCROLL] Ultra-aggressive scrolling to step: ${stepKey}`);
    
    // Scroll instantané avec scrollIntoView
    stepElement.scrollIntoView({
        behavior: 'instant',
        block: 'center',
        inline: 'nearest'
    });
    
    // Forcer un second scroll immédiat après
    setTimeout(() => {
        const rect = stepElement.getBoundingClientRect();
        const windowHeight = window.innerHeight || document.documentElement.clientHeight;
        const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Calcul ultra-simple : centrer parfaitement
        const elementCenter = rect.top + currentScrollTop + (rect.height / 2);
        const viewportCenter = (windowHeight / 2);
        const targetScrollTop = elementCenter - viewportCenter;
        
        console.log(`[SCROLL] Ultra-aggressive calculation:`, {
            rectTop: rect.top,
            rectHeight: rect.height,
            elementCenter,
            viewportCenter,
            targetScrollTop
        });
        
        window.scrollTo({
            top: Math.max(0, targetScrollTop),
            behavior: 'instant'
        });
    }, 10);
}

/**
 * Scrolls to a step with absolute forced repositioning (ignores all CSS and layout factors)
 * @param {string} stepKey - The key of the step to scroll to
 * @param {Object} options - Additional options for scrolling
 */
export function scrollToStepAbsolute(stepKey, options = {}) {
    if (!stepKey) {
        console.warn('[SCROLL] No stepKey provided for scrollToStepAbsolute');
        return;
    }
    
    const stepElement = document.getElementById(`step-${stepKey}`);
    if (!stepElement) {
        console.warn(`[SCROLL] Step element not found: step-${stepKey}`);
        return;
    }
    
    console.log(`[SCROLL] Absolute forced scrolling to step: ${stepKey}`);
    
    // Forcer un scroll absolu en calculant la position exacte
    const rect = stepElement.getBoundingClientRect();
    const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const windowHeight = window.innerHeight || document.documentElement.clientHeight;
    
    // Calcul absolu : centrer l'élément parfaitement au milieu du viewport
    const elementAbsoluteTop = rect.top + currentScrollTop;
    const elementCenter = elementAbsoluteTop + (rect.height / 2);
    const viewportCenter = windowHeight / 2;
    const absoluteScrollTop = elementCenter - viewportCenter;
    
    console.log(`[SCROLL] Absolute calculation:`, {
        rectTop: rect.top,
        rectHeight: rect.height,
        currentScrollTop,
        elementAbsoluteTop,
        elementCenter,
        viewportCenter,
        absoluteScrollTop
    });
    
    // Appliquer le scroll absolu instantané
    window.scrollTo({
        top: Math.max(0, absoluteScrollTop),
        behavior: 'instant'
    });
    
    // Forcer un second scroll après un court delay pour contrer toute animation CSS
    setTimeout(() => {
        window.scrollTo({
            top: Math.max(0, absoluteScrollTop),
            behavior: 'instant'
        });
        console.log(`[SCROLL] Applied absolute scroll to: ${Math.max(0, absoluteScrollTop)}px`);
    }, 5);
}

export { SCROLL_CONFIG };
