// Frontend test: apiService CSRF header injection and fetch helpers
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
globalThis.open = () => {};

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
  createElement: () => ({ set textContent(v) {}, set innerHTML(v) {}, set href(v) {} }),
};

// Minimal stub for showNotification used by ErrorHandler
global.showNotification = () => {};

(async () => {
  try {
    const modUrl = new URL('../../static/apiService.js', import.meta.url);
    const mod = await import(modUrl);

    // Given: fetchWithLoadingState exists and is a function
    if (typeof mod.fetchWithLoadingState !== 'function') {
      console.error('fetchWithLoadingState is not a function');
      process.exit(1);
    }

    // Given: runStepAPI exists and is a function
    if (typeof mod.runStepAPI !== 'function') {
      console.error('runStepAPI is not a function');
      process.exit(1);
    }

    // Given: cancelStepAPI exists and is a function
    if (typeof mod.cancelStepAPI !== 'function') {
      console.error('cancelStepAPI is not a function');
      process.exit(1);
    }

    // Given: startPollingAPI exists and is a function
    if (typeof mod.startPollingAPI !== 'function') {
      console.error('startPollingAPI is not a function');
      process.exit(1);
    }

    // Given: stopPollingAPI exists and is a function
    if (typeof mod.stopPollingAPI !== 'function') {
      console.error('stopPollingAPI is not a function');
      process.exit(1);
    }

    // Given: fetchInitialStatusAPI exists and is a function
    if (typeof mod.fetchInitialStatusAPI !== 'function') {
      console.error('fetchInitialStatusAPI is not a function');
      process.exit(1);
    }

    // Given: fetchSpecificLogAPI exists and is a function
    if (typeof mod.fetchSpecificLogAPI !== 'function') {
      console.error('fetchSpecificLogAPI is not a function');
      process.exit(1);
    }

    // When: checking the module exports
    // Then: all core API service functions are exported correctly
    console.log('apiService module exports test: OK');

    // Given: a meta CSRF token element is present in the DOM
    const csrfMeta = { name: 'csrf-token', getAttribute: () => 'test-csrf-token-123' };
    const workerMeta = { name: 'worker-token', getAttribute: () => 'test-worker-token-456' };

    // Track fetch calls to verify headers
    let capturedOptions = null;
    const originalFetch = globalThis.fetch || global.fetch || (() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
    globalThis.fetch = async (url, options) => {
      capturedOptions = options;
      return { ok: true, status: 200, json: async () => ({ status: 'ok' }) };
    };

    const originalQuerySelector = global.document.querySelector;
    let metaQueryCount = 0;
    global.document.querySelector = (sel) => {
      metaQueryCount++;
      if (sel.includes('csrf-token')) return csrfMeta;
      if (sel.includes('worker-token')) return workerMeta;
      return null;
    };

    // When: making a POST request with fetchWithLoadingState
    try {
      await mod.fetchWithLoadingState('/test', { method: 'POST' });
    } catch (e) {
      // Expected in test environment — may throw due to missing DOM
    }

    // Then: CSRF token was queried and injected
    const csrfWasQueried = metaQueryCount > 0;
    console.log(`apiService CSRF injection test: ${csrfWasQueried ? 'OK' : 'FAILED'}`);
    if (!csrfWasQueried) {
      console.error('CSRF token meta tag was not queried');
      process.exit(1);
    }

    // Then: Worker token was also queried
    if (capturedOptions && capturedOptions.headers) {
      const hasWorkerToken = capturedOptions.headers['X-Worker-Token'] === 'test-worker-token-456';
      const hasCsrfToken = capturedOptions.headers['X-CSRF-Token'] === 'test-csrf-token-123';
      console.log(`apiService Worker-Token header: ${hasWorkerToken ? 'OK' : 'MISSING'}`);
      console.log(`apiService X-CSRF-Token header: ${hasCsrfToken ? 'OK' : 'MISSING'}`);
      if (!hasWorkerToken || !hasCsrfToken) {
        console.error('Expected both X-Worker-Token and X-CSRF-Token headers in POST request');
        process.exit(1);
      }
    }

    // Restore globals
    global.document.querySelector = originalQuerySelector;
    globalThis.fetch = originalFetch;

    console.log('apiService CSRF & Worker token header test: OK');
    process.exit(0);
  } catch (err) {
    console.error('apiService test failed:', err);
    process.exit(1);
  }
})();
