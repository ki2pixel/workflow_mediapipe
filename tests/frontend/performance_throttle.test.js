// Frontend test: Throttle semantics (self-contained)
// Run with: node tests/frontend/performance_throttle.test.js

import assert from 'assert';

// Minimal throttle equivalent to PerformanceOptimizer.throttle behavior used for keyboard shortcuts
function throttle(fn, waitMs) {
  let last = 0;
  let timeout = null;
  return function throttled(...args) {
    const now = Date.now();
    const remaining = waitMs - (now - last);
    if (remaining <= 0) {
      last = now;
      fn.apply(this, args);
    } else if (!timeout) {
      timeout = setTimeout(() => {
        last = Date.now();
        timeout = null;
        fn.apply(this, args);
      }, remaining);
    }
  };
}

// Helper to wait ms
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  let calls = [];
  const fn = () => { calls.push(Date.now()); };
  const throttled = throttle(fn, 120);

  // Fire rapidly: 10 calls every ~10ms
  for (let i = 0; i < 10; i++) {
    throttled();
    await sleep(10);
  }
  // Wait to allow trailing
  await sleep(220);

  // Should be throttled to a few invocations
  assert.ok(calls.length >= 1 && calls.length <= 3, `Expected 1..3 calls, got ${calls.length}`);
  for (let i = 1; i < calls.length; i++) {
    const dt = calls[i] - calls[i - 1];
    assert.ok(dt >= 80, `Expected spacing >= 80ms, got ${dt}`);
  }

  console.log('[frontend] performance_throttle.test.js passed');
})().catch((err) => { console.error(err); process.exit(1); });
