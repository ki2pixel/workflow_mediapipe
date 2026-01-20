// Frontend test (CJS): fetchWithLoadingState
// Run with: node tests/frontend/loading_state_fetch.test.cjs

const assert = require('assert');

// Minimal DOM/button stub
function makeButton(id) {
  return {
    id,
    disabled: false,
    attrs: {},
    setAttribute(name, value) { this.attrs[name] = String(value); },
    removeAttribute(name) { delete this.attrs[name]; }
  };
}

// Local, self-contained version of fetchWithLoadingState (no optional chaining)
async function fetchWithLoadingState(url, options, buttonElOrId) {
  let btn = null;
  if (typeof buttonElOrId === 'string' && typeof document !== 'undefined') {
    btn = document.getElementById(buttonElOrId);
  } else if (buttonElOrId && buttonElOrId.nodeType === 1) {
    btn = buttonElOrId;
  }
  try {
    if (btn) { btn.setAttribute('data-loading', 'true'); btn.disabled = true; }
    const response = await fetch(url, options || {});
    let data = {};
    try { data = await response.json(); } catch (e) { data = {}; }
    if (!response.ok) {
      throw new Error((data && data.message) || ('Erreur HTTP ' + response.status));
    }
    return data;
  } finally {
    if (btn) { btn.removeAttribute('data-loading'); btn.disabled = false; }
  }
}

// Install minimal global document + fetch stubs
const btn = makeButton('test-button');
const doc = {
  getElementById: (id) => (id === 'test-button' ? btn : null)
};
global.document = doc;

(async () => {
  // Success case
  {
    let fetchCalled = 0;
    global.fetch = async (url, options) => ({
      ok: (++fetchCalled && true),
      status: 200,
      async json() { return { ok: true, url: url, method: (options && options.method) || 'GET' }; }
    });

    assert.equal(btn.disabled, false);
    assert.equal(btn.attrs['data-loading'], undefined);

    const data = await fetchWithLoadingState('/api/ping', { method: 'POST' }, 'test-button');

    assert.equal(fetchCalled, 1);
    assert.equal(data.ok, true);
    assert.equal(btn.disabled, false);
    assert.equal(btn.attrs['data-loading'], undefined);
  }

  // Error case
  {
    global.fetch = async () => ({ ok: false, status: 500, async json() { return { message: 'server error' }; } });
    let threw = false;
    try {
      await fetchWithLoadingState('/api/fail', { method: 'GET' }, 'test-button');
    } catch (e) {
      threw = true;
      const msg = (e && e.message) ? e.message : String(e);
      assert.match(String(msg), /server error|Erreur HTTP/);
    }
    assert.equal(threw, true);
    assert.equal(btn.disabled, false);
    assert.equal(btn.attrs['data-loading'], undefined);
  }

  console.log('[frontend] loading_state_fetch.test.cjs passed');
})().catch((err) => { console.error(err); process.exit(1); });
