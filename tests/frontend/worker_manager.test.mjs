// Frontend worker manager test: ensure fallback works in Node environment
// Node-based, no external deps. We stub browser APIs required by module imports.

// Stub global window/document/localStorage before importing modules
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
  innerHeight: 800,
  innerWidth: 1200,
  pageYOffset: 0,
  scrollTo: () => {},
};

// Worker is NOT defined globally here, simulating Node/Test environment without Worker support
// global.Worker is undefined

// requestAnimationFrame is used as a global function in DOMBatcher
global.requestAnimationFrame = (cb) => setTimeout(cb, 0);
global.cancelAnimationFrame = (id) => clearTimeout(id);

// Minimal Notification stub
global.Notification = {
  permission: 'denied',
  requestPermission: async () => 'denied',
};

// Minimal Audio stub
global.Audio = function () {
  return {
    preload: 'auto',
    volume: 1,
    addEventListener: () => {},
    play: () => Promise.resolve(),
    pause: () => {},
    currentTime: 0,
  };
};

if (!global.performance) {
  global.performance = { now: () => Date.now() };
}

global.document = {
  addEventListener: () => {},
  removeEventListener: () => {},
  getElementById: () => null,
  querySelector: () => null,
  querySelectorAll: () => [],
  documentElement: {
    style: {},
    clientHeight: 800,
    clientWidth: 1200,
    scrollTop: 0,
    scrollHeight: 2000,
  },
  createElement: () => {
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
  },
};

(async () => {
  try {
    const moduleUrl = new URL('../../static/utils/WorkerManager.js', import.meta.url);
    const { workerManager } = await import(moduleUrl);

    // Verify it detects the lack of Web Worker support
    if (workerManager.isSupported) {
      console.error('Expected workerManager.isSupported to be false in Node environment.');
      process.exit(1);
    }

    // Test fallback for JSON parsing
    const jsonStr = '{"status": "ok"}';
    const parsedJson = await workerManager.parseJson(jsonStr);
    if (parsedJson.status !== 'ok') {
      console.error('JSON fallback parsing failed');
      process.exit(1);
    }

    // Test fallback for log parsing
    const logStr = 'Erreur critique 404\nLancement du processus';
    const styledHtml = await workerManager.parseLogs(logStr);
    
    if (!styledHtml.includes('log-error') || !styledHtml.includes('log-info')) {
      console.error('Log fallback parsing failed or missing expected styling:', styledHtml);
      process.exit(1);
    }

    console.log('WorkerManager fallback test: OK');
    process.exit(0);
  } catch (err) {
    console.error('WorkerManager test failed:', err);
    process.exit(1);
  }
})();
