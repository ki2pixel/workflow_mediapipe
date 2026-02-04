/* Media Solution v12.0 CEP - Main JavaScript */
(function() {
    'use strict';

    // Global state
    var csInterface = new CSInterface();
    var state = {
        folderPath: '',
        csvPath: '',
        isBatchRunning: false,
        config: {
            pythonCmd: 'C:/Python313/python.exe',
            enablePythonCutsParser: true,
            enableAutoRecentering: true,
            enablePythonAnalyzer: true
        }
    };

    // DOM Elements
    var elements = {};

    // Initialize
    function init() {
        cacheElements();
        loadConfig();
        bindEvents();
        setupCSInterface();
        addLog('Media Solution v12.0 CEP - Initialisé', 'info');
    }

    // Cache DOM elements
    function cacheElements() {
        elements = {
            statusIndicator: document.getElementById('statusIndicator'),
            statusDot: document.querySelector('.status-dot'),
            statusText: document.querySelector('.status-text'),
            folderPath: document.getElementById('folderPath'),
            browseFolder: document.getElementById('browseFolder'),
            folderInfo: document.getElementById('folderInfo'),
            pythonCmd: document.getElementById('pythonCmd'),
            enablePythonCutsParser: document.getElementById('enablePythonCutsParser'),
            enableAutoRecentering: document.getElementById('enableAutoRecentering'),
            enablePythonAnalyzer: document.getElementById('enablePythonAnalyzer'),
            exportConfig: document.getElementById('exportConfig'),
            importConfig: document.getElementById('importConfig'),
            startBatch: document.getElementById('startBatch'),
            cancelBatch: document.getElementById('cancelBatch'),
            runDiagnostics: document.getElementById('runDiagnostics'),
            batchProgress: document.getElementById('batchProgress'),
            progressFill: document.getElementById('progressFill'),
            progressText: document.getElementById('progressText'),
            csvPath: document.getElementById('csvPath'),
            browseCsv: document.getElementById('browseCsv'),
            applyCuts: document.getElementById('applyCuts'),
            logsContainer: document.getElementById('logsContainer'),
            clearLogs: document.getElementById('clearLogs'),
            exportLogs: document.getElementById('exportLogs')
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
        var skinInfo = JSON.parse(window.__adobe_cep__.getHostEnvironment()).appSkinInfo;
        updateTheme(skinInfo);
        csInterface.addEventListener('com.adobe.csxs.events.ThemeChanged', function(event) {
            var skinInfo = JSON.parse(window.__adobe_cep__.getHostEnvironment()).appSkinInfo;
            updateTheme(skinInfo);
        });
    }

    // Update theme based on AE theme
    function updateTheme(skinInfo) {
        var basePanelColor = skinInfo.panelBackgroundColor.color;
        var baseTextColor = skinInfo.panelTextColor.color;
        var bgColor = 'rgb(' + basePanelColor.red + ',' + basePanelColor.green + ',' + basePanelColor.blue + ')';
        var textColor = 'rgb(' + baseTextColor.red + ',' + baseTextColor.green + ',' + baseTextColor.blue + ')';
        document.body.style.backgroundColor = bgColor;
        document.body.style.color = textColor;
    }

    // Bind events
    function bindEvents() {
        elements.browseFolder.addEventListener('click', selectFolder);
        elements.exportConfig.addEventListener('click', exportConfig);
        elements.importConfig.addEventListener('click', importConfig);
        elements.startBatch.addEventListener('click', startBatch);
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
        logEntry.textContent = new Date().toLocaleTimeString() + ' - ' + message;
        elements.logsContainer.appendChild(logEntry);
        elements.logsContainer.scrollTop = elements.logsContainer.scrollHeight;
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
                updateProgress(data.current, data.total, data.message);
                break;
            case 'folderSelected':
                if (data.success === false) {
                    addLog('Erreur dossier: ' + (data.error || 'Annulé'), 'warning');
                } else if (data.path) {
                    state.folderPath = data.path;
                    elements.folderPath.value = data.path;
                    elements.folderInfo.textContent = data.info || '';
                    updateUI();
                    addLog('Dossier OK: ' + data.path, 'success');
                }
                break;
            case 'csvSelected':
                if (data.path) {
                    state.csvPath = data.path;
                    elements.csvPath.value = data.path;
                    updateUI();
                    addLog('CSV OK: ' + data.path, 'success');
                }
                break;
            case 'batchCompleted':
                state.isBatchRunning = false;
                updateStatus('ready', 'Prêt');
                updateUI();
                addLog('Batch terminé: ' + data.results, 'success');
                break;
            case 'error':
                addLog(data.message, 'error');
                state.isBatchRunning = false;
                updateStatus('error', 'Erreur');
                updateUI();
                break;
        }
    }

    function updateProgress(current, total, message) {
        var percentage = total > 0 ? (current / total) * 100 : 0;
        elements.progressFill.style.width = percentage + '%';
        elements.progressText.textContent = message || (current + ' / ' + total);
    }

    function updateUI() {
        var hasFolder = state.folderPath.length > 0;
        var hasCsv = state.csvPath.length > 0;
        elements.startBatch.disabled = !hasFolder || state.isBatchRunning;
        elements.cancelBatch.disabled = !state.isBatchRunning;
        elements.runDiagnostics.disabled = !hasFolder || state.isBatchRunning;
        elements.applyCuts.disabled = !hasCsv || state.isBatchRunning;
        elements.batchProgress.style.display = state.isBatchRunning ? 'block' : 'none';
        
        if (state.isBatchRunning) updateStatus('working', 'Traitement...');
        else updateStatus('ready', 'Prêt');
    }

    // Calls to ExtendScript
    function selectFolder() {
        addLog('Sélection dossier...', 'info');
        csInterface.evalScript('selectFolder()', function(result) {
            // Le résultat est traité via l'event folderSelected, 
            // mais on check aussi le retour direct au cas où
            if(result && result !== 'undefined' && result !== 'null') {
                try {
                    var data = JSON.parse(result);
                    // Si le message n'a pas été envoyé via event, on le traite ici
                    // (Evite doublon si sendToCEP a marché)
                } catch(e) {}
            }
        });
    }

    function selectCsv() {
        csInterface.evalScript('selectCsv()');
    }

    function startBatch() {
        if (!state.folderPath) return;
        state.isBatchRunning = true;
        updateUI();
        var config = JSON.stringify(state.config);
        // Échappement des backslashes pour la string ExtendScript
        config = config.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
        csInterface.evalScript('startBatch("' + state.folderPath.replace(/\\/g, "\\\\") + '", "' + config + '")');
    }

    function cancelBatch() {
        csInterface.evalScript('cancelBatch()');
    }

    function runDiagnostics() {
        if (!state.folderPath) return;
        csInterface.evalScript('runDiagnostics("' + state.folderPath.replace(/\\/g, "\\\\") + '")', function(result) {
            if (result && result !== 'null') {
                var data = JSON.parse(result);
                if (data.ok) {
                    addLog('Diagnostics OK', 'success');
                    if (data.warnings) data.warnings.forEach(w => addLog('WARN: ' + w, 'warning'));
                } else {
                    addLog('Diagnostics KO', 'error');
                    if (data.errors) data.errors.forEach(e => addLog('ERR: ' + e, 'error'));
                }
            }
        });
    }

    function applyCuts() {
        if (!state.csvPath) return;
        csInterface.evalScript('applyCuts("' + state.csvPath.replace(/\\/g, "\\\\") + '")', function(result) {
            if(result) {
                var data = JSON.parse(result);
                if(data.success) addLog('Cuts: ' + data.count + ' créés', 'success');
                else addLog('Erreur Cuts: ' + data.error, 'error');
            }
        });
    }

    function updateConfig() {
        state.config.pythonCmd = elements.pythonCmd.value;
        state.config.enablePythonCutsParser = elements.enablePythonCutsParser.checked;
        state.config.enableAutoRecentering = elements.enableAutoRecentering.checked;
        state.config.enablePythonAnalyzer = elements.enablePythonAnalyzer.checked;
        saveConfig();
    }

    function loadConfig() {
        var saved = localStorage.getItem('mediasolution_config');
        if (saved) {
            try {
                state.config = JSON.parse(saved);
                if(elements.pythonCmd) elements.pythonCmd.value = state.config.pythonCmd;
                if(elements.enablePythonCutsParser) elements.enablePythonCutsParser.checked = state.config.enablePythonCutsParser;
                if(elements.enableAutoRecentering) elements.enableAutoRecentering.checked = state.config.enableAutoRecentering;
                if(elements.enablePythonAnalyzer) elements.enablePythonAnalyzer.checked = state.config.enablePythonAnalyzer;
            } catch (e) {}
        }
    }

    function saveConfig() {
        localStorage.setItem('mediasolution_config', JSON.stringify(state.config));
    }

    function exportConfig() {
        var configJson = JSON.stringify(state.config, null, 2);
        configJson = configJson.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
        csInterface.evalScript('saveConfigFile("' + configJson + '")', function(res) {
            if(res && res != 'null') addLog('Config exportée', 'success');
        });
    }

    function importConfig() {
        csInterface.evalScript('loadConfigFile()', function(res) {
            if (res && res !== 'null') {
                try {
                    state.config = JSON.parse(res);
                    loadConfig();
                    saveConfig();
                    addLog('Config importée', 'success');
                } catch(e) { addLog('Erreur import config', 'error'); }
            }
        });
    }

    function clearLogs() {
        elements.logsContainer.innerHTML = '';
    }

    function exportLogs() {
        var logs = [];
        elements.logsContainer.querySelectorAll('.log-entry').forEach(e => logs.push(e.textContent));
        var logText = logs.join('\n').replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, '\\n');
        csInterface.evalScript('saveLogFile("' + logText + '")', function(res){
            if(res && res != 'null') addLog('Logs exportés', 'success');
        });
    }

    document.addEventListener('DOMContentLoaded', init);
})();