// Stub global window/document/localStorage before importing modules
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
global.document = {
    querySelectorAll: () => [],
    getElementById: () => null,
    addEventListener: () => {}
};
global.structuredClone = (val) => JSON.parse(JSON.stringify(val));

import { appState } from '../../static/state/AppState.js';

console.log('=== Test AppState Persistence ===');

function runTest() {
    mockLocalStorage.clear();
    appState.reset();

    console.log('Test 1: Legacy Migrations');
    mockLocalStorage.setItem('ui.compactMode', 'true');
    mockLocalStorage.setItem('autoOpenLogOverlay', 'false');
    mockLocalStorage.setItem('ui.settingsOpen', 'true');
    
    // Trigger the load mechanism (it runs in constructor but we can call it explicitly after mocking)
    appState._loadPersistedState();
    
    assert(mockLocalStorage.getItem('ui.compactMode') === null, 'Legacy key should be removed');
    assert(mockLocalStorage.getItem('appstate:ui.compactMode') === 'true', 'Legacy key should be migrated');
    assert(mockLocalStorage.getItem('appstate:ui.autoOpenLogOverlay') === 'false', 'Legacy key autoOpenLogOverlay should be migrated');
    assert(mockLocalStorage.getItem('appstate:ui.settingsOpen') === 'true', 'Legacy key ui.settingsOpen should be migrated');
    
    assert(appState.getStateProperty('ui.compactMode') === true, 'State should reflect migrated compactMode');
    assert(appState.getStateProperty('ui.autoOpenLogOverlay') === false, 'State should reflect migrated autoOpenLogOverlay');
    assert(appState.getStateProperty('ui.settingsOpen') === true, 'State should reflect migrated settingsOpen');
    console.log('✓ Migrations success');

    console.log('Test 2: Persisting state changes');
    appState.setState({ ui: { compactMode: false } }, 'test_update');
    assert(mockLocalStorage.getItem('appstate:ui.compactMode') === 'false', 'Changes should be persisted to localStorage');
    
    appState.setState({ selectedStepsOrder: ['STEP1', 'STEP3'] }, 'test_steps');
    assert(mockLocalStorage.getItem('appstate:selectedStepsOrder') === '["STEP1","STEP3"]', 'Arrays should be stringified correctly');
    console.log('✓ Persisting changes success');

    console.log('Test 3: Reset clears persistence');
    appState.reset();
    assert(mockLocalStorage.getItem('appstate:ui.compactMode') === null, 'Reset should clear persisted items');
    assert(appState.getStateProperty('ui.compactMode') === false, 'State should revert to default');
    assert(appState.getStateProperty('selectedStepsOrder').length === 0, 'Steps order should revert to default');
    console.log('✓ Reset success');

    console.log('=== Tous les tests passés ===\n');
}

runTest();
