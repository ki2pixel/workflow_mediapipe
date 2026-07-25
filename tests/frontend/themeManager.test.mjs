import { assert } from 'console';

const mockLocalStorage = {
    store: {},
    getItem(key) {
        return this.store[key] || null;
    },
    setItem(key, value) {
        this.store[key] = String(value);
    },
    removeItem(key) {
        delete this.store[key];
    },
    clear() {
        this.store = {};
    }
};

global.localStorage = mockLocalStorage;
global.window = {
    location: { hostname: 'localhost' },
    addEventListener: () => {}
};

const docAttributes = {};
global.document = {
    documentElement: {
        setAttribute(name, val) {
            docAttributes[name] = val;
        },
        getAttribute(name) {
            return docAttributes[name];
        }
    },
    getElementById: () => null,
    querySelectorAll: () => [],
    addEventListener: () => {}
};
global.structuredClone = (val) => JSON.parse(JSON.stringify(val));

import { themeManager, THEMES } from '../../static/themeManager.js';

console.log('=== Test ThemeManager Singleton ===');

function runTest() {
    // 1. Verify module export and singleton instance
    assert(themeManager !== undefined, 'themeManager should be exported');
    assert(THEMES !== undefined, 'THEMES should be exported');
    assert(THEMES['dark-pro'] !== undefined, 'THEMES should contain dark-pro');

    // 2. Test applyTheme
    themeManager.applyTheme('light-mode');
    assert(themeManager.getCurrentTheme().id === 'light-mode', 'Current theme should be light-mode');
    assert(docAttributes['data-theme'] === 'light-mode', 'Document data-theme attribute should be set');

    // 3. Test fallback for unknown theme
    themeManager.applyTheme('unknown-invalid-theme');
    assert(themeManager.getCurrentTheme().id === 'dark-pro', 'Unknown theme should fall back to dark-pro');
    assert(docAttributes['data-theme'] === 'dark-pro', 'Document data-theme attribute should fall back to dark-pro');

    console.log('✓ ThemeManager tests passed successfully');
}

runTest();
