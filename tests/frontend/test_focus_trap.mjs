// Focus trap + focus restore tests for modals (Node/ESM)
// No external deps. We stub minimal DOM to validate behavior.

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

function makeFocusable(id) {
  return {
    id,
    offsetParent: {},
    _attrs: new Map(),
    getAttribute: function (k) { return this._attrs.has(k) ? this._attrs.get(k) : null; },
    setAttribute: function (k, v) { this._attrs.set(k, String(v)); },
    focus: function () { global.document.activeElement = this; },
  };
}

function makeOverlay(focusables) {
  const overlay = {
    offsetParent: {},
    _attrs: new Map(),
    _listeners: new Map(),
    style: {},
    querySelectorAll: () => focusables,
    getAttribute: function (k) { return this._attrs.has(k) ? this._attrs.get(k) : null; },
    setAttribute: function (k, v) { this._attrs.set(k, String(v)); },
    addEventListener: function (type, handler) { this._listeners.set(type, handler); },
    removeEventListener: function (type, handler) {
      const current = this._listeners.get(type);
      if (current === handler) this._listeners.delete(type);
    },
    focus: function () { global.document.activeElement = overlay; },
  };
  return overlay;
}

function triggerKeydown(overlay, e) {
  const handler = overlay._listeners.get('keydown');
  if (!handler) throw new Error('No keydown handler registered');
  handler(e);
}

// Stub globals required by imported modules
if (!global.window) {
  global.window = {};
}
global.window.addEventListener = () => {};
global.window.removeEventListener = () => {};
global.window.location = { hostname: 'localhost' };

if (!global.requestAnimationFrame) {
  global.requestAnimationFrame = (cb) => setTimeout(cb, 0);
}
if (!global.cancelAnimationFrame) {
  global.cancelAnimationFrame = (id) => clearTimeout(id);
}

if (!global.document) {
  global.document = {};
}
global.document.body = {};
global.document.documentElement = {};
global.document.activeElement = null;
// DOMUpdateUtils.escapeHtml (DOMBatcher import) uses createElement
global.document.createElement = () => {
  let _text = '';
  return {
    set textContent(v) { _text = String(v); },
    get innerHTML() {
      return _text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    },
  };
};

(async () => {
  try {
    const reportUrl = new URL('../../static/reportViewer.js', import.meta.url);
    const reportMod = await import(reportUrl);
    const reportViewer = reportMod.reportViewer;

    // Given: Preconditions
    const prev = makeFocusable('prev');
    global.document.activeElement = prev;

    const f1 = makeFocusable('f1');
    const f2 = makeFocusable('f2');
    const overlay = makeOverlay([f1, f2]);

    // When:  Operation to execute
    reportViewer.overlay = overlay;
    reportViewer._enableModalFocusTrap();

    // Then:  Expected result/verification
    assert(reportViewer.prevFocusEl === prev, 'Expected prev focus to be stored');
    assert(global.document.activeElement === f1, 'Expected first focusable to receive focus');

    // Given: Preconditions
    // When:  Operation to execute
    triggerKeydown(overlay, { key: 'Tab', shiftKey: false, preventDefault: () => {} });

    // Then:  Expected result/verification
    assert(global.document.activeElement === f2, 'Expected Tab to move focus forward');

    // Given: Preconditions
    // When:  Operation to execute
    triggerKeydown(overlay, { key: 'Tab', shiftKey: false, preventDefault: () => {} });

    // Then:  Expected result/verification
    assert(global.document.activeElement === f1, 'Expected Tab to wrap around');

    // Given: Preconditions
    // When:  Operation to execute
    triggerKeydown(overlay, { key: 'Tab', shiftKey: true, preventDefault: () => {} });

    // Then:  Expected result/verification
    assert(global.document.activeElement === f2, 'Expected Shift+Tab to wrap backward');

    // Given: Preconditions
    // When:  Operation to execute
    reportViewer._disableModalFocusTrap();

    // Then:  Expected result/verification
    assert(global.document.activeElement === prev, 'Expected focus restored to previous element');

    // Given: Preconditions
    const prev2 = makeFocusable('prev2');
    global.document.activeElement = prev2;
    const emptyOverlay = makeOverlay([]);

    // When:  Operation to execute
    reportViewer.overlay = emptyOverlay;
    reportViewer._enableModalFocusTrap();

    // Then:  Expected result/verification
    assert(reportViewer.prevFocusEl === prev2, 'Expected prev focus to be stored (reportViewer)');
    assert(global.document.activeElement === emptyOverlay, 'Expected overlay to be focused when no focusables');

    // Given: Preconditions
    // When:  Operation to execute
    reportViewer._disableModalFocusTrap();

    // Then:  Expected result/verification
    assert(global.document.activeElement === prev2, 'Expected focus restored (reportViewer)');

    console.log('Modal focus trap & focus restore tests: OK');
    process.exit(0);
  } catch (err) {
    console.error('Modal focus trap & focus restore tests failed:', err);
    process.exit(1);
  }
})();
