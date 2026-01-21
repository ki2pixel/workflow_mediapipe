function assert(condition, message) {
  if (!condition) throw new Error(message || 'Assertion failed');
}

const elements = {};
const getElementCalls = [];

if (!global.document) global.document = {};

global.document.getElementById = (id) => {
  getElementCalls.push(id);
  return elements[id] || null;
};

global.document.querySelectorAll = () => [];

global.document.createElement = () => ({
  set textContent(_) {},
  get innerHTML() {
    return '';
  }
});

if (!global.window) global.window = {};

global.window.addEventListener = () => {};

global.window.removeEventListener = () => {};

(async () => {
  try {
    const domModule = await import('../../static/domElements.js');
    const { getStepElement } = domModule;

    // Given: A valid step element exists in the DOM map
    elements['step-STEP1'] = { id: 'step-STEP1', dataset: { stepKey: 'STEP1' } };

    // When: We request the element via getStepElement
    const validResult = getStepElement('STEP1');

    // Then: We get back the same element
    assert(validResult === elements['step-STEP1'], 'Expected to retrieve DOM element for STEP1');

    // Given: Another safe key containing dash/underscore
    elements['step-STEP-5_ok'] = { id: 'step-STEP-5_ok' };

    // When: We request the element
    const dashResult = getStepElement('STEP-5_ok');

    // Then: Element is returned normally
    assert(dashResult === elements['step-STEP-5_ok'], 'Expected to retrieve DOM element for STEP-5_ok');

    // Given: Baseline number of calls before invalid requests
    const baselineCalls = getElementCalls.length;

    // When: We pass an unsafe key containing a space
    const unsafeSpace = getStepElement('STEP 1');

    // Then: Returned value is null and no DOM query was made
    assert(unsafeSpace === null, 'Expected null for unsafe step key with spaces');
    assert(getElementCalls.length === baselineCalls, 'Unsafe key should not trigger getElementById');

    // When: Another unsafe key containing HTML-like characters is used
    const unsafeHtml = getStepElement('<img>');

    // Then: Null returned and getElementById not invoked
    assert(unsafeHtml === null, 'Expected null for unsafe step key with HTML characters');
    assert(getElementCalls.length === baselineCalls, 'Unsafe HTML key should not trigger getElementById');

    console.log('domElements step guard tests: OK');
    process.exit(0);
  } catch (err) {
    console.error('domElements step guard tests failed:', err);
    process.exit(1);
  }
})();
