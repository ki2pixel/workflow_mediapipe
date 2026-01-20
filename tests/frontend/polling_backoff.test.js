// Minimal Node-based test for PollingManager adaptive backoff


// Stub global window for _bindCleanupEvents
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

(async () => {
  try {
    const moduleUrl = new URL('../../static/utils/PollingManager.js', import.meta.url);
    const mod = await import(moduleUrl);
    const pollingManager = mod.pollingManager || new mod.PollingManager();

    let callCount = 0;
    let requestedBackoff = false;

    const callback = async () => {
      callCount += 1;
      if (!requestedBackoff) {
        requestedBackoff = true;
        return 120; // request backoff
      }
      return undefined;
    };

    pollingManager.startPolling('testBackoff', callback, 30, { immediate: true, maxErrors: 3 });

    await sleep(50);
    if (!(requestedBackoff && callCount >= 1)) {
      console.error('Expected first callback call and backoff request');
      process.exit(1);
    }

    const countAfterBackoffRequest = callCount;

    await sleep(80); // still within backoff
    if (callCount !== countAfterBackoffRequest) {
      console.error('Polling should be paused during backoff');
      process.exit(1);
    }

    await sleep(70); // total > 120ms from request
    if (callCount <= countAfterBackoffRequest) {
      console.error('Polling did not resume after backoff');
      process.exit(1);
    }

    pollingManager.stopPolling('testBackoff');
    pollingManager.destroy();

    console.log('PollingManager adaptive backoff test: OK');
    process.exit(0);
  } catch (err) {
    console.error('PollingManager adaptive backoff test failed:', err);
    process.exit(1);
  }
})();
