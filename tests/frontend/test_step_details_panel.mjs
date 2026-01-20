// Step Details panel tests (Node/ESM)
// No external deps. We stub browser APIs required by AppState/DOMBatcher/StepDetailsPanel.

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function createClassList(initial = []) {
  const set = new Set(initial);
  return {
    add: (...names) => names.forEach((n) => set.add(n)),
    remove: (...names) => names.forEach((n) => set.delete(n)),
    contains: (name) => set.has(name),
    toString: () => Array.from(set).join(' '),
  };
}

function createMockElement(tagName, { id = null, classes = [], dataset = {} } = {}) {
  const el = {
    tagName: String(tagName || 'DIV').toUpperCase(),
    id: id || '',
    dataset: { ...dataset },
    classList: createClassList(classes),
    className: classes.join(' '),
    attributes: {},
    hidden: false,
    textContent: '',
    _listeners: {},
    focus() {
      global.document.activeElement = el;
    },
    setAttribute(name, value) {
      el.attributes[name] = String(value);
      if (name === 'class') {
        el.className = String(value);
      }
      if (name.startsWith('data-')) {
        const key = name
          .slice(5)
          .replace(/-([a-z])/g, (_, c) => c.toUpperCase());
        el.dataset[key] = String(value);
      }
    },
    removeAttribute(name) {
      delete el.attributes[name];
      if (name.startsWith('data-')) {
        const key = name
          .slice(5)
          .replace(/-([a-z])/g, (_, c) => c.toUpperCase());
        delete el.dataset[key];
      }
    },
    getAttribute(name) {
      return el.attributes[name];
    },
    addEventListener(type, cb) {
      if (!el._listeners[type]) el._listeners[type] = [];
      el._listeners[type].push(cb);
    },
    dispatch(type, event = {}) {
      const list = el._listeners[type] || [];
      list.forEach((cb) => cb(event));
    },
    closest(selector) {
      // Minimal matcher for our tests
      if (!selector) return null;
      const selectors = selector.split(',').map((s) => s.trim());
      for (const s of selectors) {
        if (s === 'button' && el.tagName === 'BUTTON') return el;
        if (s === 'input' && el.tagName === 'INPUT') return el;
        if (s === 'a' && el.tagName === 'A') return el;
        if (s === 'select' && el.tagName === 'SELECT') return el;
        if (s === 'textarea' && el.tagName === 'TEXTAREA') return el;
      }
      return null;
    },
  };

  return el;
}

// Stub browser globals expected by modules
if (!global.window) {
  global.window = {};
}

global.window.addEventListener = () => {};
global.window.removeEventListener = () => {};
global.window.location = { hostname: 'localhost', origin: 'http://localhost' };

if (!global.performance) {
  global.performance = { now: () => Date.now() };
}

if (!global.requestAnimationFrame) {
  global.requestAnimationFrame = (cb) => setTimeout(cb, 0);
}
if (!global.cancelAnimationFrame) {
  global.cancelAnimationFrame = (id) => clearTimeout(id);
}

if (!global.document) {
  global.document = {};
}

const elementsById = {};
const allTimelineSteps = [];

global.document.activeElement = null;
global.document.addEventListener = (type, cb) => {
  if (!global.document._listeners) global.document._listeners = {};
  if (!global.document._listeners[type]) global.document._listeners[type] = [];
  global.document._listeners[type].push(cb);
};

global.document.dispatch = (type, event) => {
  const list = (global.document._listeners && global.document._listeners[type]) || [];
  list.forEach((cb) => cb(event));
};

global.document.removeEventListener = () => {};

global.document.getElementById = (id) => elementsById[id] || null;

global.document.querySelectorAll = (selector) => {
  if (selector === '.timeline-step') return allTimelineSteps;
  if (selector === '.step[data-status="running"], .step[data-status="starting"], .step[data-status="initiated"]') return [];
  if (selector === '.step') return allTimelineSteps;
  return [];
};

global.document.querySelector = (selector) => {
  const match = selector.match(/^\.run-button\[data-step="([A-Z0-9_]+)"\]$/);
  if (match) {
    const stepKey = match[1];
    return elementsById[`run-${stepKey}`] || null;
  }
  const matchCancel = selector.match(/^\.cancel-button\[data-step="([A-Z0-9_]+)"\]$/);
  if (matchCancel) {
    const stepKey = matchCancel[1];
    return elementsById[`cancel-${stepKey}`] || null;
  }
  return null;
};

