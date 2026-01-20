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
    scrollDelay: 150
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
 * Calculates the optimal scroll position for an element
 * @param {HTMLElement} element - The target element
 * @returns {number} The optimal scroll top position
 */
function calculateOptimalScrollPosition(element) {
    if (!element) return 0;
    
    const rect = element.getBoundingClientRect();
    const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const windowHeight = window.innerHeight || document.documentElement.clientHeight;
    
    const elementTop = rect.top + currentScrollTop;
    const elementHeight = rect.height;
    
    let targetScrollTop = elementTop - (windowHeight / 2) + (elementHeight / 2);
    
    const minScrollTop = elementTop - SCROLL_CONFIG.topOffset;
    targetScrollTop = Math.max(targetScrollTop, minScrollTop);
    
    const maxScrollTop = Math.max(0, document.documentElement.scrollHeight - windowHeight);
    targetScrollTop = Math.min(targetScrollTop, maxScrollTop);
    
    return Math.max(0, targetScrollTop);
}

/**
 * Determines if scrolling is necessary based on current element visibility
 * @param {HTMLElement} element - The target element
 * @returns {boolean} True if scrolling should be performed
 */
function shouldScroll(element) {
    if (!element) return false;
    
    if (isElementInViewport(element)) {
        const rect = element.getBoundingClientRect();
        const hasGoodPosition = rect.top > SCROLL_CONFIG.topOffset && 
                               rect.bottom < (window.innerHeight - 50);
        if (hasGoodPosition) {
            console.log('[SCROLL] Element is well-positioned, skipping scroll');
            return false;
        }
    }
    
    if (!isElementPartiallyVisible(element)) {
        console.log('[SCROLL] Element not visible, scrolling required');
        return true;
    }
    
    const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const optimalScrollTop = calculateOptimalScrollPosition(element);
    const scrollDistance = Math.abs(optimalScrollTop - currentScrollTop);
    
    if (scrollDistance < SCROLL_CONFIG.minScrollDistance) {
        console.log('[SCROLL] Scroll distance too small, skipping');
        return false;
    }
    
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
    
    if (element.scrollIntoView && 'behavior' in document.documentElement.style) {
        try {
            element.scrollIntoView({
                behavior: config.behavior,
                block: config.block,
                inline: config.inline
            });
        } catch (error) {
            console.warn('[SCROLL] Modern scrollIntoView failed, using fallback:', error);
            const targetScrollTop = calculateOptimalScrollPosition(element);
            window.scrollTo({
                top: targetScrollTop,
                behavior: config.behavior
            });
        }
    } else {
        const targetScrollTop = calculateOptimalScrollPosition(element);
        window.scrollTo(0, targetScrollTop);
    }
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

export { SCROLL_CONFIG };
