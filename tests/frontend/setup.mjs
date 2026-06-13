// Setup file to stub browser globals in Node.js test environment
globalThis.addEventListener = () => {};
globalThis.removeEventListener = () => {};
globalThis.dispatchEvent = () => {};
globalThis.location = { hostname: 'localhost' };
