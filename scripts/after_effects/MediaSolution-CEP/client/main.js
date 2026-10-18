/* Media Solution v12.0 CEP - Main JavaScript */
(function() {
    'use strict';

    // Global state
    var csInterface = new CSInterface();

    // Configuration par défaut (appliquée quand aucun stockage persistant n'est disponible,
    // p. ex. panel fermé avant redémarrage d'AE → localStorage purgé)
    var DEFAULT_CONFIG = {
        version: "12.0.0",
        pythonCmd: '',
        enablePythonCutsParser: true,
        enableAutoRecentering: true,
        enablePythonAnalyzer: true,
        enablePythonRecentering: true,
        enablePythonProjectOpen: true,
        enablePythonBaseAepCreation: true,
        enablePyAepCuts: true,
        enableLogFile: true
    };

    var state = {
        folderPath: '',
        folderPaths: [],
        detectedFolders: [],
        csvPath: '',
        isBatchRunning: false,
        bridgeOk: null,
        bridgeLastError: '',
        pythonTransport: 'mailbox',
        pipeName: null,
        isSpawningDaemon: false,
        lastDaemonSpawnAt: null,
        hasError: false,
        errorMessage: '',
        targetOk: false,
        targetComp: '',
        targetLayer: '',
        config: {
            version: "12.0.0",
            pythonCmd: '',
            enablePythonCutsParser: true,
            enableAutoRecentering: true,
            enablePythonAnalyzer: true,
            enablePythonRecentering: true,
            enablePythonProjectOpen: true,
            enablePythonBaseAepCreation: true,
            enablePyAepCuts: true,
            enableLogFile: true
        }
    };

    // DOM Elements
    var elements = {};

    // Initialize
    function init() {
        try {
            if (supportsNodeRequire()) {
                try {
                    csInterface.evalScript('checkPyShiftBridgeHealth()', function(res) {
                        // Résultat de santé consigné dans le panneau (pas d'écriture disque externe)
                        console.log('ExtendScript checkPyShiftBridgeHealth result:', res);
                    });
                } catch(eJson) {}
            }
            cacheElements();
            loadConfig();
            bindEvents();
            setupCSInterface();
            addLog('Media Solution v12.0 CEP - Initialisé', 'info');
            startBridgeHealthMonitoring();
            updateUI();
            updateActiveTarget();
            window.setInterval(function() {
                if (document.hidden) return;
                if (state.isBatchRunning) return; // pas de polling pendant le batch
                updateActiveTarget();
            }, 10000);
        } catch (e) {
            console.error("Erreur d'initialisation de l'extension:", e);
            try {
                addLog("Erreur d'initialisation : " + e.toString(), "error");
            } catch (e2) {}
        }
    }

    function supportsNodeRequire() {
        return typeof require === 'function';
    }

    // Échappe une valeur pour injection comme littéral chaîne dans un appel evalScript
    function safeString(value) {
        return String(value === null || value === undefined ? '' : value)
            .replace(/\\/g, "\\\\")
            .replace(/"/g, '\\"')
            .replace(/\r/g, "\\r")
            .replace(/\n/g, "\\n");
    }

    // evalScript avec garde anti-blocage : callback + timeout de sécurité
    function evalScriptWithTimeout(script, callback, timeoutMs) {
        callback = callback || function () {};
        var settled = false;
        function finish(res) {
            if (settled) return;
            settled = true;
            callback(res);
        }
        csInterface.evalScript(script, function (res) {
            finish(res);
        });
        window.setTimeout(function () {
            finish(null);
        }, timeoutMs || 30000);
    }

    function getPipeName() {
        // Pipe nommé Windows exposé par bridge_daemon.py (\\.\pipe\mediasolution) :
        // transport basse latence, détecté au health check. L'ancien nom CEPy
        // (com.psc.MediaSolution-CEP) n'est conservé que si l'utilisateur l'a
        // configuré explicitement (localStorage) ; le mode nominal reste mailbox
        // tant que le daemon n'est pas lancé.
        try {
            return localStorage.getItem('pyshift_pipe_name') || 'mediasolution';
        } catch (e) {
            return 'mediasolution';
        }
    }

    function getPipePath(name) {
        name = String(name || '');
        if (!name) name = 'mediasolution';
        var isWin = typeof process !== 'undefined' && process.platform === 'win32';
        if (isWin) {
            return '\\\\.\\pipe\\' + name;
        }
        if (name.indexOf('/') !== -1) {
            return name;
        }
        return '/tmp/' + name;
    }

    function detectPythonTransport(callback) {
        callback = callback || function () { };
        if (!supportsNodeRequire()) {
            state.pythonTransport = 'mailbox';
            state.pipeName = null;
            callback(false);
            return;
        }

        var name = getPipeName();
        state.pipeName = name;
        sendCommandToPythonPipe('ping', {}, 800, function (res) {
            var ok = !!(res && res.ok && res.result && res.result.status === 'ok');
            if (ok) {
                state.pythonTransport = 'pipe';
                state.pipeName = name;
            } else {
                state.pythonTransport = 'mailbox';
                state.pipeName = null;
            }
            callback(ok);
        });
     }

    function startPythonDaemon() {
        if (state.isSpawningDaemon) return;
        if (!supportsNodeRequire()) return;
        // Espace minimum de 60 s entre deux spawns : le daemon met ~10 s à démarrer
        // (imports lourds), un seul spawn suffit. Empêche la course de respawn en boucle.
        var now = new Date().getTime();
        if (state.lastDaemonSpawnAt && (now - state.lastDaemonSpawnAt) < 60000) {
            return;
        }
        state.lastDaemonSpawnAt = now;
        
        try {
            var cp = require('child_process');
            var path = require('path');
            var os = require('os');
            var fs = require('fs');
            
            var docDir = path.join(os.homedir(), 'Documents');
            // Recherche portable du script du démon : dossier Documents/Scripts/PyShiftBridge d'abord,
            // puis recherche de l'installation PyShiftBridge dans Documents.
            var daemonScript = path.join(docDir, 'Scripts', 'PyShiftBridge', 'bridge_daemon.py');

            if (!fs.existsSync(daemonScript)) {
                var found = findPyShiftBridgeDaemon(docDir);
                if (found) daemonScript = found;
            }

            if (!fs.existsSync(daemonScript)) {
                addLog('Démon Python introuvable sur le disque.', 'error');
                return;
            }

            // pythonCmd configuré par l'utilisateur, sinon résolution depuis le PATH
            var pythonExe = resolvePythonExe();
            if (!pythonExe) {
                addLog('Aucun exécutable Python trouvé. Configurez le chemin dans les paramètres.', 'error');
                return;
            }

            state.isSpawningDaemon = true;
            addLog('Démarrage du démon Python : ' + pythonExe + ' ' + daemonScript, 'info');
            
            var child;
            try {
                child = cp.spawn(pythonExe, [daemonScript], {
                    detached: true,
                    stdio: 'ignore',
                    windowsHide: true
                });
            } catch (e) {
                state.isSpawningDaemon = false;
                addLog('Erreur démarrage démon: ' + e.toString(), 'error');
                return;
            }
            child.on('error', function (err) {
                state.isSpawningDaemon = false;
                addLog('Erreur spawn démon Python: ' + err.toString(), 'error');
            });
            child.unref();
            
            window.setTimeout(function() {
                state.isSpawningDaemon = false;
                addLog('Démon Python démarré en arrière-plan.', 'success');
                // Le daemon crée le pipe ~2-3 s après son démarrage : on reteste
                // plusieurs fois (4 s, 8 s, 12 s) pour basculer en pipe sans
                // attendre le health check suivant.
                var attempts = 0;
                function retestPipe() {
                    attempts++;
                    sendCommandToPythonPipe('ping', {}, 1500, function (resPipe) {
                        var pipeOk = !!(resPipe && resPipe.ok && resPipe.result && resPipe.result.status === 'ok');
                        if (pipeOk) {
                            state.pythonTransport = 'pipe';
                            state.pipeName = getPipeName();
                            state.bridgeOk = true;
                            state.bridgeLastError = '';
                            addLog('Transport PyShiftBridge: pipe (\\\\.\\pipe\\' + state.pipeName + ')', 'success');
                            updateUI();
                        } else if (!pipeOk && attempts < 3) {
                            window.setTimeout(retestPipe, 4000);
                        }
                    });
                }
                window.setTimeout(retestPipe, 4000);
            }, 3000);
        } catch (e) {
            state.isSpawningDaemon = false;
            addLog('Erreur démarrage démon: ' + e.toString(), 'error');
        }
    }

    // Résout l'exécutable Python à utiliser pour le démon :
    // 1. pythonCmd configuré (si le fichier existe)
    // 2. 'python' / 'py -3' si un interpréteur existe dans le PATH
    // (vérifié via `where`, sans exécuter de code Python)
    function resolvePythonExe() {
        try {
            var fs = require('fs');
            var configured = state.config.pythonCmd || '';
            if (configured && fs.existsSync(configured)) {
                return configured;
            }

            var cp = require('child_process');
            var candidates = ['python', 'py -3'];
            for (var i = 0; i < candidates.length; i++) {
                try {
                    var found = cp.execSync('where ' + candidates[i], { stdio: ['ignore', 'pipe', 'ignore'] });
                    if (found && found.length > 0) {
                        var first = found.toString().split(/\r?\n/)[0];
                        if (first && first.trim().length > 0) {
                            return first.trim();
                        }
                    }
                } catch (e) { }
            }
        } catch (e) { }
        return null;
    }

    // Recherche récursive (profondeur 4) du script bridge_daemon.py sous Documents,
    // pour couvrir les installations PyShiftBridge locales (site-packages, Scripts, etc.)
    function findPyShiftBridgeDaemon(rootDir) {
        try {
            var fs = require('fs');
            var path = require('path');
            var priorityPath = path.join(rootDir, 'Scripts', 'PyShiftBridge', 'bridge_daemon.py');
            if (fs.existsSync(priorityPath)) return priorityPath;

            var queue = [rootDir];
            var maxDepth = 4;
            var depth = 0;
            while (queue.length > 0 && depth < maxDepth) {
                var next = [];
                for (var i = 0; i < queue.length; i++) {
                    var dir = queue[i];
                    var entries;
                    try { entries = fs.readdirSync(dir); } catch (e) { continue; }
                    for (var k = 0; k < entries.length; k++) {
                        var full = path.join(dir, entries[k]);
                        var stat;
                        try { stat = fs.statSync(full); } catch (e) { continue; }
                        if (stat.isDirectory() && entries[k].indexOf('node_modules') === -1 && entries[k] !== 'AppData') {
                            next.push(full);
                        } else if (stat.isFile() && entries[k] === 'bridge_daemon.py' && full.indexOf('PyShiftBridge') !== -1) {
                            return full;
                        }
                    }
                }
                queue = next;
                depth++;
            }
        } catch (e) {}
        return null;
    }

    function sendCommandToPythonPipe(entrypoint, args, timeoutMs, callback) {
        callback = callback || function () { };
        timeoutMs = timeoutMs || 3000;

        if (!supportsNodeRequire()) {
            callback({ ok: false, result: null, error: 'node_require_unavailable' });
            return;
        }

        // Le serveur pipe (bridge_daemon._pipe_serve_one) ferme le pipe après chaque
        // connexion servie puis le recrée dans la boucle main() : pendant cette fenêtre
        // (quelques centaines de ms), un connect client échoue en ENOENT alors que le
        // daemon est vivant. On retente quelques fois avant de conclure à un échec.
        // Les autres erreurs (timeout, EPIPE, réponse invalide) ne sont PAS retentées.
        var attempts = 0;
        var maxAttempts = 3;
        var retryDelayMs = 250;

        function attempt() {
            attempts++;
            doPipeAttempt(entrypoint, args, timeoutMs, function (res) {
                if (res && res.ok === false && res.error && String(res.error).indexOf('ENOENT') !== -1 && attempts < maxAttempts) {
                    window.setTimeout(attempt, retryDelayMs);
                    return;
                }
                callback(res);
            });
        }
        attempt();
    }

    function doPipeAttempt(entrypoint, args, timeoutMs, callback) {
        callback = callback || function () { };
        timeoutMs = timeoutMs || 3000;

        if (!supportsNodeRequire()) {
            callback({ ok: false, result: null, error: 'node_require_unavailable' });
            return;
        }

        try {
            var net = require('net');
            if (!net || typeof net.Socket !== 'function') {
                throw new Error('net.Socket is not available in require("net")');
            }

            var name = state.pipeName || getPipeName();
            var pipePath = getPipePath(name);

            var client = new net.Socket();
            var buffer = '';
            var settled = false;
            var connectionTimeout = null;

            function cleanup() {
                if (connectionTimeout) {
                    window.clearTimeout(connectionTimeout);
                    connectionTimeout = null;
                }
                try { client.removeAllListeners(); } catch (e) { }
                try { client.destroy(); } catch (e) { }
            }

            function finishOk(obj) {
                if (settled) return;
                settled = true;
                cleanup();
                callback(obj);
            }

            function finishErr(msg) {
                if (settled) return;
                settled = true;
                cleanup();
                callback({ ok: false, result: null, error: String(msg || 'pipe_error') });
            }

            client.setTimeout(timeoutMs);
            client.on('timeout', function () { finishErr('pipe_timeout'); });
            client.on('error', function (err) { finishErr(err); });
            client.on('data', function (chunk) {
                buffer += chunk.toString();
                var idx = buffer.indexOf('\n');
                if (idx === -1) return;
                var raw = buffer.substring(0, idx);
                try {
                    var parsed = JSON.parse(raw);
                    if (parsed && typeof parsed === 'object' && typeof parsed.ok !== 'undefined') {
                        if (typeof parsed.result === 'string') {
                            try {
                                var inner = JSON.parse(parsed.result);
                                if (inner && typeof inner === 'object' && typeof inner.ok !== 'undefined') {
                                    finishOk(inner);
                                    return;
                                }
                            } catch (e2) {}
                        }
                        finishOk(parsed);
                    } else if (parsed && typeof parsed === 'object') {
                        finishOk({ ok: true, result: parsed, error: null });
                    } else {
                        finishOk({ ok: true, result: parsed, error: null });
                    }
                } catch (e) {
                    finishErr('pipe_invalid_response');
                }
            });

            connectionTimeout = window.setTimeout(function () {
                finishErr('pipe_connection_timeout');
            }, timeoutMs);

            client.connect(pipePath, function () {
                if (connectionTimeout) {
                    window.clearTimeout(connectionTimeout);
                    connectionTimeout = null;
                }
                var payload = {
                    endpoint: 'Response',
                    functionName: entrypoint,
                    args: { param1: JSON.stringify(args || {}) }
                };
                client.write(JSON.stringify(payload) + '\n');
            });
        } catch (e) {
            callback({ ok: false, result: null, error: 'pipe_init_failed: ' + e.toString() });
        }
    }

    // Ping mailbox via Node.js : écrit cep_to_py.json, attend la réponse
    // py_to_cep.json avec l'id correspondant. Lecture UTF-8 fiable (BOM géré).
    function sendCommandToPythonMailbox(entrypoint, args, timeoutMs, callback) {
        callback = callback || function () { };
        timeoutMs = timeoutMs || 3000;
        if (!supportsNodeRequire()) {
            callback({ ok: false, result: null, error: 'node_require_unavailable' });
            return;
        }
        try {
            var fs = require('fs');
            var path = require('path');
            var os = require('os');
            var bridgeDir = path.join(os.homedir(), 'Documents', 'PyShiftAE_CEP_Bridge');
            var reqPath = path.join(bridgeDir, 'cep_to_py.json');
            var respPath = path.join(bridgeDir, 'py_to_cep.json');

            var msgId = String(new Date().getTime()) + '-' + String(Math.floor(Math.random() * 100000));
            var payload = JSON.stringify({ id: msgId, entrypoint: entrypoint, args: args || {} });

            fs.writeFileSync(reqPath, payload, 'utf8');

            var start = new Date().getTime();
            var timer = null;
            function poll() {
                if (new Date().getTime() - start >= timeoutMs) {
                    callback({ ok: false, result: null, error: 'mailbox_timeout' });
                    return;
                }
                try {
                    var raw = fs.readFileSync(respPath, 'utf8');
                    // Le daemon écrit avec BOM (pour ExtendScript) : on le retire pour JSON.parse
                    if (raw.charCodeAt(0) === 0xFEFF) {
                        raw = raw.substring(1);
                    }
                    var parsed = JSON.parse(raw);
                    if (parsed && parsed.id === msgId) {
                        callback({
                            ok: parsed.ok === true,
                            result: parsed.result || null,
                            error: parsed.error || null
                        });
                        return;
                    }
                } catch (e) { /* pas encore de réponse valide */ }
                timer = window.setTimeout(poll, 200);
            }
            poll();
        } catch (e) {
            callback({ ok: false, result: null, error: 'mailbox_init_failed: ' + e.toString() });
        }
    }

    // Cache DOM elements
    function cacheElements() {
        elements = {
            statusIndicator: document.getElementById('statusIndicator'),
            statusDot: document.querySelector('.status-dot'),
            statusText: document.querySelector('.status-text'),
            folderPath: document.getElementById('folderPath'),
            folderList: document.getElementById('folderList'),
            folderListContainer: document.getElementById('folderListContainer'),
            selectAllFolders: document.getElementById('selectAllFolders'),
            deselectAllFolders: document.getElementById('deselectAllFolders'),
            clearFolders: document.getElementById('clearFolders'),
            browseFolder: document.getElementById('browseFolder'),
            autoDetectFolders: document.getElementById('autoDetectFolders'),
            folderInfo: document.getElementById('folderInfo'),
            pythonCmd: document.getElementById('pythonCmd'),
            enablePythonCutsParser: document.getElementById('enablePythonCutsParser'),
            bridgeHealthDot: document.getElementById('bridgeHealthDot'),
            enableAutoRecentering: document.getElementById('enableAutoRecentering'),
            enablePythonAnalyzer: document.getElementById('enablePythonAnalyzer'),
            enablePythonRecentering: document.getElementById('enablePythonRecentering'),
            enablePythonProjectOpen: document.getElementById('enablePythonProjectOpen'),
            enablePythonBaseAepCreation: document.getElementById('enablePythonBaseAepCreation'),
            enablePyAepCuts: document.getElementById('enablePyAepCuts'),
            enableLogFile: document.getElementById('enableLogFile'),
            exportConfig: document.getElementById('exportConfig'),
            importConfig: document.getElementById('importConfig'),
            startBatch: document.getElementById('startBatch'),
            startBatchPipe: document.getElementById('startBatchPipe'),
            cancelBatch: document.getElementById('cancelBatch'),
            runDiagnostics: document.getElementById('runDiagnostics'),
            batchProgress: document.getElementById('batchProgress'),
            progressFill: document.getElementById('progressFill'),
            progressText: document.getElementById('progressText'),
            csvPath: document.getElementById('csvPath'),
            browseCsv: document.getElementById('browseCsv'),
            applyCuts: document.getElementById('applyCuts'),
            cutsTargetInfo: document.getElementById('cutsTargetInfo'),
            refreshTarget: document.getElementById('refreshTarget'),
            cutsModeInfo: document.getElementById('cutsModeInfo'),
            bridgeHealthText: document.getElementById('bridgeHealthText'),
            bridgeRecoveryInfo: document.getElementById('bridgeRecoveryInfo'),
            restartBridge: document.getElementById('restartBridge'),
            logsContainer: document.getElementById('logsContainer'),
            clearLogs: document.getElementById('clearLogs'),
            exportLogs: document.getElementById('exportLogs'),
            logFilter: document.getElementById('logFilter')
        };
    }

    // Setup CSInterface
    function setupCSInterface() {
        // UN SEUL ÉCOUTEUR ROBUSTE
        csInterface.addEventListener('com.workflowmediapipe.mediasolution.hostMessage', function(event) {
            try {
                // Vérification si donnée valide
                if (!event.data || event.data === "undefined") return;
                
                // Si c'est déjà un objet (certaines versions de CEP le font auto), on l'utilise
                if (typeof event.data === "object") {
                    handleHostMessage(event.data);
                    return;
                }

                // Si c'est une string mal formée [object Object], on l'ignore proprement
                if (typeof event.data === "string") {
                    if (event.data === "[object Object]") {
                        console.warn("Reçu [object Object] du host - Ignoré");
                        return;
                    }
                    var data = JSON.parse(event.data);
                    handleHostMessage(data);
                }
            } catch (e) {
                console.error("Erreur parsing:", e);
                // On n'affiche plus l'erreur dans le panel pour éviter le spam visuel si un event est malformé
            }
        });

        // Set theme
        try {
            var hostEnv = window.__adobe_cep__.getHostEnvironment();
            if (hostEnv) {
                var skinInfo = JSON.parse(hostEnv).appSkinInfo;
                updateTheme(skinInfo);
            }
        } catch (e) {
            console.error("Erreur getHostEnvironment/updateTheme:", e);
        }

        csInterface.addEventListener('com.adobe.csxs.events.ThemeChanged', function(event) {
            try {
                var hostEnv = window.__adobe_cep__.getHostEnvironment();
                if (hostEnv) {
                    var skinInfo = JSON.parse(hostEnv).appSkinInfo;
                    updateTheme(skinInfo);
                }
            } catch (e) {
                console.error("Erreur ThemeChanged:", e);
            }
        });
    }

    // Update theme based on AE theme
    function updateTheme(skinInfo) {
        var basePanelColor = skinInfo.panelBackgroundColor.color;
        var baseTextColor = skinInfo.panelTextColor.color;
        var r = basePanelColor.red;
        var g = basePanelColor.green;
        var b = basePanelColor.blue;
        
        var bgColor = 'rgb(' + r + ',' + g + ',' + b + ')';
        var textColor = 'rgb(' + baseTextColor.red + ',' + baseTextColor.green + ',' + baseTextColor.blue + ')';
        
        document.documentElement.style.setProperty('--panel-bg', bgColor);
        document.documentElement.style.setProperty('--panel-text', textColor);
        
        // Calculate brightness (0-255)
        var brightness = (r * 299 + g * 587 + b * 114) / 1000;
        
        if (brightness < 128) {
            document.documentElement.classList.remove('theme-light');
            document.documentElement.classList.add('theme-dark');
        } else {
            document.documentElement.classList.remove('theme-dark');
            document.documentElement.classList.add('theme-light');
        }
    }

    // Bind events
    function bindEvents() {
        elements.browseFolder.addEventListener('click', selectFolder);
        if (elements.autoDetectFolders) {
            elements.autoDetectFolders.addEventListener('click', autoDetectFolders);
        }
        if (elements.selectAllFolders) {
            elements.selectAllFolders.addEventListener('click', function() { selectAllFolders(true); });
        }
        if (elements.deselectAllFolders) {
            elements.deselectAllFolders.addEventListener('click', function() { selectAllFolders(false); });
        }
        if (elements.clearFolders) {
            elements.clearFolders.addEventListener('click', clearFolders);
        }
        elements.exportConfig.addEventListener('click', exportConfig);
        elements.importConfig.addEventListener('click', importConfig);
        elements.startBatch.addEventListener('click', startBatch);
        if (elements.startBatchPipe) {
            elements.startBatchPipe.addEventListener('click', startBatchViaPipe);
        }
        elements.cancelBatch.addEventListener('click', cancelBatch);
        elements.runDiagnostics.addEventListener('click', runDiagnostics);
        elements.browseCsv.addEventListener('click', selectCsv);
        elements.applyCuts.addEventListener('click', applyCuts);
        elements.clearLogs.addEventListener('click', clearLogs);
        elements.exportLogs.addEventListener('click', exportLogs);
        elements.pythonCmd.addEventListener('change', updateConfig);
        elements.enablePythonCutsParser.addEventListener('change', updateConfig);
        elements.enableAutoRecentering.addEventListener('change', updateConfig);
        elements.enablePythonAnalyzer.addEventListener('change', updateConfig);
        elements.enablePythonRecentering.addEventListener('change', updateConfig);
        if (elements.enablePythonProjectOpen) {
            elements.enablePythonProjectOpen.addEventListener('change', updateConfig);
        }
        if (elements.enablePythonBaseAepCreation) {
            elements.enablePythonBaseAepCreation.addEventListener('change', updateConfig);
        }
        if (elements.enablePyAepCuts) {
            elements.enablePyAepCuts.addEventListener('change', updateConfig);
        }
        if (elements.enableLogFile) {
            elements.enableLogFile.addEventListener('change', updateConfig);
        }
        if (elements.restartBridge) {
            elements.restartBridge.addEventListener('click', restartBridge);
        }
        if (elements.refreshTarget) {
            elements.refreshTarget.addEventListener('click', updateActiveTarget);
        }
        if (elements.logFilter) {
            elements.logFilter.addEventListener('change', filterLogs);
        }
        var cutsSection = document.querySelector('.cuts-section');
        if (cutsSection) {
            // Débounce 250 ms : le survol ne déclenche pas un evalScript à chaque mouseenter/focusin
            var targetDebounceTimer = null;
            function scheduleTargetUpdate() {
                if (state.isBatchRunning) return; // pas de evalScript pendant le batch
                if (targetDebounceTimer) window.clearTimeout(targetDebounceTimer);
                targetDebounceTimer = window.setTimeout(function() {
                    targetDebounceTimer = null;
                    updateActiveTarget();
                }, 250);
            }
            cutsSection.addEventListener('mouseenter', scheduleTargetUpdate);
            cutsSection.addEventListener('focusin', scheduleTargetUpdate);
        }
    }

    // Update status
    function updateStatus(status, text) {
        if(elements.statusDot) elements.statusDot.className = 'status-dot ' + status;
        if(elements.statusText) elements.statusText.textContent = text;
    }

    // Add log entry
    function addLog(message, type) {
        type = type || 'info';
        var logEntry = document.createElement('div');
        logEntry.className = 'log-entry ' + type;
        
        var prefix = '';
        if (type === 'error') prefix = '[ERREUR] ';
        else if (type === 'warning') prefix = '[AVERTISSEMENT] ';
        else if (type === 'success') prefix = '[SUCCÈS] ';
        else if (type === 'python') prefix = '[PYTHON] ';
        else prefix = '[INFO] ';

        logEntry.textContent = new Date().toLocaleTimeString() + ' - ' + prefix + message;
        
        if (elements.logFilter) {
            var filterValue = elements.logFilter.value;
            if (filterValue !== 'all' && type !== filterValue) {
                logEntry.style.display = 'none';
            }
        }
        
        var isAtBottom = (elements.logsContainer.scrollHeight - elements.logsContainer.clientHeight - elements.logsContainer.scrollTop) < 20;
        
        elements.logsContainer.appendChild(logEntry);
        
        if (isAtBottom) {
            elements.logsContainer.scrollTop = elements.logsContainer.scrollHeight;
        }
    }

    // Handle messages from ExtendScript
    function handleHostMessage(data) {
        // Log discret dans la console JS, pas dans l'UI pour éviter le spam
        console.log('Message reçu:', data);

        if (!data || typeof data !== 'object') return;

        switch (data.type) {
            case 'log':
                addLog(data.message, data.level || 'info');
                break;
            case 'progress':
                updateProgress(data.current, data.total, data.message, data.folder);
                break;
            case 'foldersSelected':
                if (data.success === false) {
                    if (data.error && data.error !== 'Aucun dossier sélectionné') {
                        addLog('Erreur dossiers: ' + data.error, 'warning');
                    }
                } else if ((data.folders && data.folders.length > 0) || (data.paths && data.paths.length > 0)) {
                    var incomingFolders = [];
                    if (data.folders && data.folders.length > 0) {
                        incomingFolders = data.folders.map(function(f) {
                            var pClean = f.path.replace(/\\/g, '/');
                            return {
                                path: pClean,
                                name: f.name || pClean.substring(pClean.lastIndexOf('/') + 1),
                                videoCount: f.videoCount,
                                checked: f.checked !== false
                            };
                        });
                    } else if (data.paths && data.paths.length > 0) {
                        incomingFolders = data.paths.map(function(p) {
                            var pClean = p.replace(/\\/g, '/');
                            return {
                                path: pClean,
                                name: pClean.substring(pClean.lastIndexOf('/') + 1),
                                videoCount: undefined,
                                checked: true
                            };
                        });
                    }

                    var merged = (state.detectedFolders || []).slice();
                    incomingFolders.forEach(function(item) {
                        var found = false;
                        for (var m = 0; m < merged.length; m++) {
                            if (merged[m].path === item.path) {
                                if (item.videoCount !== undefined) merged[m].videoCount = item.videoCount;
                                merged[m].name = item.name;
                                found = true;
                                break;
                            }
                        }
                        if (!found) {
                            merged.push(item);
                        }
                    });

                    state.detectedFolders = merged;
                    renderFolderList();
                    if (elements.folderInfo) {
                        elements.folderInfo.textContent = data.info || '';
                    }
                    state.hasError = false;
                    state.errorMessage = '';
                    updateUI();
                    addLog('Dossiers listés: ' + state.detectedFolders.length + ' (' + state.folderPaths.length + ' coché(s))', 'success');
                } else {
                    state.detectedFolders = [];
                    state.folderPaths = [];
                    state.folderPath = '';
                    renderFolderList();
                    if (elements.folderInfo) {
                        elements.folderInfo.textContent = data.info || '';
                    }
                    updateUI();
                    addLog(data.info || 'Aucun dossier détecté', 'warning');
                }
                break;
            case 'csvSelected':
                if (data.path) {
                    state.csvPath = data.path;
                    elements.csvPath.value = data.path;
                    state.hasError = false;
                    state.errorMessage = '';
                    updateUI();
                    addLog('CSV OK: ' + data.path, 'success');
                }
                break;
            case 'batchCompleted':
                state.isBatchRunning = false;
                state.hasError = false;
                state.errorMessage = '';
                updateUI();
                if (data.folder) {
                    addLog('Batch terminé: ' + data.results + ' (' + data.folder + ')', 'success');
                } else {
                    addLog('Batch terminé: ' + data.results, 'success');
                }
                break;
            case 'error':
                addLog(data.message, 'error');
                state.isBatchRunning = false;
                state.hasError = true;
                state.errorMessage = data.message || 'Erreur';
                updateUI();
                break;
        }
    }

    function updateProgress(current, total, message, folder) {
        var percentage = total > 0 ? (current / total) * 100 : 0;
        elements.progressFill.style.width = percentage + '%';
        elements.progressText.textContent = message || (current + ' / ' + total);
        if (folder) {
            elements.progressText.textContent = folder + ' - ' + (message || (current + ' / ' + total));
        }
        if (elements.batchProgress) {
            elements.batchProgress.setAttribute('aria-valuenow', Math.round(percentage));
        }
    }

    function syncCheckedFolders() {
        if (!state.detectedFolders) state.detectedFolders = [];
        var checked = state.detectedFolders.filter(function(item) {
            return item.checked !== false;
        });
        state.folderPaths = checked.map(function(item) {
            return item.path;
        });
        if (state.folderPaths.length > 0) {
            state.folderPath = state.folderPaths[state.folderPaths.length - 1];
        } else {
            state.folderPath = '';
        }

        if (elements.folderPath) {
            if (state.detectedFolders.length === 0) {
                elements.folderPath.value = '';
            } else if (state.folderPaths.length === 0) {
                elements.folderPath.value = 'Aucun dossier coché (0 / ' + state.detectedFolders.length + ')';
            } else if (state.folderPaths.length === 1 && state.detectedFolders.length === 1) {
                elements.folderPath.value = state.detectedFolders[0].name || state.detectedFolders[0].path;
            } else {
                elements.folderPath.value = state.folderPaths.length + ' / ' + state.detectedFolders.length + ' dossier(s) coché(s)';
            }
        }

        updateUI();
    }

    function renderFolderList() {
        if (!elements.folderList || !elements.folderListContainer) return;
        elements.folderList.innerHTML = '';

        if (!state.detectedFolders || state.detectedFolders.length === 0) {
            elements.folderListContainer.classList.add('is-hidden');
            elements.folderListContainer.style.display = 'none';
            if (elements.folderPath) elements.folderPath.value = '';
            syncCheckedFolders();
            return;
        }

        elements.folderListContainer.classList.remove('is-hidden');
        elements.folderListContainer.style.display = 'block';

        state.detectedFolders.forEach(function(item, idx) {
            var li = document.createElement('li');
            li.className = 'folder-list-item';

            var chk = document.createElement('input');
            chk.type = 'checkbox';
            chk.className = 'folder-checkbox';
            chk.id = 'chk_folder_' + idx;
            chk.checked = item.checked !== false;
            chk.title = 'Sélectionner ce dossier pour le batch';
            chk.addEventListener('change', function() {
                item.checked = chk.checked;
                syncCheckedFolders();
            });

            var lbl = document.createElement('label');
            lbl.htmlFor = chk.id;
            lbl.className = 'folder-list-label';

            var nameSpan = document.createElement('span');
            nameSpan.className = 'folder-list-name';
            nameSpan.textContent = item.name || item.path;
            lbl.appendChild(nameSpan);

            if (item.videoCount !== undefined) {
                var detailsSpan = document.createElement('span');
                detailsSpan.className = 'folder-list-details';
                detailsSpan.textContent = item.videoCount + ' vidéo(s)';
                lbl.appendChild(detailsSpan);
            }

            var removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'btn btn-secondary btn-xs folder-remove';
            removeBtn.textContent = '✕';
            removeBtn.title = 'Retirer ce dossier de la liste';
            removeBtn.addEventListener('click', function(ev) {
                ev.preventDefault();
                ev.stopPropagation();
                removeFolder(item.path);
            });

            li.title = item.path;
            li.appendChild(chk);
            li.appendChild(lbl);
            li.appendChild(removeBtn);
            elements.folderList.appendChild(li);
        });

        syncCheckedFolders();
    }

    function removeFolder(path) {
        if (!state.detectedFolders) return;
        state.detectedFolders = state.detectedFolders.filter(function(item) {
            return item.path !== path;
        });
        renderFolderList();
        addLog('Dossier retiré: ' + path, 'info');
    }

    function clearFolders() {
        state.detectedFolders = [];
        state.folderPaths = [];
        state.folderPath = '';
        renderFolderList();
        if (elements.folderInfo) elements.folderInfo.textContent = '';
        addLog('Liste des dossiers effacée', 'info');
    }

    function selectAllFolders(checked) {
        if (!state.detectedFolders || state.detectedFolders.length === 0) return;
        state.detectedFolders.forEach(function(item) {
            item.checked = checked;
        });
        renderFolderList();
        addLog(checked ? 'Tous les dossiers ont été cochés' : 'Tous les dossiers ont été décochés', 'info');
    }

    function updateUI() {
        var hasFolder = state.folderPaths.length > 0;
        var hasDetected = state.detectedFolders && state.detectedFolders.length > 0;
        var hasCsv = state.csvPath.length > 0;
        var bridgeUnknown = state.bridgeOk === null;
        var bridgeOffline = state.bridgeOk === false;
        
        elements.startBatch.disabled = !hasFolder || state.isBatchRunning;
        if (elements.startBatchPipe) {
            var pipeOk = isPipeAvailable();
            elements.startBatchPipe.disabled = !hasFolder || state.isBatchRunning || !pipeOk;
            elements.startBatchPipe.title = pipeOk ? 'Batch via pipe (transport fiable)' : 'Pipe non disponible - utiliser Démarrer Batch';
        }
        elements.cancelBatch.disabled = !state.isBatchRunning;
        elements.runDiagnostics.disabled = !hasFolder || state.isBatchRunning;
        elements.applyCuts.disabled = !hasCsv || state.isBatchRunning || !state.targetOk;
        if (elements.clearFolders) {
            elements.clearFolders.disabled = !hasDetected || state.isBatchRunning;
        }
        if (elements.selectAllFolders) {
            elements.selectAllFolders.disabled = !hasDetected || state.isBatchRunning;
        }
        if (elements.deselectAllFolders) {
            elements.deselectAllFolders.disabled = !hasDetected || state.isBatchRunning;
        }
        if (elements.autoDetectFolders) {
            elements.autoDetectFolders.disabled = state.isBatchRunning;
        }
        if (elements.batchProgress) {
            elements.batchProgress.style.display = state.isBatchRunning ? 'block' : 'none';
        }

        if (elements.enablePythonProjectOpen) {
            elements.enablePythonProjectOpen.disabled = (bridgeOffline || bridgeUnknown) || state.isBatchRunning;
        }

        if (elements.enablePythonBaseAepCreation) {
            elements.enablePythonBaseAepCreation.disabled = (bridgeOffline || bridgeUnknown) || state.isBatchRunning;
        }

        if (elements.enablePyAepCuts) {
            elements.enablePyAepCuts.disabled = (bridgeOffline || bridgeUnknown) || state.isBatchRunning;
        }

        if (elements.bridgeHealthDot) {
            var dotClass = 'daemon-dot';
            var healthText = 'Vérification...';
            var recoveryDisplay = 'none';
            if (bridgeOffline) {
                dotClass += ' error';
                healthText = 'Indisponible';
                recoveryDisplay = 'block';
            } else if (bridgeUnknown) {
                dotClass += ' working';
                healthText = 'Vérification...';
                recoveryDisplay = 'none';
            } else {
                dotClass += ' ready';
                healthText = 'Connecté';
                recoveryDisplay = 'none';
            }
            elements.bridgeHealthDot.className = dotClass;
            if (elements.bridgeHealthText) {
                elements.bridgeHealthText.textContent = healthText;
            }
            if (elements.bridgeRecoveryInfo) {
                elements.bridgeRecoveryInfo.style.display = recoveryDisplay;
            }
        }
        
        var cutsMode = getCutsMode();
        var cutsModeText = '';
        if (cutsMode === 'py_aep') {
            cutsModeText = 'Mode : Python offline (py_aep - sauvegarde requise)';
        } else if (cutsMode === 'hybrid') {
            cutsModeText = 'Mode : Hybride (Calcul Python + AE)';
        } else {
            cutsModeText = 'Mode : ExtendScript local (Fallback)';
        }
        if (elements.cutsModeInfo) {
            elements.cutsModeInfo.textContent = cutsModeText;
        }
        
        if (state.isBatchRunning) {
            updateStatus('working', 'Traitement...');
        } else if (state.hasError) {
            updateStatus('error', state.errorMessage || 'Erreur');
        } else {
            updateStatus('ready', 'Prêt');
        }
    }

    function getEffectiveConfigForHost() {
        var cfg = {
            pythonCmd: state.config.pythonCmd,
            enablePythonCutsParser: state.config.enablePythonCutsParser,
            enableAutoRecentering: state.config.enableAutoRecentering,
            enablePythonAnalyzer: state.config.enablePythonAnalyzer,
            enablePythonRecentering: state.config.enablePythonRecentering,
            enablePythonProjectOpen: state.config.enablePythonProjectOpen,
            enablePythonBaseAepCreation: state.config.enablePythonBaseAepCreation,
            enablePyAepCuts: state.config.enablePyAepCuts,
            enableLogFile: state.config.enableLogFile
        };

        if (state.bridgeOk !== true) {
            cfg.enablePythonCutsParser = false;
            cfg.enablePythonAnalyzer = false;
            cfg.enablePythonRecentering = false;
            cfg.enablePythonProjectOpen = false;
            cfg.enablePythonBaseAepCreation = false;
            cfg.enablePyAepCuts = false;
        }

        return cfg;
    }

    function startBridgeHealthMonitoring() {
        state.bridgeOk = null;
        state.bridgeLastError = '';
        detectPythonTransport(function (pipeOk) {
            var transportLabel = state.pythonTransport || (pipeOk ? 'pipe' : 'mailbox');
            addLog('Transport PyShiftBridge: ' + transportLabel, pipeOk ? 'success' : 'info');
            checkBridgeHealthOnce();
        });
        window.setInterval(checkBridgeHealthOnce, 30000);
    }

    function checkBridgeHealthOnce() {
        // Pas de ping pendant le batch : le host manipule app.project (close/open),
        // un evalScript concurrent peut geler AE
        if (state.isBatchRunning) return;

        if (state.pythonTransport === 'pipe') {
            sendCommandToPythonPipe('ping', {}, 1500, function (res) {
                var ok = !!(res && res.ok);
                if (ok) {
                    state.bridgeOk = true;
                    state.bridgeLastError = '';
                    updateUI();
                    return;
                }

                state.pythonTransport = 'mailbox';
                state.pipeName = null;
                addLog('Transport PyShiftBridge: mailbox (pipe perdu)', 'info');
                csInterface.evalScript('checkPyShiftBridgeHealth()', function (result) {
                    var ok2 = false;
                    var payload = null;
                    try {
                        if (result && result !== 'undefined' && result !== 'null') {
                            payload = JSON.parse(result);
                        }
                    } catch (e) {
                        payload = null;
                    }

                    ok2 = !!(payload && payload.ok);
                    state.bridgeOk = ok2;
                    state.bridgeLastError = (!ok2 && payload && payload.error) ? payload.error : '';
                    updateUI();
                    if (!ok2 && !state.isSpawningDaemon) {
                        startPythonDaemon();
                    }
                });
            });
            return;
        }

        // Health check mailbox : ping Node direct (fiable), repli host si Node absent
        if (supportsNodeRequire()) {
            sendCommandToPythonMailbox('ping', {}, 5000, function (res) {
                var ok = !!(res && res.ok && res.result && res.result.status === 'ok');
                state.bridgeOk = ok;
                state.bridgeLastError = (!ok && res && res.error) ? res.error : '';
                updateUI();
                if (!ok && !state.isSpawningDaemon) {
                    startPythonDaemon();
                    return;
                }
                // Le daemon est vivant : on tente un upgrade vers le pipe nommé
                // (basse latence). Si le pipe répond, on bascule ; sinon on
                // reste en mailbox (le daemon peut être une vieille instance
                // sans serveur pipe).
                if (ok && state.pythonTransport === 'mailbox') {
                    sendCommandToPythonPipe('ping', {}, 1500, function (resPipe) {
                        var pipeOk = !!(resPipe && resPipe.ok && resPipe.result && resPipe.result.status === 'ok');
                        if (pipeOk) {
                            state.pythonTransport = 'pipe';
                            state.pipeName = getPipeName();
                            addLog('Transport PyShiftBridge: pipe (\\\\.\\pipe\\' + state.pipeName + ')', 'success');
                            updateUI();
                        }
                    });
                }
            });
            return;
        }

        csInterface.evalScript('checkPyShiftBridgeHealth()', function (result) {
            var ok = false;
            var payload = null;
            try {
                if (result && result !== 'undefined' && result !== 'null') {
                    payload = JSON.parse(result);
                }
            } catch (e) {
                payload = null;
            }

            ok = !!(payload && payload.ok);
            state.bridgeOk = ok;
            state.bridgeLastError = (!ok && payload && payload.error) ? payload.error : '';

            updateUI();

            if (!ok && !state.isSpawningDaemon) {
                startPythonDaemon();
            }
        });
    }

    // Calls to ExtendScript
    function selectFolder() {
        state.hasError = false;
        state.errorMessage = '';
        updateUI();
        addLog('Sélection des dossiers...', 'info');
        var pathsJson = JSON.stringify(state.folderPaths);
        pathsJson = pathsJson.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
        csInterface.evalScript('selectFolders("' + pathsJson + '")', function(result) {
            // Le résultat est traité via l'event foldersSelected,
            // on vérifie seulement que l'injection a bien abouti.
            if (!result || result === 'undefined' || result === 'null' || (typeof result === 'string' && result.indexOf('EvalScript error') !== -1)) {
                state.hasError = true;
                state.errorMessage = 'La sélection de dossiers a échoué côté ExtendScript';
                updateUI();
            } else {
                try {
                    var parsed = (typeof result === 'object') ? result : JSON.parse(result);
                    if (parsed && parsed.type === 'foldersSelected') {
                        handleHostMessage(parsed);
                    }
                } catch (eParse) {}
            }
        });
    }

    function runNodeAutoDetectFallback() {
        if (!supportsNodeRequire()) {
            state.hasError = true;
            state.errorMessage = 'La détection automatique a échoué côté ExtendScript';
            updateUI();
            return;
        }
        try {
            var fs = require('fs');
            var path = require('path');
            var rootDir = 'F:\\';
            if (!fs.existsSync(rootDir)) {
                addLog('Lecteur F:\\ non accessible via Node.js', 'warning');
                state.hasError = true;
                state.errorMessage = 'Lecteur F:\\ non accessible';
                updateUI();
                return;
            }
            var entries = fs.readdirSync(rootDir, { withFileTypes: true });
            var paths = [];
            var foldersList = [];
            for (var i = 0; i < entries.length; i++) {
                var ent = entries[i];
                if ((ent.isDirectory() || (ent.isSymbolicLink && ent.isSymbolicLink())) && ent.name.toLowerCase().indexOf('camille') !== -1) {
                    var fPath = path.join(rootDir, ent.name).replace(/\\/g, '/');
                    paths.push(fPath);
                    var vCount = 0;
                    try {
                        var docsDir = path.join(rootDir, ent.name, 'docs');
                        if (fs.existsSync(docsDir)) {
                            var dFiles = fs.readdirSync(docsDir);
                            vCount = dFiles.filter(function(f) {
                                var ext = f.split('.').pop().toLowerCase();
                                return ['mp4', 'mov', 'avi', 'mxf', 'mpg', 'mpeg', 'wmv'].indexOf(ext) !== -1;
                            }).length;
                        }
                    } catch(eCnt) {}
                    foldersList.push({
                        path: fPath,
                        name: ent.name,
                        videoCount: vCount,
                        checked: true
                    });
                }
            }
            if (paths.length > 0) {
                var totalVideos = foldersList.reduce(function(acc, x){ return acc + (x.videoCount || 0); }, 0);
                var infoMsg = paths.length + " dossier(s) 'Camille' détecté(s) sur F:\\ (" + totalVideos + " vidéo(s) trouvée(s))";
                handleHostMessage({
                    type: 'foldersSelected',
                    success: true,
                    paths: paths,
                    folders: foldersList,
                    info: infoMsg
                });
            } else {
                addLog('Aucun dossier "Camille" trouvé sur F:\\ via Node.js', 'warning');
            }
        } catch (eNode) {
            console.error('Fallback Node.js autoDetectFolders:', eNode);
            state.hasError = true;
            state.errorMessage = 'Erreur fallback Node: ' + eNode.message;
            updateUI();
        }
    }

    function autoDetectFolders() {
        if (state.isBatchRunning) return;
        state.hasError = false;
        state.errorMessage = '';
        updateUI();
        addLog('Détection automatique des dossiers "Camille"...', 'info');
        csInterface.evalScript('autoDetectFolders()', function(result) {
            if (!result || result === 'undefined' || result === 'null' || (typeof result === 'string' && result.indexOf('EvalScript error') !== -1)) {
                runNodeAutoDetectFallback();
            } else {
                try {
                    var parsed = (typeof result === 'object') ? result : JSON.parse(result);
                    if (parsed && parsed.type === 'foldersSelected') {
                        handleHostMessage(parsed);
                    } else if (parsed && parsed.error) {
                        addLog('Erreur détection ExtendScript: ' + parsed.error, 'warning');
                        runNodeAutoDetectFallback();
                    }
                } catch (eParse) {
                    console.error('Erreur parsing autoDetectFolders result:', eParse, 'Raw:', result);
                    runNodeAutoDetectFallback();
                }
            }
        });
    }

    function selectCsv() {
        state.hasError = false;
        state.errorMessage = '';
        updateUI();
        csInterface.evalScript('selectCsv()');
    }

    function startBatch() {
        if (state.folderPaths.length === 0) return;
        state.hasError = false;
        state.errorMessage = '';
        state.isBatchRunning = true;
        updateUI();
        var config = JSON.stringify(getEffectiveConfigForHost());
        config = config.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
        var pathsJson = JSON.stringify(state.folderPaths);
        pathsJson = pathsJson.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
        var script = 'startBatchQueue("' + pathsJson + '", "' + config + '")';
        evalScriptWithTimeout(script, function (result) {
            // Réponse directe du host (le batch continue ensuite de façon asynchrone via processBatch)
            if (result && result !== 'null' && result !== 'undefined') {
                try {
                    var data = JSON.parse(result);
                    if (data && data.success === false) {
                        state.isBatchRunning = false;
                        addLog('Erreur démarrage batch: ' + (data.error || 'inconnue'), 'error');
                        updateUI();
                    }
                } catch (e) {}
            }
        }, 30000);
    }

    // ================= Orchestration du batch via pipe (mode optionnel) =================
    // Le client pilote la boucle étape par étape (evalScript séquentiels vers les
    // fonctions host batchPipe*), et route vers le pipe UNIQUEMENT les calculs purs :
    // mediasolution_apply_auto_recentering (coordonnées) et
    // mediasolution_apply_cuts_active_layer (segments). Import/prepare/open restent
    // côté host natif (le daemon retourne "fallback" pour ces entrypoints).
    // Si le pipe est indisponible au déclenchement, on bascule sur startBatchQueue
    // (batch host existant) : zéro régression.

    var pipeBatchState = {
        folders: [],
        folderIndex: 0,
        projects: [],
        projectIndex: 0,
        totalProjects: 0,
        processedCount: 0,
        cancelRequested: false
    };

    function isPipeAvailable() {
        return state.pythonTransport === 'pipe' && state.bridgeOk === true && supportsNodeRequire();
    }

    function startBatchViaPipe() {
        if (state.folderPaths.length === 0) return;
        state.hasError = false;
        state.errorMessage = '';
        state.isBatchRunning = true;
        updateUI();

        var config = JSON.stringify(getEffectiveConfigForHost());
        config = config.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
        var pathsJson = JSON.stringify(state.folderPaths);
        pathsJson = pathsJson.replace(/\\/g, "\\\\").replace(/"/g, '\\"');

        addLog('Démarrage batch via pipe...', 'info');
        evalScriptWithTimeout('prepareBatchPipe("' + pathsJson + '", "' + config + '")', function (result) {
            var data = null;
            try { data = result ? JSON.parse(result) : null; } catch (e) { data = null; }

            if (data && data.success === true && data.folders && data.folders.length > 0) {
                pipeBatchState.folders = data.folders.slice();
                pipeBatchState.folderIndex = 0;
                pipeBatchState.projects = [];
                pipeBatchState.projectIndex = 0;
                pipeBatchState.totalProjects = 0;
                pipeBatchState.processedCount = 0;
                pipeBatchState.cancelRequested = false;
                addLog('Batch via pipe prêt: ' + data.folders.length + ' dossier(s)', 'success');
                runBatchPipeFolder(0);
                return;
            }

            // Fallback complet : pipe indisponible ou échec de préparation → batch host
            addLog('Pipe indisponible pour le batch, bascule sur le batch host: ' + (data && data.error ? data.error : 'préparation échouée'), 'warning');
            state.isBatchRunning = false;
            updateUI();
            startBatch();
        }, 30000);
    }

    // Traite un dossier de la file : Step2 (créer AEPs), puis chaque projet.
    function runBatchPipeFolder(folderIndex) {
        if (pipeBatchState.cancelRequested) {
            finishBatchPipe(false);
            return;
        }
        if (folderIndex >= pipeBatchState.folders.length) {
            finishBatchPipe(true);
            return;
        }

        var folder = pipeBatchState.folders[folderIndex];
        var folderLabel = folder.replace(/\\/g, '/');
        folderLabel = folderLabel.substring(folderLabel.lastIndexOf('/') + 1) || folder;
        addLog('Traitement du dossier (pipe): ' + folder, 'info');

        evalScriptWithTimeout('batchPipeStep2("' + safeString(folder) + '")', function (result) {
            var data = null;
            try { data = result ? JSON.parse(result) : null; } catch (e) { data = null; }
            if (!data || data.success !== true || !data.projects) {
                addLog('Step2 (pipe) échec pour ' + folder + ': ' + (data && data.error ? data.error : 'réponse invalide'), 'error');
                runBatchPipeFolder(folderIndex + 1);
                return;
            }

            pipeBatchState.folderIndex = folderIndex;
            pipeBatchState.projects = data.projects.slice();
            pipeBatchState.projectIndex = 0;
            pipeBatchState.totalProjects = data.projects.length;
            addLog('Step2.2 (pipe): ' + data.projects.length + ' AEPs créés', 'info');
            runBatchPipeProject(folderIndex, folderLabel);
        }, 60000);
    }

    // Traite un projet : ouverture, import, préparation, auto-recentrage (pipe),
    // cuts (pipe), sauvegarde, fermeture. Enchaîne sur le projet/dossier suivant.
    function runBatchPipeProject(folderIndex, folderLabel) {
        if (pipeBatchState.cancelRequested) {
            finishBatchPipe(false);
            return;
        }
        if (pipeBatchState.projectIndex >= pipeBatchState.projects.length) {
            runBatchPipeFolder(folderIndex + 1);
            return;
        }

        var aepPath = pipeBatchState.projects[pipeBatchState.projectIndex];
        var current = pipeBatchState.projectIndex + 1;
        var total = pipeBatchState.totalProjects;
        updateProgress(current, total, 'Traitement de ' + aepPath, folderLabel);

        evalScriptWithTimeout('batchPipeOpenProject("' + safeString(aepPath) + '")', function (result) {
            var data = null;
            try { data = result ? JSON.parse(result) : null; } catch (e) { data = null; }
            if (!data || data.success !== true) {
                addLog('Step3.1 (pipe) échec pour ' + aepPath + ': ' + (data && data.error ? data.error : 'réponse invalide'), 'error');
                pipeBatchState.projectIndex++;
                runBatchPipeProject(folderIndex, folderLabel);
                return;
            }

            var compName = data.activeCompName;
            var layerIndex = data.videoLayerIndex;
            addLog('Projet ouvert (pipe): ' + compName + ' (calque ' + layerIndex + ')', 'info');

            runBatchPipeImport(folderIndex, folderLabel, aepPath, compName, layerIndex);
        }, 60000);
    }

    // Import des images : host natif (le daemon retourne fallback pour cet entrypoint).
    function runBatchPipeImport(folderIndex, folderLabel, aepPath, compName, layerIndex) {
        if (pipeBatchState.cancelRequested) {
            finishBatchPipe(false);
            return;
        }
        evalScriptWithTimeout('step3_2ImportImagesForFolder()', function (result) {
            var data = null;
            try { data = result ? JSON.parse(result) : null; } catch (e) { data = null; }
            if (!data || data.success !== true) {
                addLog('Import images (pipe): ' + (data && data.error ? data.error : 'échec'), 'warning');
            }
            runBatchPipePrepare(folderIndex, folderLabel, aepPath, compName, layerIndex);
        }, 30000);
    }

    // Préparation du calque : host natif via le wrapper exporté.
    function runBatchPipePrepare(folderIndex, folderLabel, aepPath, compName, layerIndex) {
        if (pipeBatchState.cancelRequested) {
            finishBatchPipe(false);
            return;
        }
        evalScriptWithTimeout('step3_2PrepareLayerByComp("' + safeString(compName) + '", ' + Number(layerIndex) + ')', function (result) {
            var data = null;
            try { data = result ? JSON.parse(result) : null; } catch (e) { data = null; }
            if (!data || data.success !== true) {
                addLog('Préparation calque (pipe): ' + (data && data.error ? data.error : 'échec'), 'warning');
            }
            runBatchPipeRecentering(folderIndex, folderLabel, aepPath, compName, layerIndex);
        }, 30000);
    }

    // Auto-recentrage : CALCUL via pipe (mediasolution_apply_auto_recentering),
    // application via host (applyAutoRecenteringCoords). Le contexte (tracking JSON,
    // inPoint, durée, frameRate, compWidth, config bridge) est résolu par le host
    // via batchPipeGetProjectContext (getActiveLayerInfo est inutilisable en batch :
    // app.project.activeItem est null sans viewer ouvert).
    function runBatchPipeRecentering(folderIndex, folderLabel, aepPath, compName, layerIndex) {
        if (pipeBatchState.cancelRequested) {
            finishBatchPipe(false);
            return;
        }
        if (!state.config.enableAutoRecentering) {
            runBatchPipeCuts(folderIndex, folderLabel, aepPath, compName, layerIndex);
            return;
        }
        if (!isPipeAvailable()) {
            addLog('Pipe perdu pendant le batch, recentrage natif par défaut', 'warning');
            runBatchPipeCuts(folderIndex, folderLabel, aepPath, compName, layerIndex);
            return;
        }

        evalScriptWithTimeout('batchPipeGetProjectContext("' + safeString(compName) + '", ' + Number(layerIndex) + ')', function (result) {
            var ctx = null;
            try { ctx = result ? JSON.parse(result) : null; } catch (e) { ctx = null; }
            if (!ctx || ctx.success !== true) {
                addLog('Auto-recentrage (pipe): contexte indisponible: ' + (ctx && ctx.error ? ctx.error : 'inconnue'), 'warning');
                runBatchPipeCuts(folderIndex, folderLabel, aepPath, compName, layerIndex);
                return;
            }

            var args = {
                tracking_json_path: ctx.trackingJsonPath,
                in_point: ctx.inPoint !== undefined && ctx.inPoint !== null ? ctx.inPoint : 0,
                duration: ctx.layerDuration || 0,
                frame_rate: ctx.frameRate || 25,
                comp_width: ctx.compWidth || 1920,
                config: {
                    SPREAD_THRESHOLD: (ctx.bridgeConfig && ctx.bridgeConfig.SPREAD_THRESHOLD !== undefined) ? ctx.bridgeConfig.SPREAD_THRESHOLD : 200,
                    ENABLE_CONFIDENCE_WEIGHTING: (ctx.bridgeConfig && ctx.bridgeConfig.ENABLE_CONFIDENCE_WEIGHTING !== undefined) ? ctx.bridgeConfig.ENABLE_CONFIDENCE_WEIGHTING : true,
                    CONFIDENCE_WEIGHT: (ctx.bridgeConfig && ctx.bridgeConfig.CONFIDENCE_WEIGHT !== undefined) ? ctx.bridgeConfig.CONFIDENCE_WEIGHT : 0,
                    LABEL_HIGH_SPREAD: (ctx.bridgeConfig && ctx.bridgeConfig.LABEL_HIGH_SPREAD !== undefined) ? ctx.bridgeConfig.LABEL_HIGH_SPREAD : 12,
                    LABEL_STABLE: (ctx.bridgeConfig && ctx.bridgeConfig.LABEL_STABLE !== undefined) ? ctx.bridgeConfig.LABEL_STABLE : 3,
                    apply_to_all_layers: false,
                    DISABLE_UNDO_GROUP: true
                }
            };

            sendCommandToPythonPipe('mediasolution_apply_auto_recentering', args, 15000, function (res) {
                if (res && res.ok && res.result && res.result.status === 'computed') {
                    var centerX = res.result.center_x !== undefined ? res.result.center_x : ctx.compWidth / 2;
                    var labelIndex = res.result.label_index !== undefined ? res.result.label_index : 3;
                    if (res.result.applied === true) {
                        evalScriptWithTimeout('applyAutoRecenteringCoords("' + safeString(compName) + '", ' + Number(layerIndex) + ', ' + Number(centerX) + ', ' + Number(labelIndex) + ')', function (applyRes) {
                            var applyData = null;
                            try { applyData = applyRes ? JSON.parse(applyRes) : null; } catch (e) { applyData = null; }
                            if (!applyData || applyData.success !== true) {
                                addLog('Auto-recentrage (pipe): application échouée: ' + (applyData && applyData.error ? applyData.error : 'inconnue'), 'warning');
                            } else {
                                addLog('Auto-recentrage (pipe): center_x=' + centerX + ' label=' + labelIndex, 'info');
                            }
                            runBatchPipeCuts(folderIndex, folderLabel, aepPath, compName, layerIndex);
                        }, 15000);
                        return;
                    }
                    addLog('Auto-recentrage (pipe): aucun objet détecté, centrage par défaut', 'info');
                    runBatchPipeCuts(folderIndex, folderLabel, aepPath, compName, layerIndex);
                    return;
                }
                addLog('Auto-recentrage (pipe) échec, centrage par défaut: ' + (res && res.error ? res.error : 'inconnue'), 'warning');
                runBatchPipeCuts(folderIndex, folderLabel, aepPath, compName, layerIndex);
            });
        }, 30000);
    }

    // Cuts : CALCUL via pipe (mediasolution_apply_cuts_active_layer) → segments,
    // application via host (applyComputedCutsToLayer, existant). Le CSV matchant
    // et le tracking JSON sont résolus par le host (batchPipeGetProjectContext).
    function runBatchPipeCuts(folderIndex, folderLabel, aepPath, compName, layerIndex) {
        if (pipeBatchState.cancelRequested) {
            finishBatchPipe(false);
            return;
        }
        if (!state.config.enablePythonCutsParser) {
            runBatchPipeSave(folderIndex, folderLabel, aepPath, compName, layerIndex);
            return;
        }
        if (!isPipeAvailable()) {
            addLog('Pipe perdu pendant le batch, cuts via fallback ExtendScript', 'warning');
            runBatchPipeCutsFallback(folderIndex, folderLabel, aepPath, compName, layerIndex);
            return;
        }

        evalScriptWithTimeout('batchPipeGetProjectContext("' + safeString(compName) + '", ' + Number(layerIndex) + ')', function (result) {
            var ctx = null;
            try { ctx = result ? JSON.parse(result) : null; } catch (e) { ctx = null; }
            if (!ctx || ctx.success !== true) {
                addLog('Cuts (pipe): contexte indisponible, fallback ExtendScript: ' + (ctx && ctx.error ? ctx.error : 'inconnue'), 'warning');
                runBatchPipeCutsFallback(folderIndex, folderLabel, aepPath, compName, layerIndex);
                return;
            }

            if (!ctx.csvPath) {
                addLog('WARN (pipe): aucun CSV matchant pour ' + (ctx.baseName || compName), 'warning');
                runBatchPipeSave(folderIndex, folderLabel, aepPath, compName, layerIndex);
                return;
            }

            var args = {
                csv_path: ctx.csvPath,
                frame_rate: ctx.frameRate || 25,
                comp_duration: ctx.compDuration,
                comp_width: ctx.compWidth || 1920,
                snap_factor: 1.5,
                tracking_json_path: ctx.trackingJsonPath,
                config: {
                    SPREAD_THRESHOLD: (ctx.bridgeConfig && ctx.bridgeConfig.SPREAD_THRESHOLD !== undefined) ? ctx.bridgeConfig.SPREAD_THRESHOLD : 200,
                    ENABLE_CONFIDENCE_WEIGHTING: (ctx.bridgeConfig && ctx.bridgeConfig.ENABLE_CONFIDENCE_WEIGHTING !== undefined) ? ctx.bridgeConfig.ENABLE_CONFIDENCE_WEIGHTING : true,
                    CONFIDENCE_WEIGHT: (ctx.bridgeConfig && ctx.bridgeConfig.CONFIDENCE_WEIGHT !== undefined) ? ctx.bridgeConfig.CONFIDENCE_WEIGHT : 0,
                    LABEL_HIGH_SPREAD: (ctx.bridgeConfig && ctx.bridgeConfig.LABEL_HIGH_SPREAD !== undefined) ? ctx.bridgeConfig.LABEL_HIGH_SPREAD : 12,
                    LABEL_STABLE: (ctx.bridgeConfig && ctx.bridgeConfig.LABEL_STABLE !== undefined) ? ctx.bridgeConfig.LABEL_STABLE : 3,
                    DISABLE_UNDO_GROUP: true
                }
            };

            sendCommandToPythonPipe('mediasolution_apply_cuts_active_layer', args, 20000, function (res) {
                if (res && res.ok && res.result && res.result.status === 'computed' && res.result.segments && res.result.segments.length > 0) {
                    addLog('Cuts (pipe): ' + res.result.segments.length + ' segments calculés, application AE...', 'info');
                    var segmentsJson = JSON.stringify(res.result.segments);
                    var escapedJson = segmentsJson.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
                    evalScriptWithTimeout('applyComputedCutsToLayerByComp("' + safeString(compName) + '", ' + Number(layerIndex) + ', "' + escapedJson + '")', function (jsxRes) {
                        var parsedJsx = null;
                        try { parsedJsx = jsxRes ? JSON.parse(jsxRes) : null; } catch (e) { parsedJsx = null; }
                        if (parsedJsx && parsedJsx.success) {
                            addLog('Cuts (pipe) appliqués: ' + parsedJsx.count, 'success');
                            runBatchPipeSave(folderIndex, folderLabel, aepPath, compName, layerIndex);
                            return;
                        }
                        addLog('Cuts (pipe): application AE échouée, fallback ExtendScript', 'warning');
                        runBatchPipeCutsFallback(folderIndex, folderLabel, aepPath, compName, layerIndex);
                    }, 30000);
                    return;
                }
                addLog('Cuts (pipe) échec, fallback ExtendScript: ' + (res && res.error ? res.error : 'inconnue'), 'warning');
                runBatchPipeCutsFallback(folderIndex, folderLabel, aepPath, compName, layerIndex);
            });
        }, 30000);
    }

    // Fallback cuts côté host (step3_2_applyCuts : même logique que le batch host).
    function runBatchPipeCutsFallback(folderIndex, folderLabel, aepPath, compName, layerIndex) {
        if (pipeBatchState.cancelRequested) {
            finishBatchPipe(false);
            return;
        }
        evalScriptWithTimeout('step3_2ApplyCutsByComp("' + safeString(compName) + '", ' + Number(layerIndex) + ')', function (result) {
            var data = null;
            try { data = result ? JSON.parse(result) : null; } catch (e) { data = null; }
            if (!data || data.success !== true) {
                addLog('Cuts fallback (host): ' + (data && data.error ? data.error : 'échec'), 'warning');
            } else {
                addLog('Cuts fallback (host): ' + (data.segmentsCreated || 0) + ' segments', 'info');
            }
            runBatchPipeSave(folderIndex, folderLabel, aepPath, compName, layerIndex);
        }, 60000);
    }

    // Sauvegarde + fermeture propre du projet (host).
    function runBatchPipeSave(folderIndex, folderLabel, aepPath, compName, layerIndex) {
        if (pipeBatchState.cancelRequested) {
            finishBatchPipe(false);
            return;
        }
        evalScriptWithTimeout('batchPipeSaveAndClose()', function (result) {
            var data = null;
            try { data = result ? JSON.parse(result) : null; } catch (e) { data = null; }
            if (!data || data.success !== true) {
                addLog('Sauvegarde/fermeture (pipe): ' + (data && data.error ? data.error : 'échec'), 'error');
            }
            pipeBatchState.processedCount++;
            pipeBatchState.projectIndex++;
            runBatchPipeProject(folderIndex, folderLabel);
        }, 60000);
    }

    // Finalise le batch pipe (purge + verrou host relâché) et affiche le bilan.
    function finishBatchPipe(completed) {
        evalScriptWithTimeout('batchPipeFinalize()', function (result) {
            state.isBatchRunning = false;
            updateUI();
            if (completed && !pipeBatchState.cancelRequested) {
                addLog('Batch via pipe terminé: ' + pipeBatchState.processedCount + ' projet(s) traité(s)', 'success');
            } else {
                addLog('Batch via pipe annulé (' + pipeBatchState.processedCount + ' projet(s) traité(s))', 'warning');
            }
        }, 30000);
    }

    function cancelBatchViaPipe() {
        pipeBatchState.cancelRequested = true;
        addLog('Annulation du batch via pipe demandée...', 'warning');
    }

    function cancelBatch() {
        // Si le batch pipe est en cours (pipeBatchState.folders rempli), on arrête
        // proprement la boucle client ; sinon, annulation du batch host existant.
        if (pipeBatchState.folders.length > 0 || pipeBatchState.cancelRequested) {
            cancelBatchViaPipe();
        } else {
            csInterface.evalScript('cancelBatch()');
        }
    }

    function runDiagnostics() {
        if (!state.folderPath) return;
        state.hasError = false;
        state.errorMessage = '';
        updateUI();
        csInterface.evalScript('runDiagnostics("' + safeString(state.folderPath) + '")', function(result) {
            if (result && result !== 'null') {
                var data = JSON.parse(result);
                if (data.ok) {
                    addLog('Diagnostics OK', 'success');
                    if (data.warnings) data.warnings.forEach(function(w) { addLog('WARN: ' + w, 'warning'); });
                } else {
                    addLog('Diagnostics KO', 'error');
                    if (data.errors) data.errors.forEach(function(e) { addLog('ERR: ' + e, 'error'); });
                }
            }
        });
    }

    function applyCuts() {
        if (!state.csvPath) return;

        state.hasError = false;
        state.errorMessage = '';
        updateUI();

        var cutsMode = getCutsMode();
        if (cutsMode === 'py_aep') {
            var confirmMsg = "ATTENTION : Le mode 'py_aep' va sauvegarder votre projet After Effects et modifier directement le fichier binaire AEP sur le disque.\n\n"
                + "Composition cible : " + (state.targetComp || "Active") + "\n"
                + "Calque cible : " + (state.targetLayer || "Sélectionné/Premier") + "\n\n"
                + "Voulez-vous continuer ?";
            if (!confirm(confirmMsg)) {
                addLog('Application des cuts annulée par l\'utilisateur', 'info');
                return;
            }
        }

        if (state.config.enablePythonCutsParser && state.bridgeOk === true && (state.pythonTransport === 'pipe')) {
            if (state.config.enablePyAepCuts) {
                applyCutsViaPyAepOffline();
                return;
            }

            csInterface.evalScript('getActiveLayerInfo()', function (result) {
                var info = null;
                try { info = JSON.parse(result); } catch (e) { info = null; }
                if (!info || info.ok !== true) {
                    addLog('Cuts Python: ' + (info && info.error ? info.error : 'Erreur info AE'), 'error');
                    applyCutsViaHostFallback();
                    return;
                }

                var trackingPath = null;
                if (supportsNodeRequire() && state.folderPath) {
                    try {
                        var fs = require('fs');
                        var path = require('path');
                        var docsFolder = path.join(state.folderPath, 'docs');
                        var baseName = String(info.videoName || '');
                        var dot = baseName.lastIndexOf('.');
                        if (dot !== -1) baseName = baseName.substring(0, dot);
                        var variants = [
                            baseName + '_ae.json',
                            baseName + '_tracking.json',
                            baseName + '.json'
                        ];
                        for (var i = 0; i < variants.length; i++) {
                            var p = path.join(docsFolder, variants[i]);
                            if (fs.existsSync(p)) {
                                trackingPath = p;
                                break;
                            }
                        }
                    } catch (e) {
                        trackingPath = null;
                    }
                }

                csInterface.evalScript('getPyShiftBridgeConfig()', function (cfgRaw) {
                    var bridgeCfg = {};
                    try {
                        bridgeCfg = JSON.parse(cfgRaw || '{}');
                    } catch (e) {
                        bridgeCfg = {};
                    }

                    sendCommandToPythonPipe(
                        'mediasolution_apply_cuts_active_layer',
                        {
                            csv_path: state.csvPath,
                            frame_rate: info.frameRate,
                            comp_duration: info.duration,
                            comp_width: info.compWidth,
                            snap_factor: 1.5,
                            tracking_json_path: trackingPath,
                            config: bridgeCfg
                        },
                        20000,
                        function (res) {
                            if (res && res.ok && res.result && res.result.status === "computed") {
                                var segmentsJson = JSON.stringify(res.result.segments);
                                var escapedJson = segmentsJson.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
                                csInterface.evalScript('applyComputedCutsToLayer(' + info.layerIndex + ', "' + escapedJson + '")', function(jsxRes) {
                                    if (jsxRes && jsxRes !== "null" && jsxRes !== "undefined") {
                                        try {
                                            var parsedJsx = JSON.parse(jsxRes);
                                            if (parsedJsx && parsedJsx.success) {
                                                addLog('Cuts (CEPy hybride): ' + parsedJsx.count + ' créés et recentrés', 'success');
                                                return;
                                            }
                                        } catch(e) {}
                                    }
                                    addLog('Cuts via ExtendScript failed, fallback', 'warning');
                                    applyCutsViaHostFallback();
                                });
                                return;
                            }

                            addLog('Cuts Python failed, fallback ExtendScript', 'warning');
                            applyCutsViaHostFallback();
                        }
                    );
                });
            });
            return;
        }

        applyCutsViaHostFallback();
    }

    function applyCutsViaHostFallback() {
        var config = JSON.stringify(getEffectiveConfigForHost());
        config = config.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
        csInterface.evalScript('applyCuts("' + safeString(state.csvPath) + '", "' + config + '")', function (result) {
            if (result) {
                var data = JSON.parse(result);
                if (data.success) addLog('Cuts: ' + data.count + ' créés', 'success');
                else addLog('Erreur Cuts: ' + data.error, 'error');
            }
        });
    }

    function applyCutsViaPyAepOffline() {
        addLog('Mode py_aep: Sauvegarde du projet AE...', 'info');
        csInterface.evalScript('saveAndGetProjectPath()', function(result) {
            var projInfo = null;
            try { projInfo = JSON.parse(result); } catch (e) { projInfo = null; }
            if (!projInfo || projInfo.success !== true) {
                addLog('Mode py_aep: Échec sauvegarde projet - ' + (projInfo && projInfo.error ? projInfo.error : 'erreur inconnue'), 'error');
                return;
            }

            var trackingPath = null;
            if (supportsNodeRequire() && state.folderPath) {
                try {
                    var fs = require('fs');
                    var path = require('path');
                    var docsFolder = path.join(state.folderPath, 'docs');
                    var baseName = String(projInfo.videoName || '');
                    var dot = baseName.lastIndexOf('.');
                    if (dot !== -1) baseName = baseName.substring(0, dot);
                    var variants = [
                        baseName + '_ae.json',
                        baseName + '_tracking.json',
                        baseName + '.json'
                    ];
                    for (var i = 0; i < variants.length; i++) {
                        var p = path.join(docsFolder, variants[i]);
                        if (fs.existsSync(p)) {
                            trackingPath = p;
                            break;
                        }
                    }
                } catch (e) {
                    trackingPath = null;
                }
            }

            csInterface.evalScript('getPyShiftBridgeConfig()', function (cfgRaw) {
                var bridgeCfg = {};
                try {
                    bridgeCfg = JSON.parse(cfgRaw || '{}');
                } catch (e) {
                    bridgeCfg = {};
                }

                addLog('Mode py_aep: Modification binaire en cours...', 'info');
                sendCommandToPythonPipe(
                    'mediasolution_apply_cuts_pyaep',
                    {
                        aep_path: projInfo.path,
                        csv_path: state.csvPath,
                        comp_name: projInfo.compName,
                        layer_index: projInfo.layerIndex,
                        frame_rate: projInfo.frameRate,
                        comp_duration: projInfo.duration,
                        comp_width: projInfo.compWidth,
                        snap_factor: 1.5,
                        tracking_json_path: trackingPath,
                        config: bridgeCfg
                    },
                    30000,
                    function (res) {
                        if (res && res.ok && res.result && res.result.status === "ok") {
                            addLog('Mode py_aep: Réouverture du projet...', 'info');
                            csInterface.evalScript('reopenProjectPath("' + safeString(projInfo.path) + '")', function(reopenRes) {
                                var reopenInfo = null;
                                try { reopenInfo = JSON.parse(reopenRes); } catch(e) { reopenInfo = null; }
                                if (reopenInfo && reopenInfo.success) {
                                    addLog('Cuts (py_aep Offline): ' + res.result.created + ' segments créés et recentrés en binaire !', 'success');
                                } else {
                                    addLog('Mode py_aep: Échec réouverture - ' + (reopenInfo && reopenInfo.error ? reopenInfo.error : 'erreur inconnue'), 'error');
                                }
                            });
                            return;
                        }

                        addLog('Mode py_aep: Échec modification binaire: ' + (res && res.error ? res.error : 'erreur bridge'), 'error');
                        addLog('Bascule vers le fallback ExtendScript...', 'warning');
                        applyCutsViaHostFallback();
                    }
                );
            });
        });
    }

    function getPersistentConfigFilePath() {
        if (!supportsNodeRequire()) return null;
        try {
            var path = require('path');
            var os = require('os');
            return path.join(os.homedir(), 'Documents', 'PyShiftAE_CEP_Bridge', 'mediasolution_config.json');
        } catch (e) {
            return null;
        }
    }

    function writeJsonAtomic(filePath, data) {
        if (!supportsNodeRequire()) return false;
        try {
            var fs = require('fs');
            var path = require('path');
            var dir = path.dirname(filePath);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
            var tmpPath = filePath + '.' + Date.now() + '.tmp';
            fs.writeFileSync(tmpPath, JSON.stringify(data, null, 2), 'utf8');
            try {
                if (fs.existsSync(filePath)) {
                    fs.unlinkSync(filePath);
                }
            } catch (eDel) {}
            fs.renameSync(tmpPath, filePath);
            return true;
        } catch (e) {
            console.error('Erreur ecriture atomique config:', e);
            return false;
        }
    }

    function applyConfigToUI() {
        if (elements.pythonCmd) elements.pythonCmd.value = state.config.pythonCmd || '';
        if (elements.enablePythonCutsParser) elements.enablePythonCutsParser.checked = state.config.enablePythonCutsParser !== false;
        if (elements.enableAutoRecentering) elements.enableAutoRecentering.checked = state.config.enableAutoRecentering !== false;
        if (elements.enablePythonAnalyzer) elements.enablePythonAnalyzer.checked = state.config.enablePythonAnalyzer !== false;
        if (elements.enablePythonRecentering) elements.enablePythonRecentering.checked = state.config.enablePythonRecentering !== false;
        if (elements.enablePythonProjectOpen) elements.enablePythonProjectOpen.checked = state.config.enablePythonProjectOpen !== false;
        if (elements.enablePythonBaseAepCreation) elements.enablePythonBaseAepCreation.checked = state.config.enablePythonBaseAepCreation !== false;
        if (elements.enablePyAepCuts) elements.enablePyAepCuts.checked = state.config.enablePyAepCuts !== false;
        if (elements.enableLogFile) elements.enableLogFile.checked = state.config.enableLogFile !== false;
    }

    function updateConfig() {
        state.config.pythonCmd = elements.pythonCmd ? elements.pythonCmd.value : state.config.pythonCmd;
        if (elements.enablePythonCutsParser) state.config.enablePythonCutsParser = elements.enablePythonCutsParser.checked;
        if (elements.enableAutoRecentering) state.config.enableAutoRecentering = elements.enableAutoRecentering.checked;
        if (elements.enablePythonAnalyzer) state.config.enablePythonAnalyzer = elements.enablePythonAnalyzer.checked;
        if (elements.enablePythonRecentering) state.config.enablePythonRecentering = elements.enablePythonRecentering.checked;
        if (elements.enablePythonProjectOpen) state.config.enablePythonProjectOpen = elements.enablePythonProjectOpen.checked;
        if (elements.enablePythonBaseAepCreation) state.config.enablePythonBaseAepCreation = elements.enablePythonBaseAepCreation.checked;
        if (elements.enablePyAepCuts) state.config.enablePyAepCuts = elements.enablePyAepCuts.checked;
        if (elements.enableLogFile) state.config.enableLogFile = elements.enableLogFile.checked;

        saveConfig();
    }

    function loadConfig(callback) {
        var loaded = false;
        var parsed = null;

        // 1. Tenter la lecture synchrone du fichier JSON sur disque
        var filePath = getPersistentConfigFilePath();
        if (filePath) {
            try {
                var fs = require('fs');
                if (fs.existsSync(filePath)) {
                    var fileContent = fs.readFileSync(filePath, 'utf8');
                    if (fileContent && fileContent.trim().length > 0) {
                        parsed = JSON.parse(fileContent);
                        loaded = true;
                    }
                }
            } catch (eFile) {
                console.warn('Erreur lecture config sur disque:', eFile);
            }
        }

        // 2. Repli sur localStorage si non trouve sur disque
        if (!loaded) {
            try {
                var saved = localStorage.getItem('mediasolution_config');
                if (saved) {
                    parsed = JSON.parse(saved);
                    loaded = true;
                }
            } catch (eLs) {}
        }

        // 3. Fusion avec DEFAULT_CONFIG pour toute cle manquante
        if (loaded && parsed) {
            for (var key in DEFAULT_CONFIG) {
                if (parsed[key] === undefined) parsed[key] = DEFAULT_CONFIG[key];
            }
            state.config = parsed;
        } else {
            state.config = {};
            for (var k in DEFAULT_CONFIG) {
                state.config[k] = DEFAULT_CONFIG[k];
            }
        }

        // Normalisation des booleens
        state.config.enablePythonCutsParser = state.config.enablePythonCutsParser !== false;
        state.config.enableAutoRecentering = state.config.enableAutoRecentering !== false;
        state.config.enablePythonAnalyzer = state.config.enablePythonAnalyzer !== false;
        state.config.enablePythonRecentering = state.config.enablePythonRecentering !== false;
        state.config.enablePythonProjectOpen = state.config.enablePythonProjectOpen !== false;
        state.config.enablePythonBaseAepCreation = state.config.enablePythonBaseAepCreation !== false;
        state.config.enablePyAepCuts = state.config.enablePyAepCuts !== false;
        state.config.enableLogFile = state.config.enableLogFile !== false;

        // Mettre a jour l'interface immediatement
        applyConfigToUI();

        // 4. Synchronisation avec le host ExtendScript (recuperation de app.settings si disponible)
        try {
            csInterface.evalScript('loadRuntimeConfig()', function(hostRes) {
                if (hostRes && hostRes !== 'null' && hostRes !== 'undefined') {
                    try {
                        var hostCfg = JSON.parse(hostRes);
                        if (hostCfg && typeof hostCfg === 'object') {
                            for (var hk in DEFAULT_CONFIG) {
                                if (hostCfg[hk] !== undefined) state.config[hk] = hostCfg[hk];
                            }
                            applyConfigToUI();
                            try { localStorage.setItem('mediasolution_config', JSON.stringify(state.config)); } catch(e) {}
                            if (filePath) writeJsonAtomic(filePath, state.config);
                        }
                    } catch (eHostParse) {}
                } else {
                    var escaped = JSON.stringify(state.config).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
                    csInterface.evalScript('saveRuntimeConfig("' + escaped + '")');
                }
                if (typeof callback === 'function') callback();
            });
        } catch (eHost) {
            if (typeof callback === 'function') callback();
        }
    }

    function saveConfig() {
        var jsonStr = JSON.stringify(state.config);

        // 1. LocalStorage
        try {
            localStorage.setItem('mediasolution_config', jsonStr);
        } catch (eLs) {}

        // 2. Fichier persistant disque (Documents/PyShiftAE_CEP_Bridge/mediasolution_config.json)
        var filePath = getPersistentConfigFilePath();
        if (filePath) {
            writeJsonAtomic(filePath, state.config);
        }

        // 3. ExtendScript host runtime + app.settings natif After Effects
        var escapedConfig = jsonStr.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
        csInterface.evalScript('saveRuntimeConfig("' + escapedConfig + '")');
    }

    function exportConfig() {
        var configJson = JSON.stringify(state.config, null, 2);
        configJson = configJson.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
        csInterface.evalScript('saveConfigFile("' + configJson + '")', function(res) {
            if (res && res !== 'null' && res !== 'undefined') {
                addLog('Configuration exportee avec succes vers : ' + res, 'success');
            } else {
                addLog('Export de la configuration annule ou echoue', 'warning');
            }
        });
    }

    function importConfig() {
        csInterface.evalScript('loadConfigFile()', function(res) {
            if (res && res !== 'null') {
                try {
                    var parsed = JSON.parse(res);
                    if (parsed && typeof parsed === 'object') {
                        for (var key in DEFAULT_CONFIG) {
                            if (parsed[key] === undefined) parsed[key] = DEFAULT_CONFIG[key];
                        }
                        state.config = parsed;
                        applyConfigToUI();
                        saveConfig();
                        addLog('Config importee avec succes', 'success');
                    }
                } catch(e) {
                    addLog('Erreur import config: ' + e.toString(), 'error');
                }
            }
        });
    }

    function clearLogs() {
        elements.logsContainer.innerHTML = '';
    }

    function exportLogs() {
        var logs = [];
        elements.logsContainer.querySelectorAll('.log-entry').forEach(function(e) { logs.push(e.textContent); });
        var logText = logs.join('\n').replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, '\\n');
        csInterface.evalScript('saveLogFile("' + logText + '")', function(res){
            if (res && res !== 'null' && res !== 'undefined') {
                addLog('Logs exportés avec succès vers : ' + res, 'success');
            } else {
                addLog('Export des logs annulé ou échoué', 'warning');
            }
        });
    }

    function getCutsMode() {
        if (state.config.enablePythonCutsParser && state.bridgeOk === true && (state.pythonTransport === 'pipe')) {
            if (state.config.enablePyAepCuts) {
                return 'py_aep';
            }
            return 'hybrid';
        }
        return 'fallback';
    }

    function restartBridge() {
        addLog('Relance manuelle du bridge Python...', 'info');
        state.bridgeOk = null;
        state.lastDaemonSpawnAt = null; // Relance manuelle : on force un nouveau spawn
        updateUI();
        startPythonDaemon();
    }

    function updateActiveTarget() {
        csInterface.evalScript('getActiveLayerInfo()', function(result) {
            var targetInfo = elements.cutsTargetInfo;
            if (!targetInfo) return;
            try {
                if (result && result !== 'undefined' && result !== 'null') {
                    var res = JSON.parse(result);
                    if (res.ok) {
                        targetInfo.textContent = 'Cible : ' + res.compName + ' > ' + res.layerName;
                        targetInfo.className = 'cuts-target-info success';
                        state.targetOk = true;
                        state.targetComp = res.compName;
                        state.targetLayer = res.layerName;
                    } else {
                        targetInfo.textContent = 'Cible : ' + res.error;
                        targetInfo.className = 'cuts-target-info warning';
                        state.targetOk = false;
                        state.targetComp = '';
                        state.targetLayer = '';
                    }
                } else {
                    targetInfo.textContent = 'Cible : Aucune composition détectée';
                    targetInfo.className = 'cuts-target-info warning';
                    state.targetOk = false;
                    state.targetComp = '';
                    state.targetLayer = '';
                }
            } catch(e) {
                targetInfo.textContent = 'Cible : Indisponible';
                targetInfo.className = 'cuts-target-info error';
                state.targetOk = false;
                state.targetComp = '';
                state.targetLayer = '';
            }
            updateUI();
        });
    }

    function filterLogs() {
        if (!elements.logFilter) return;
        var filterValue = elements.logFilter.value;
        var entries = elements.logsContainer.querySelectorAll('.log-entry');
        entries.forEach(function(entry) {
            if (filterValue === 'all') {
                entry.style.display = '';
            } else {
                if (entry.classList.contains(filterValue)) {
                    entry.style.display = '';
                } else {
                    entry.style.display = 'none';
                }
            }
        });
    }

    document.addEventListener('DOMContentLoaded', init);
})();