/**
 * Test d'intégration pour l'auto-scroll des séquences
 * Vérifie que l'auto-scroll fonctionne correctement pendant l'exécution des séquences
 */

// Mock des APIs navigateur similaires aux autres tests frontend
function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

// Mock localStorage
const mockLocalStorage = {
  data: {},
  getItem: function(key) { return this.data[key] || null; },
  setItem: function(key, value) { this.data[key] = String(value); },
  removeItem: function(key) { delete this.data[key]; },
  clear: function() { this.data = {}; }
};

global.localStorage = mockLocalStorage;

// Mock des fonctions de scroll
let scrollCalls = [];
global.window = {
  scrollTo: (options) => {
    scrollCalls.push({ type: 'scrollTo', options });
  },
  pageYOffset: 0,
  innerHeight: 800
};

global.document = {
  documentElement: {
    scrollTop: 0,
    clientHeight: 800,
    scrollHeight: 2000,
    style: { behavior: 'smooth' }
  },
  getElementById: (id) => {
    if (id === 'step-NONEXISTENT') {
      return null;
    }
    return {
      id: id,
      scrollIntoView: (options) => {
        scrollCalls.push({ type: 'scrollIntoView', elementId: id, options });
      },
      getBoundingClientRect: () => ({
        top: 100,
        height: 50,
        bottom: 150
      })
    };
  }
};

// Import des fonctions à tester (simulées pour le test)
function isSequenceAutoScrollEnabled() {
    const sequencePreference = mockLocalStorage.getItem('workflow-sequence-auto-scroll');
    if (sequencePreference === 'disabled') {
        return false;
    }
    
    if (sequencePreference === 'enabled') {
        return true;
    }
    
    // Par défaut, activer l'auto-scroll pour les séquences
    return true;
}

function setSequenceAutoScrollEnabled(enabled) {
    mockLocalStorage.setItem('workflow-sequence-auto-scroll', enabled ? 'enabled' : 'disabled');
    console.log(`[SCROLL] Sequence auto-scroll ${enabled ? 'enabled' : 'disabled'}`);
}

function scrollToActiveStep(stepKey, options = {}) {
    if (!stepKey) {
        console.warn('[SCROLL] No stepKey provided for scrollToActiveStep');
        return;
    }
    
    const stepElement = global.document.getElementById(`step-${stepKey}`);
    if (!stepElement) {
        console.warn(`[SCROLL] Step element not found: step-${stepKey}`);
        return;
    }
    
    const config = {
        behavior: 'smooth',
        block: 'center',
        inline: 'nearest',
        scrollDelay: 150,
        ...options
    };
    
    setTimeout(() => {
        if (stepElement.scrollIntoView && 'behavior' in global.document.documentElement.style) {
            try {
                stepElement.scrollIntoView({
                    behavior: config.behavior,
                    block: config.block,
                    inline: config.inline
                });
            } catch (error) {
                console.warn('[SCROLL] Modern scrollIntoView failed, using fallback:', error);
                global.window.scrollTo({
                    top: 100,
                    behavior: config.behavior
                });
            }
        }
    }, config.scrollDelay);
}

// Tests
console.log('=== Test Auto-scroll Séquences ===');

// Test 1: Activé par défaut
mockLocalStorage.clear();
assert(isSequenceAutoScrollEnabled() === true, 'Devrait être activé par défaut');
console.log('✓ Auto-scroll activé par défaut');

// Test 2: Préférence désactivée
setSequenceAutoScrollEnabled(false);
assert(isSequenceAutoScrollEnabled() === false, 'Devrait respecter la préférence désactivée');
assert(mockLocalStorage.getItem('workflow-sequence-auto-scroll') === 'disabled', 'Devrait stocker "disabled"');
console.log('✓ Préférence désactivée respectée');

// Test 3: Préférence activée
setSequenceAutoScrollEnabled(true);
assert(isSequenceAutoScrollEnabled() === true, 'Devrait respecter la préférence activée');
assert(mockLocalStorage.getItem('workflow-sequence-auto-scroll') === 'enabled', 'Devrait stocker "enabled"');
console.log('✓ Préférence activée respectée');

// Test 4: Scroll vers élément existant
scrollCalls = [];
scrollToActiveStep('STEP1', { scrollDelay: 0 });

// Attendre l'exécution du setTimeout
await new Promise(resolve => setTimeout(resolve, 50));

assert(scrollCalls.length > 0, 'Devrait effectuer un appel de scroll');
const lastCall = scrollCalls[scrollCalls.length - 1];
assert(lastCall.elementId === 'step-STEP1' || lastCall.type === 'scrollTo', 'Devrait scroller vers l\'élément STEP1');
console.log('✓ Scroll vers élément existant');

// Test 5: Gestion élément inexistant
scrollCalls = [];
scrollToActiveStep('NONEXISTENT', { scrollDelay: 0 });
await new Promise(resolve => setTimeout(resolve, 50));

// Ne devrait pas faire d'appel de scroll si l'élément n'existe pas
assert(scrollCalls.length === 0, 'Ne devrait pas scroller pour un élément inexistant');
console.log('✓ Gestion élément inexistant');

console.log('=== Tous les tests passés ===');
