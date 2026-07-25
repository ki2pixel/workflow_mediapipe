// Frontend test: uiUpdater step card rendering and log panel utilities
// Node ESM — stubs browser globals required by module imports

global.localStorage = {
  _data: new Map(),
  getItem: function (k) { return this._data.has(k) ? this._data.get(k) : null; },
  setItem: function (k, v) { this._data.set(k, String(v)); },
  removeItem: function (k) { this._data.delete(k); },
};

global.window = {
  addEventListener: () => {},
  removeEventListener: () => {},
  location: { hostname: 'localhost' },
  innerHeight: 800, innerWidth: 1200,
  pageYOffset: 0,
  scrollTo: () => {},
};
globalThis.addEventListener = () => {};
globalThis.dispatchEvent = () => {};
globalThis.location = global.window.location;

global.requestAnimationFrame = (cb) => setTimeout(cb, 0);
global.cancelAnimationFrame = (id) => clearTimeout(id);
global.Notification = { permission: 'denied', requestPermission: async () => 'denied' };
global.Audio = function () { return { preload: 'auto', volume: 1, addEventListener: () => {}, play: () => Promise.resolve(), pause: () => {}, currentTime: 0 }; };
if (!global.performance) global.performance = { now: () => Date.now() };

global.document = {
  addEventListener: () => {},
  removeEventListener: () => {},
  getElementById: () => null,
  querySelector: () => null,
  querySelectorAll: () => [],
  documentElement: { style: {}, clientHeight: 800, clientWidth: 1200, scrollTop: 0, scrollHeight: 2000 },
  createElement: () => ({
    set textContent(v) {},
    set innerHTML(v) {},
    classList: { add: () => {}, remove: () => {}, contains: () => false },
    style: {},
    setAttribute: () => {},
    getAttribute: () => null,
    addEventListener: () => {},
    appendChild: () => {},
    cloneNode: () => ({}),
  }),
};

// Stub showNotification used by various modules
global.showNotification = () => {};

// Minimal Worker stub
global.Worker = undefined; // No Worker in test = fallback path

// Provide structuredClone if missing
if (typeof structuredClone === 'undefined') {
  global.structuredClone = (obj) => JSON.parse(JSON.stringify(obj));
}

(async () => {
  try {
    const modUrl = new URL('../../static/uiUpdater.js', import.meta.url);
    const mod = await import(modUrl);

    // Given: uiUpdater exports its core functions
    if (typeof mod.openLogPanelUI !== 'function') {
      console.error('openLogPanelUI is not exported');
      process.exit(1);
    }
    if (typeof mod.closeLogPanelUI !== 'function') {
      console.error('closeLogPanelUI is not exported');
      process.exit(1);
    }
    if (typeof mod.updateStepCardUI !== 'function') {
      console.error('updateStepCardUI is not exported');
      process.exit(1);
    }
    if (typeof mod.updateMainLogOutputUI !== 'function') {
      console.error('updateMainLogOutputUI is not exported');
      process.exit(1);
    }
    if (typeof mod.updateGlobalUIForSequenceState !== 'function') {
      console.error('updateGlobalUIForSequenceState is not exported');
      process.exit(1);
    }

    // Given: parseAndStyleLogContent is re-exported from the shared logParserUtils
    if (typeof mod.parseAndStyleLogContent !== 'function') {
      console.error('parseAndStyleLogContent is not re-exported from uiUpdater');
      process.exit(1);
    }

    // When: calling parseAndStyleLogContent with log content
    const result = mod.parseAndStyleLogContent('INFO: Starting process\nerreur critique: failure');

    // Then: it returns styled HTML with proper log classes
    if (!result.includes('log-info')) {
      console.error('Expected log-info class for INFO line, got:', result);
      process.exit(1);
    }
    if (!result.includes('log-error')) {
      console.error('Expected log-error class for erreur line, got:', result);
      process.exit(1);
    }

    // Then: HTML is escaped for XSS safety
    if (result.includes('<script>')) {
      console.error('Raw HTML tags should be escaped:', result);
      process.exit(1);
    }

    // Given: empty or falsy input
    const emptyResult = mod.parseAndStyleLogContent('');
    if (emptyResult !== '') {
      console.error('Empty input should return empty string, got:', emptyResult);
      process.exit(1);
    }

    const nullResult = mod.parseAndStyleLogContent(null);
    if (nullResult !== '') {
      console.error('Null input should return empty string, got:', nullResult);
      process.exit(1);
    }

    console.log('uiUpdater module exports and log parsing test: OK');

    // Given: setStepsConfig exists for configuring step metadata
    if (typeof mod.setStepsConfig !== 'function') {
      console.error('setStepsConfig is not exported');
      process.exit(1);
    }
    mod.setStepsConfig({
      STEP1: { display_name: 'Extraction', specific_logs: [] },
      STEP2: { display_name: 'Conversion', specific_logs: [] },
    });

    // Given: getStepsConfig returns the previously set config
    if (typeof mod.getStepsConfig !== 'function') {
      console.error('getStepsConfig is not exported');
      process.exit(1);
    }
    const config = mod.getStepsConfig();
    if (!config || !config.STEP1 || config.STEP1.display_name !== 'Extraction') {
      console.error('getStepsConfig returned unexpected value:', config);
      process.exit(1);
    }

    console.log('uiUpdater steps config test: OK');
    process.exit(0);
  } catch (err) {
    console.error('uiUpdater test failed:', err);
    process.exit(1);
  }
})();
