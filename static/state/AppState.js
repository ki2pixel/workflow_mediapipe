class AppState {
    constructor() {
        this.state = {
            pollingIntervals: {},
            
            activeStepKeyForLogsPanel: null,
            isAnySequenceRunning: false,
            focusedElementBeforePopup: null,
            ui: {
                compactMode: false,
                autoOpenLogOverlay: true
            },
            
            stepTimers: {},
            selectedStepsOrder: [],
            
            processInfo: {},
            
            performanceMetrics: {
                apiResponseTimes: [],
                errorCounts: {},
                lastUpdate: null
            },
            
            cacheStats: {
                hits: 0,
                misses: 0,
                hitRate: 0
            }
        };
        
        this.listeners = new Set();
        this.isDestroyed = false;
        
        this.stateChangeCount = 0;
        this.lastStateChange = Date.now();
        
        console.debug('[AppState] Initialized with immutable state management');
    }
    
    getState() {
        if (this.isDestroyed) {
            console.warn('[AppState] Attempted to access destroyed state');
            return {};
        }
        return this._deepClone(this.state);
    }
    
    getStateProperty(path) {
        if (this.isDestroyed) return undefined;
        
        return path.split('.').reduce((obj, key) => {
            return obj && obj[key] !== undefined ? obj[key] : undefined;
        }, this.state);
    }
    
    setState(updates, source = 'unknown') {
        if (this.isDestroyed) {
            console.warn('[AppState] Attempted to update destroyed state');
            return;
        }
        
        const oldState = this._deepClone(this.state);
        const newState = this._mergeDeep(this.state, updates);
        
        if (this._stateChanged(oldState, newState)) {
            this.state = newState;
            this.stateChangeCount++;
            this.lastStateChange = Date.now();
            
            console.debug(`[AppState] State updated from ${source}:`, updates);
            
            this._notifyListeners(newState, oldState, source);
        }
    }
    
    subscribe(listener) {
        if (typeof listener !== 'function') {
            throw new Error('[AppState] Listener must be a function');
        }
        
        this.listeners.add(listener);
        
        return () => {
            this.listeners.delete(listener);
        };
    }
    
    /**
     * Subscribe to specific state property changes.
     * @param {string} path - Dot-notation path to property
     * @param {Function} listener - Callback function (newValue, oldValue) => void
     * @returns {Function} Unsubscribe function
     */
    subscribeToProperty(path, listener) {
        const propertyListener = (newState, oldState) => {
            const newValue = this._getPropertyByPath(newState, path);
            const oldValue = this._getPropertyByPath(oldState, path);
            
            if (newValue !== oldValue) {
                listener(newValue, oldValue);
            }
        };
        
        return this.subscribe(propertyListener);
    }
    
    batchUpdate(updateFn, source = 'batch') {
        const originalNotify = this._notifyListeners;
        const updates = [];
        
        this._notifyListeners = (newState, oldState, updateSource) => {
            updates.push({ newState, oldState, source: updateSource });
        };
        
        try {
            updateFn();
        } finally {
            this._notifyListeners = originalNotify;
            
            if (updates.length > 0) {
                const finalUpdate = updates[updates.length - 1];
                this._notifyListeners(finalUpdate.newState, updates[0].oldState, source);
            }
        }
    }
    
    reset() {
        const initialState = {
            pollingIntervals: {},
            activeStepKeyForLogsPanel: null,
            isAnySequenceRunning: false,
            focusedElementBeforePopup: null,
            ui: {
                compactMode: false,
                autoOpenLogOverlay: true
            },
            stepTimers: {},
            selectedStepsOrder: [],

            processInfo: {},
            performanceMetrics: {
                apiResponseTimes: [],
                errorCounts: {},
                lastUpdate: null
            },
            cacheStats: {
                hits: 0,
                misses: 0,
                hitRate: 0
            }
        };
        
        this.setState(initialState, 'reset');
        console.info('[AppState] State reset to initial values');
    }
    
    getStats() {
        return {
            listenerCount: this.listeners.size,
            stateChangeCount: this.stateChangeCount,
            lastStateChange: this.lastStateChange,
            isDestroyed: this.isDestroyed,
            stateSize: JSON.stringify(this.state).length
        };
    }
    
    destroy() {
        console.info('[AppState] Destroying state manager');
        
        this.listeners.clear();
        this.state = {};
        this.isDestroyed = true;
    }
    
    _deepClone(obj) {
        if (typeof structuredClone === 'function') {
            try {
                return structuredClone(obj);
            } catch (error) {
                console.warn('[AppState] structuredClone failed, falling back to manual clone:', error);
            }
        }

        if (obj === null || typeof obj !== 'object') {
            return obj;
        }

        if (obj instanceof Date) {
            return new Date(obj.getTime());
        }

        if (Array.isArray(obj)) {
            return obj.map(item => this._deepClone(item));
        }

        const cloned = {};
        for (const key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                cloned[key] = this._deepClone(obj[key]);
            }
        }
        return cloned;
    }
    
    _mergeDeep(target, source) {
        const result = this._deepClone(target);
        
        for (const key in source) {
            if (source.hasOwnProperty(key)) {
                if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                    result[key] = this._mergeDeep(result[key] || {}, source[key]);
                } else {
                    result[key] = source[key];
                }
            }
        }
        
        return result;
    }
    
    _stateChanged(oldState, newState) {
        return !this._areValuesEqual(oldState, newState);
    }

    _areValuesEqual(a, b, visited = new WeakMap()) {
        if (Object.is(a, b)) {
            return true;
        }

        if (typeof a !== typeof b) {
            return false;
        }

        if (a === null || b === null) {
            return false;
        }

        if (typeof a !== 'object') {
            return false;
        }

        if (visited.has(a) && visited.get(a) === b) {
            return true;
        }
        visited.set(a, b);

        const aKeys = Object.keys(a);
        const bKeys = Object.keys(b);
        if (aKeys.length !== bKeys.length) {
            return false;
        }

        for (const key of aKeys) {
            if (!Object.prototype.hasOwnProperty.call(b, key)) {
                return false;
            }
            if (!this._areValuesEqual(a[key], b[key], visited)) {
                return false;
            }
        }

        return true;
    }
    
    _getPropertyByPath(obj, path) {
        return path.split('.').reduce((current, key) => {
            return current && current[key] !== undefined ? current[key] : undefined;
        }, obj);
    }
    
    _notifyListeners(newState, oldState, source) {
        this.listeners.forEach(listener => {
            try {
                listener(newState, oldState, source);
            } catch (error) {
                console.error('[AppState] Listener error:', error);
            }
        });
    }
}

export const appState = new AppState();

window.addEventListener('beforeunload', () => {
    appState.destroy();
});

if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    window.appState = appState;
    
    appState.subscribe((newState, oldState, source) => {
        console.debug(`[AppState] Change from ${source}:`, {
            newState: newState,
            oldState: oldState
        });
    });
}

export default appState;
