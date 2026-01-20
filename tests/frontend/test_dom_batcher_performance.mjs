// DOMBatcher performance/robustness test (Node/ESM)
// No external deps. We stub browser APIs required by DOMBatcher.

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Stub browser globals required by DOMBatcher module scope
if (!global.window) {
  global.window = {};
}
global.window.addEventListener = () => {};
global.window.removeEventListener = () => {};
global.window.location = { hostname: 'localhost' };

// requestAnimationFrame is used as a global function in DOMBatcher
if (!global.requestAnimationFrame) {
  global.requestAnimationFrame = (cb) => setTimeout(cb, 0);
}
if (!global.cancelAnimationFrame) {
  global.cancelAnimationFrame = (id) => clearTimeout(id);
}

// DOMUpdateUtils.escapeHtml uses document.createElement
if (!global.document) {
  global.document = {};
}
global.document.addEventListener = () => {};
global.document.removeEventListener = () => {};
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
    const moduleUrl = new URL('../../static/utils/DOMBatcher.js', import.meta.url);
    const mod = await import(moduleUrl);
    const domBatcher = mod.domBatcher;

    // Given: Preconditions
    let calls = 0;

    // When:  Operation to execute
    domBatcher.scheduleUpdate('one', () => { calls += 1; });
    await sleep(5);

    // Then:  Expected result/verification
    assert(calls === 1, `Expected 1 call after RAF flush, got ${calls}`);

    // Given: Preconditions
    const order = [];

    // When:  Operation to execute
    domBatcher.scheduleUpdate('same-key', () => order.push('first'));
    domBatcher.scheduleUpdate('same-key', () => order.push('second'));
    await sleep(5);

    // Then:  Expected result/verification
    assert(order.length === 1, `Expected single execution for same key, got ${order.length}`);
    assert(order[0] === 'second', `Expected last scheduled function to win, got ${order[0]}`);

    // Given: Preconditions
    const prio = [];

    // When:  Operation to execute
    domBatcher.scheduleUpdate('normal', () => prio.push('normal'), 0);
    domBatcher.scheduleHighPriorityUpdate('high', () => prio.push('high'));
    await sleep(5);

    // Then:  Expected result/verification
    assert(prio.length === 2, `Expected 2 executions, got ${prio.length}`);
    assert(prio[0] === 'high', `Expected high priority first, got ${prio.join(',')}`);

    // Given: Preconditions
    const pendingBefore = domBatcher.getStats().pendingUpdates;

    // When:  Operation to execute
    domBatcher.scheduleUpdate('invalid-fn', null);
    await sleep(5);

    // Then:  Expected result/verification
    const pendingAfter = domBatcher.getStats().pendingUpdates;
    assert(pendingAfter === pendingBefore, 'Expected invalid updateFn not to be scheduled');

    // Given: Preconditions
    domBatcher.scheduleUpdate('cancel-me', () => {});

    // When:  Operation to execute
    const cancelled = domBatcher.cancelUpdate('cancel-me');

    // Then:  Expected result/verification
    assert(cancelled === true, 'Expected cancelUpdate to return true for existing key');
    assert(domBatcher.hasPendingUpdates() === false, 'Expected no pending updates after cancel');

    // Given: Preconditions
    domBatcher.destroy();

    // When:  Operation to execute
    domBatcher.scheduleUpdate('after-destroy', () => {});

    // Then:  Expected result/verification
    assert(domBatcher.getStats().pendingUpdates === 0, 'Expected no scheduling after destroy');

    console.log('DOMBatcher performance/robustness test: OK');
    process.exit(0);
  } catch (err) {
    console.error('DOMBatcher performance/robustness test failed:', err);
    process.exit(1);
  }
})();
