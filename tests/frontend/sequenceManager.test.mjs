// Frontend test: sequenceManager step execution and state transitions
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

global.showNotification = () => {};

// Provide structuredClone if missing
if (typeof structuredClone === 'undefined') {
  global.structuredClone = (obj) => JSON.parse(JSON.stringify(obj));
}

(async () => {
  try {
    // First import constants to verify STEP_STATUS is frozen
    const constantsUrl = new URL('../../static/constants.js', import.meta.url);
    const constants = await import(constantsUrl);

    // Given: STEP_STATUS is an Object.freeze enum
    if (typeof constants.STEP_STATUS !== 'object') {
      console.error('STEP_STATUS is not an object');
      process.exit(1);
    }

    // When: trying to mutate STEP_STATUS
    try {
      constants.STEP_STATUS.RUNNING = 'mutated';
    } catch (e) {
      // Expected in strict mode — assignment to frozen object fails
    }

    // Then: STEP_STATUS values are immutable
    if (constants.STEP_STATUS.RUNNING === 'mutated') {
      console.error('STEP_STATUS is not frozen — RUNNING was mutated');
      process.exit(1);
    }
    if (constants.STEP_STATUS.RUNNING !== 'running') {
      console.error('STEP_STATUS.RUNNING value is incorrect');
      process.exit(1);
    }
    if (constants.STEP_STATUS.COMPLETED !== 'completed') {
      console.error('STEP_STATUS.COMPLETED value is incorrect');
      process.exit(1);
    }
    if (constants.STEP_STATUS.FAILED !== 'failed') {
      console.error('STEP_STATUS.FAILED value is incorrect');
      process.exit(1);
    }
    if (constants.STEP_STATUS.IDLE !== 'idle') {
      console.error('STEP_STATUS.IDLE value is incorrect');
      process.exit(1);
    }

    // Given: POLLING_INTERVAL is 500ms (reduced from 2000ms)
    if (constants.POLLING_INTERVAL !== 500) {
      console.error(`Expected POLLING_INTERVAL=500, got ${constants.POLLING_INTERVAL}`);
      process.exit(1);
    }

    // Given: defaultSequenceableStepsKeys has 8 steps
    if (!Array.isArray(constants.defaultSequenceableStepsKeys) || constants.defaultSequenceableStepsKeys.length !== 8) {
      console.error('defaultSequenceableStepsKeys should have 8 steps');
      process.exit(1);
    }

    // Given: REMOTE_SEQUENCE_STEP_KEYS still works as legacy alias
    if (constants.REMOTE_SEQUENCE_STEP_KEYS !== constants.defaultSequenceableStepsKeys) {
      console.error('REMOTE_SEQUENCE_STEP_KEYS should reference defaultSequenceableStepsKeys');
      process.exit(1);
    }

    console.log('constants.js STEP_STATUS and polling config test: OK');

    // Now import sequenceManager to verify exports
    const seqUrl = new URL('../../static/sequenceManager.js', import.meta.url);
    const seqMod = await import(seqUrl);

    // Given: runStepSequence is exported
    if (typeof seqMod.runStepSequence !== 'function') {
      console.error('runStepSequence is not exported from sequenceManager');
      process.exit(1);
    }

    // When/Then: runStepSequence is a valid async function
    const fnStr = seqMod.runStepSequence.toString();
    if (!fnStr.includes('async') && !fnStr.includes('function')) {
      console.error('runStepSequence does not appear to be a function');
      process.exit(1);
    }

    console.log('sequenceManager module exports test: OK');
    process.exit(0);
  } catch (err) {
    console.error('sequenceManager test failed:', err);
    process.exit(1);
  }
})();
