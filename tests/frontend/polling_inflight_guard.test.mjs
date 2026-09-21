// Node-based tests for PollingManager in-flight guard and error recovery.
// Context: overlapping polls used to stack requests and starve the browser
// connection pool while a large download saturated the server, freezing
// unrelated widgets until the backlog drained.

globalThis.addEventListener = () => {};
globalThis.dispatchEvent = () => {};

global.window = {
  addEventListener: () => {},
  removeEventListener: () => {},
};

global.document = {
  addEventListener: () => {},
  removeEventListener: () => {},
};

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

let failures = 0;

function check(condition, message) {
  if (!condition) {
    console.error(`FAIL: ${message}`);
    failures += 1;
  }
}

const moduleUrl = new URL('../../static/utils/PollingManager.js', import.meta.url);
const mod = await import(moduleUrl);

// --- Test 1: a slow callback never overlaps itself -------------------------
{
  const manager = new mod.PollingManager();
  let concurrent = 0;
  let maxConcurrent = 0;
  let callCount = 0;

  const slowCallback = async () => {
    callCount += 1;
    concurrent += 1;
    maxConcurrent = Math.max(maxConcurrent, concurrent);
    await sleep(60);
    concurrent -= 1;
  };

  manager.startPolling('slow', slowCallback, 10, { immediate: true });
  await sleep(200);

  const ops = manager.getActiveOperations();
  const slowOps = ops.intervals.find((entry) => entry.name === 'slow');

  check(maxConcurrent === 1, `expected no overlapping runs, got ${maxConcurrent}`);
  check(callCount <= 4, `expected ticks to be skipped, got ${callCount} runs in 200ms`);
  check(!!slowOps, 'expected the poller to stay registered');
  check((slowOps?.skippedTicks || 0) > 0, 'expected skipped ticks to be reported');

  manager.destroy();
}

// --- Test 2: transient errors must not stop the poller --------------------
{
  const manager = new mod.PollingManager();
  let callCount = 0;
  let errorCount = 0;

  globalThis.addEventListener = () => {};
  const flakyCallback = async () => {
    callCount += 1;
    if (callCount <= 2) {
      errorCount += 1;
      throw new Error('server busy');
    }
  };

  manager.startPolling('flaky', flakyCallback, 10, { immediate: true, maxErrors: 5 });
  await sleep(300);

  const ops = manager.getActiveOperations();
  const flakyOps = ops.intervals.find((entry) => entry.name === 'flaky');

  check(errorCount === 2, `expected 2 errors, got ${errorCount}`);
  check(callCount >= 3, `expected polling to resume after errors, got ${callCount} runs`);
  check(!!flakyOps, 'poller was stopped after transient errors');
  check((flakyOps?.errorCount || 0) === 0, 'error counter should reset after a success');

  manager.destroy();
}

if (failures > 0) {
  console.error(`PollingManager in-flight guard test: ${failures} failure(s)`);
  process.exit(1);
}

console.log('PollingManager in-flight guard test: OK');
process.exit(0);
