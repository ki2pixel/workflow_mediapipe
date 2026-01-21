function assert(condition, message) {
  if (!condition) throw new Error(message || 'Assertion failed');
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
  const children = [];
  const el = {
    tagName: String(tagName || 'DIV').toUpperCase(),
    id: id || '',
    dataset: { ...dataset },
    classList: createClassList(classes),
    className: classes.join(' '),
    attributes: {},
    style: {},
    textContent: '',
    _listeners: {},
    get firstChild() {
      return children.length ? children[0] : null;
    },
    appendChild(child) {
      children.push(child);
      return child;
    },
    removeChild(child) {
      const idx = children.indexOf(child);
      if (idx >= 0) children.splice(idx, 1);
      return child;
    },
    get childNodes() {
      return children;
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
    addEventListener(type, cb) {
      if (!el._listeners[type]) el._listeners[type] = [];
      el._listeners[type].push(cb);
    },
    dispatch(type, event = {}) {
      const list = el._listeners[type] || [];
      list.forEach((cb) => cb(event));
    },
  };

  return el;
}

if (!global.window) global.window = {};

global.window.addEventListener = () => {};
global.window.removeEventListener = () => {};
global.window.location = { hostname: 'localhost', origin: 'http://localhost' };
global.window.innerHeight = 800;

if (!global.localStorage) {
  const store = new Map();
  global.localStorage = {
    getItem(key) {
      return store.has(String(key)) ? store.get(String(key)) : null;
    },
    setItem(key, value) {
      store.set(String(key), String(value));
    },
    removeItem(key) {
      store.delete(String(key));
    },
    clear() {
      store.clear();
    },
  };
}

if (!global.performance) {
  global.performance = { now: () => Date.now() };
}

if (!global.requestAnimationFrame) {
  global.requestAnimationFrame = (cb) => setTimeout(cb, 0);
}

if (!global.document) global.document = {};

const elementsById = {};
const stepElements = [];

global.document.getElementById = (id) => elementsById[id] || null;

global.document.querySelectorAll = (selector) => {
  if (selector === '.step') return stepElements;
  if (selector === '.step[data-status="running"], .step[data-status="starting"], .step[data-status="initiated"]') return [];
  return [];
};

global.document.querySelector = () => null;

global.document.createElement = (tag) => {
  if (tag === 'button') return createMockElement('BUTTON', { classes: [] });
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

global.fetch = async () => ({ ok: true, json: async () => ({ log: [] }) });

(async () => {
  try {
    const wrapper = createMockElement('DIV', { id: 'workflow-wrapper', classes: ['workflow-wrapper', 'compact-mode'] });
    elementsById['workflow-wrapper'] = wrapper;

    const logsColumn = createMockElement('DIV', { id: 'logs-column-global', classes: ['logs-column'] });
    logsColumn.style.removeProperty = () => {};
    elementsById['logs-column-global'] = logsColumn;

    const logPanelTitle = createMockElement('SPAN', { id: 'log-panel-title' });
    elementsById['log-panel-title'] = logPanelTitle;

    const currentStepLogName = createMockElement('SPAN', { id: 'current-step-log-name-panel' });
    elementsById['current-step-log-name-panel'] = currentStepLogName;

    const logPanelContextStep = createMockElement('SPAN', { id: 'log-panel-context-step' });
    const logPanelContextStatus = createMockElement('SPAN', { id: 'log-panel-context-status' });
    const logPanelContextTimer = createMockElement('SPAN', { id: 'log-panel-context-timer' });
    elementsById['log-panel-context-step'] = logPanelContextStep;
    elementsById['log-panel-context-status'] = logPanelContextStatus;
    elementsById['log-panel-context-timer'] = logPanelContextTimer;

    const specificButtons = createMockElement('DIV', { id: 'log-panel-specific-buttons-container' });
    elementsById['log-panel-specific-buttons-container'] = specificButtons;

    const step1 = createMockElement('DIV', {
      id: 'step-STEP1',
      classes: ['step'],
      dataset: { stepKey: 'STEP1', stepName: 'Extraction' },
    });
    stepElements.push(step1);
    elementsById['step-STEP1'] = step1;

    const status1 = createMockElement('SPAN', { id: 'status-STEP1' });
    status1.textContent = 'Prêt';
    elementsById['status-STEP1'] = status1;

    const timer1 = createMockElement('SPAN', { id: 'timer-STEP1' });
    timer1.textContent = '(10s)';
    elementsById['timer-STEP1'] = timer1;

    const modUrl = new URL('../../static/uiUpdater.js', import.meta.url);
    const ui = await import(modUrl);

    ui.setStepsConfig({
      STEP1: {
        display_name: 'Extraction',
        specific_logs: [{ name: 'Log A' }, { name: 'Log B' }],
      },
    });

    ui.setActiveStepForLogPanelUI('STEP1');
    await sleep(10);

    assert(logPanelTitle.textContent === 'Logs: Extraction', 'Expected log panel title to include step name');
    assert(currentStepLogName.textContent === 'Extraction', 'Expected current step log name to be updated');
    assert(logPanelContextStep.textContent === 'Extraction', 'Expected contextual step label to be updated');
    assert(logPanelContextStatus.textContent === 'Prêt', 'Expected contextual status to mirror step status');
    assert(logPanelContextTimer.textContent === '(10s)', 'Expected contextual timer to mirror step timer');

    assert(specificButtons.childNodes.length === 2, 'Expected two specific log buttons');
    assert(specificButtons.childNodes[0].textContent === 'Log A', 'Expected first specific log button label');
    assert(specificButtons.childNodes[1].textContent === 'Log B', 'Expected second specific log button label');

    ui.setActiveStepForLogPanelUI(null);
    await sleep(10);

    assert(logPanelTitle.textContent === 'Logs', 'Expected log panel title reset on clear');
    assert(currentStepLogName.textContent === 'Aucune étape active', 'Expected current step log name reset on clear');
    assert(logPanelContextStep.textContent === 'Aucune étape active', 'Expected contextual step reset on clear');
    assert(specificButtons.childNodes.length === 0, 'Expected specific log buttons cleared on clear');

    console.log('Timeline-Logs Phase 2 test: OK');
    process.exit(0);
  } catch (err) {
    console.error('Timeline-Logs Phase 2 test failed:', err);
    process.exit(1);
  }
})();
