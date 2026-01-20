// Simple test for DOMUpdateUtils.escapeHtml to ensure XSS-safe escaping
// We import from DOMBatcher.js which exports DOMUpdateUtils.

// Stub minimal browser globals expected by DOMBatcher
global.window = {
  addEventListener: () => {},
  removeEventListener: () => {},
  requestAnimationFrame: (cb) => setTimeout(cb, 0),
  cancelAnimationFrame: (id) => clearTimeout(id),
  location: { hostname: 'localhost' },
};
global.document = {
  addEventListener: () => {},
  removeEventListener: () => {},
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
    const moduleUrl = new URL('../../static/utils/DOMBatcher.js', import.meta.url);
    const mod = await import(moduleUrl);
    const { DOMUpdateUtils } = mod;

    const cases = [
      { input: 'Plain text', expected: 'Plain text' },
      { input: '<script>alert(1)</script>', expected: '&lt;script&gt;alert(1)&lt;/script&gt;' },
      { input: 'Hello & goodbye', expected: 'Hello &amp; goodbye' },
      { input: '"double" and \'single\'', expected: '&quot;double&quot; and &#039;single&#039;' },
      { input: '5 > 3 && 2 < 4', expected: '5 &gt; 3 &amp;&amp; 2 &lt; 4' },
    ];

    for (const { input, expected } of cases) {
      const out = DOMUpdateUtils.escapeHtml(input);
      if (out !== expected) {
        console.error(`escapeHtml failed for input: ${input}\nExpected: ${expected}\nGot: ${out}`);
        process.exit(1);
      }
    }

    console.log('DOMUpdateUtils.escapeHtml test: OK');
    process.exit(0);
  } catch (err) {
    console.error('DOMUpdateUtils.escapeHtml test failed:', err);
    process.exit(1);
  }
})();
