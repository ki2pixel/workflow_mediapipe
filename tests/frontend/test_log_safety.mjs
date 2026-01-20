// Frontend security test: ensure parseAndStyleLogContent escapes HTML to prevent XSS
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

// requestAnimationFrame is used as a global function in DOMBatcher
global.requestAnimationFrame = (cb) => setTimeout(cb, 0);
global.cancelAnimationFrame = (id) => clearTimeout(id);

// Minimal Notification stub (utils.js can reference window.Notification)
global.Notification = {
  permission: 'denied',
  requestPermission: async () => 'denied',
};

// Minimal Audio stub (soundManager may instantiate Audio when called)
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

// Provide performance.now (Node has it, but keep safe fallback)
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
    // Given: Preconditions
    const input = '<img src=x onerror=alert(1)><script>alert(2)</script>';

    // When:  Operation to execute
    const moduleUrl = new URL('../../static/uiUpdater.js', import.meta.url);
    const mod = await import(moduleUrl);
    const out = mod.parseAndStyleLogContent(input);

    // Then:  Expected result/verification
    if (typeof out !== 'string') {
      console.error('Expected string output');
      process.exit(1);
    }
    if (out.includes('<img') || out.includes('<script')) {
      console.error('Output contains unescaped HTML tags:', out);
      process.exit(1);
    }
    if (!out.includes('&lt;img') || !out.includes('&lt;script')) {
      console.error('Expected escaped HTML entities in output:', out);
      process.exit(1);
    }

    console.log('parseAndStyleLogContent XSS safety test: OK');
    process.exit(0);
  } catch (err) {
    console.error('parseAndStyleLogContent XSS safety test failed:', err);
    process.exit(1);
  }
})();
