// parseWorker.js
// Web Worker for heavy parsing operations (log syntax highlighting and JSON parsing)

import { COMPILED_LOG_PATTERNS, LOG_LINE_EMPTY_OR_WHITESPACE_PATTERN } from './logPatterns.js';

const _LOG_LINE_EMPTY_OR_WHITESPACE_PATTERN = LOG_LINE_EMPTY_OR_WHITESPACE_PATTERN;
const _COMPILED_LOG_PATTERNS = COMPILED_LOG_PATTERNS;

/**
 * Fast pure JS HTML escape for Web Workers (without DOM access)
 * @param {string} text 
 * @returns {string}
 */
function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function parseAndStyleLogContent(rawContent) {
    if (!rawContent || typeof rawContent !== 'string') {
        return rawContent || '';
    }

    const lines = rawContent.split('\n');
    const styledLines = new Array(lines.length);

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line === '' || _LOG_LINE_EMPTY_OR_WHITESPACE_PATTERN.test(line)) {
            styledLines[i] = escapeHtml(line);
            continue;
        }

        const escapedLine = escapeHtml(line);

        let logType = 'default';
        for (let j = 0; j < _COMPILED_LOG_PATTERNS.length; j++) {
            const pattern = _COMPILED_LOG_PATTERNS[j];
            if (pattern.regex.test(line)) {
                logType = pattern.type;
                break;
            }
        }

        styledLines[i] = logType !== 'default'
            ? `<span class="log-line log-${logType}">${escapedLine}</span>`
            : escapedLine;
    }

    return styledLines.join('\n');
}

// Listen for messages from the main thread
self.addEventListener('message', (e) => {
    // Sécurité: vérifier l'origine du message
    if (e.origin && e.origin !== self.location.origin) {
        console.warn("[parseWorker] Message ignoré: origine non autorisée", e.origin);
        return;
    }

    const { id, type, payload } = e.data;
    
    try {
        let result = null;
        
        switch (type) {
            case 'parseLogs':
                result = parseAndStyleLogContent(payload);
                break;
            case 'parseJson':
                // Simply parse JSON in the worker thread to offload heavy JSON.parse operations
                result = typeof payload === 'string' ? JSON.parse(payload) : payload;
                break;
            default:
                throw new Error(`Type de message inconnu : ${type}`);
        }
        
        self.postMessage({ id, success: true, result });
    } catch (error) {
        self.postMessage({ id, success: false, error: error.message });
    }
});
