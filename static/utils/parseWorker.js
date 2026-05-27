// parseWorker.js
// Web Worker for heavy parsing operations (log syntax highlighting and JSON parsing)

const _LOG_LINE_EMPTY_OR_WHITESPACE_PATTERN = /^\s*$/;
const _LOG_TIMESTAMP_PATTERN = /^(?:\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2})/;
const _LOG_ERROR_PATTERN = /(?:erreur|error|échec|failed|exception|critical|fatal|crash)/i;
const _LOG_WARNING_PATTERN = /(?:warning|attention|avertissement|warn|caution|deprecated)/i;
const _LOG_SUCCESS_PATTERN = /(?:success|réussi|terminé|completed|finished|done|✓|✔|ok\b)/i;
const _LOG_INFO_PATTERN = /(?:info|information|démarrage|starting|lancement|initiated|status)/i;
const _LOG_DEBUG_PATTERN = /(?:debug|trace|verbose|détail)/i;
const _LOG_COMMAND_PATTERN = /^(?:commande:|command:|executing:|exécution:|\$|>)/i;
const _LOG_PROGRESS_PATTERN = /(?:\d+%|\d+\/\d+|progress|progression|chargement|loading|téléchargement|downloading)/i;

const _LOG_PATTERNS = [
    { regex: _LOG_ERROR_PATTERN, type: 'error' },
    { regex: _LOG_WARNING_PATTERN, type: 'warning' },
    { regex: _LOG_SUCCESS_PATTERN, type: 'success' },
    { regex: _LOG_PROGRESS_PATTERN, type: 'progress' },
    { regex: _LOG_COMMAND_PATTERN, type: 'command' },
    { regex: _LOG_INFO_PATTERN, type: 'info' },
    { regex: _LOG_TIMESTAMP_PATTERN, type: 'info' },
    { regex: _LOG_DEBUG_PATTERN, type: 'debug' }
];

const _COMPILED_LOG_PATTERNS = _LOG_PATTERNS.map(p => ({
    type: p.type,
    regex: new RegExp(p.regex.source, p.regex.flags)
}));

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