// DOMUpdateUtils.escapeHtml requires document.createElement
global.document.createElement = () => {
  let _text = '';
  return {
    set textContent(v) {
      _text = String(v);
    },
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
    // Given: Minimal DOM scaffold for the feature
    const wrapper = createMockElement('DIV', { id: 'workflow-wrapper', classes: ['workflow-wrapper', 'compact-mode'] });
    elementsById['workflow-wrapper'] = wrapper;

    const panel = createMockElement('ASIDE', { id: 'step-details-panel', classes: ['step-details-panel'] });
    panel.hidden = true;
    elementsById['step-details-panel'] = panel;

    const closeBtn = createMockElement('BUTTON', { id: 'close-step-details', classes: ['step-details-close'] });
    elementsById['close-step-details'] = closeBtn;

    const titleEl = createMockElement('DIV', { id: 'step-details-title' });
    elementsById['step-details-title'] = titleEl;

    const statusEl = createMockElement('SPAN', { id: 'step-details-status', classes: ['status-badge', 'status-idle'] });
    statusEl.textContent = 'Prêt';
    elementsById['step-details-status'] = statusEl;

    const timerEl = createMockElement('SPAN', { id: 'step-details-timer', classes: ['timer'] });
    elementsById['step-details-timer'] = timerEl;

    const progressTextEl = createMockElement('DIV', { id: 'step-details-progress-text', classes: ['progress-text-step'] });
    elementsById['step-details-progress-text'] = progressTextEl;

    const runDetailsBtn = createMockElement('BUTTON', { id: 'step-details-run', classes: ['run-button'] });
    runDetailsBtn.disabled = true;
    elementsById['step-details-run'] = runDetailsBtn;

    const cancelDetailsBtn = createMockElement('BUTTON', { id: 'step-details-cancel', classes: ['cancel-button'] });
    cancelDetailsBtn.disabled = true;
    elementsById['step-details-cancel'] = cancelDetailsBtn;

    const logsDetailsBtn = createMockElement('BUTTON', { id: 'step-details-open-logs', classes: ['step-details-open-logs'] });
    logsDetailsBtn.disabled = true;
    elementsById['step-details-open-logs'] = logsDetailsBtn;

    // Step elements + sources that panel mirrors
    const step1 = createMockElement('DIV', {
      id: 'step-STEP1',
      classes: ['step', 'timeline-step'],
      dataset: { stepKey: 'STEP1', stepName: 'Extraction' },
    });
    const step2 = createMockElement('DIV', {
      id: 'step-STEP2',
      classes: ['step', 'timeline-step'],
      dataset: { stepKey: 'STEP2', stepName: 'Conversion' },
    });
    allTimelineSteps.push(step1, step2);
    elementsById['step-STEP1'] = step1;
    elementsById['step-STEP2'] = step2;

    const status1 = createMockElement('SPAN', { id: 'status-STEP1', classes: ['status-badge', 'status-idle'] });
    status1.textContent = 'Prêt';
    elementsById['status-STEP1'] = status1;

    const timer1 = createMockElement('SPAN', { id: 'timer-STEP1', classes: ['timer'] });
    timer1.textContent = '(0s)';
    elementsById['timer-STEP1'] = timer1;

    const ptext1 = createMockElement('DIV', { id: 'progress-text-STEP1', classes: ['progress-text-step'] });
    ptext1.textContent = 'Initialisation';
    elementsById['progress-text-STEP1'] = ptext1;

    const runStep1 = createMockElement('BUTTON', { id: 'run-STEP1', classes: ['run-button'] });
    runStep1.disabled = false;
    runStep1.dataset.step = 'STEP1';
    elementsById['run-STEP1'] = runStep1;

    const cancelStep1 = createMockElement('BUTTON', { id: 'cancel-STEP1', classes: ['cancel-button'] });
    cancelStep1.disabled = true;
    cancelStep1.dataset.step = 'STEP1';
    elementsById['cancel-STEP1'] = cancelStep1;

    // When: Initialize module
    const modUrl = new URL('../../static/stepDetailsPanel.js', import.meta.url);
    const stepDetails = await import(modUrl);
    stepDetails.initializeStepDetailsPanel();

    // When: Click on STEP1
    step1.dispatch('click', { target: step1 });
    await sleep(10);

    // Then: Panel is shown and wrapper toggled
    assert(panel.hidden === false, 'Expected details panel to be visible after click');
    assert(wrapper.classList.contains('details-active') === true, 'Expected wrapper to have details-active');
    assert(panel.dataset.stepKey === 'STEP1', 'Expected panel.dataset.stepKey to be STEP1');

    // Then: Selected step has aria-expanded and selected class
    assert(step1.classList.contains('is-selected') === true, 'Expected STEP1 to have is-selected');
    assert(step1.attributes['aria-expanded'] === 'true', 'Expected STEP1 aria-expanded true');
    assert(step2.attributes['aria-expanded'] === 'false', 'Expected STEP2 aria-expanded false');

    // When: Update underlying status and refresh
    status1.textContent = 'En cours';
    status1.className = 'status-badge status-running';
    stepDetails.refreshStepDetailsPanelIfOpen('STEP1');
    await sleep(10);

    // Then: Panel mirrors status text/class
    assert(statusEl.textContent === 'En cours', 'Expected panel status text to mirror step status');
    assert(statusEl.className === 'status-badge status-running', 'Expected panel status class to mirror step status');

    // When: Close via Escape
    global.document.dispatch('keydown', { key: 'Escape' });
    await sleep(10);

    // Then: Panel closed and focus restored to selected step
    assert(panel.hidden === true, 'Expected details panel hidden after Escape');
    assert(wrapper.classList.contains('details-active') === false, 'Expected wrapper details-active removed');
    assert(step1.classList.contains('is-selected') === false, 'Expected STEP1 is-selected removed');
    assert(global.document.activeElement === step1, 'Expected focus to return to STEP1');

    console.log('Step Details panel test: OK');
    process.exit(0);
  } catch (err) {
    console.error('Step Details panel test failed:', err);
    process.exit(1);
  }
})();
