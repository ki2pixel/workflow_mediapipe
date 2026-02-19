---
name: after-effects-cep-panel
description: after-effects-cep-panel skill migrated from Windsurf as contextual rules
globs: 
  - "**/*.{html,css,js}"
alwaysApply: false
---

# After Effects CEP Panel Expert (Media Solution v12.0)

Cette skill couvre le développement, le débogage et la maintenance des extensions CEP (Common Extensibility Platform) pour Adobe After Effects, avec un focus sur le panel Media Solution intégré.

## Architecture CEP & Positionnement

### Rôle dans l'Écosystème
Les extensions CEP remplacent les scripts ExtendScript traditionnels par des panels modernes HTML/CSS/JS intégrés à After Effects :

```
Pipeline MediaPipe → STEP7 (fichiers *_ae.json)
↓
Panel CEP (Media Solution v12.0) → Interface moderne dans AE
↓
Ponts Python (system.callSystem) → Traitement optimisé
```

### Structure Technique

| Composant | Technologie | Rôle |
|---|---|---|
| Panel HTML/CSS/JS | HTML5, CSS3, ES6+ | Interface utilisateur moderne |
| Pont ExtendScript | JavaScript | Communication AE ↔ Panel |
| Backend Python | Python 3.10+ | Traitement des données |

## Développement CEP

### Structure des Fichiers
```
Media-Solution-CEP/
├── manifest.xml              # Configuration CEP
├── index.html               # Interface du panel
├── css/
│   ├── panel.css        # Styles du panel
│   └── components.css   # Composants réutilisables
├── js/
│   ├── main.js           # Logique principale
│   ├── ae-bridge.js      # Pont ExtendScript
│   └── utils.js          # Utilitaires
└── icons/                  # Icônes du panel
```

### manifest.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExtensionManifest Version="7.0" xmlns="http://ns.adobe.com/ExtensionManifest/1.0">
  <Extension Id="com.mediasolution.ceppanel">
    <Extension Name="Media Solution Panel"/>
    <Extension Version="12.0"/>
    <Author>KidPixel Workflow</Author>
    <Host Name="AEFT">
      <Host Version="23.0"/>
    <Data Path="./"/>
    <CommandLineArguments/>
      <Argument>-arg1</Argument>
      <Argument>-arg2</Argument>
    </CommandLineArguments>
    <DispatchInfo>
      <Info>
        <Category>Media Solution</Category>
      <Entry Point>Main</Entry Point>
      <Event Name="com.mediasolution.event.update" />
      <Event Name="com.mediasolution.event.process" />
      <Event Name="com.mediasolution.export" />
      </Info>
    </DispatchInfo>
    <UI>
      <Type>Panel</Type>
      <Menu>Media Solution</Menu>
      <Geometry>
        <Size>
          <Height>600</Height>
          <Width>400</Width>
        </Size>
        <MinSize>
          <Height>400</Height>
          <Width>300</Width>
        </MinSize>
      </Geometry>
    </UI>
    <Runtime>
      <Host>AEFT</Host>
    </Runtime>
  </Host>
</ExtensionManifest>
```

## Pont ExtendScript

### ae-bridge.js
```javascript
// Communication avec After Effects via ExtendScript
class AEBridge {
  static csInterface = new CSInterface();
  
  static async call(functionName, ...args) {
    return new Promise((resolve, reject) => {
      this.csInterface.evalScript(
        `${functionName}(${args.map(arg => JSON.stringify(arg)).join(', ')})`,
        result => {
          if (result.status === 'ok') {
            resolve(JSON.parse(result.data));
          } else {
            reject(new Error(result.data));
          }
        }
      );
    });
  }
  
  static async getProjectInfo() {
    return this.call('getProjectInfo');
  }
  
  static async importTrackingData(filePath) {
    return this.call('importTrackingData', filePath);
  }
  
  static async exportComposition(format) {
    return this.call('exportComposition', format);
  }
}
```

### Script After Effects (ExtendScript)
```javascript
// Media-Solution-bridge.jsx
function getProjectInfo() {
  var project = app.project;
  return {
    name: project.name,
    items: project.numItems,
    duration: project.duration,
    frameRate: project.frameRate
  };
}

function importTrackingData(filePath) {
  var file = new File(filePath);
  if (file.exists) {
    var content = file.open();
    try {
      var data = JSON.parse(content);
      // Importer les données dans le projet
      importTrackingDataToAE(data);
      return { status: 'ok', data: 'Import successful' };
    } catch(e) {
      return { status: 'error', data: e.toString() };
    }
  } else {
    return { status: 'error', data: 'File not found' };
  }
}

function exportComposition(format) {
  var project = app.project;
  var comp = project.activeItem;
  
  if (comp && comp instanceof CompItem) {
    var outputPath = project.file.saveDialog({
      title: 'Export Composition',
      name: project.name + '_export.' + format
    });
    
    if (outputPath) {
      comp.renderUsingPreset(
        outputPath.fsName,
        format === 'mp4' ? 'H.264 Match Source - 23.976 fps' : 'Lossless with Alpha'
      );
      
      return { status: 'ok', data: outputPath.toString() };
    } else {
      return { status: 'error', data: 'Export cancelled' };
    }
  } else {
    return { status: 'error', data: 'No active composition' };
  }
}
```

## Interface Panel (index.html)

### Structure HTML
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Media Solution Panel</title>
  <link rel="stylesheet" href="css/panel.css">
</head>
<body>
  <div class="panel-container">
    <header class="panel-header">
      <h1>Media Solution v12.0</h1>
      <div class="status-indicator" id="ae-status"></div>
    </header>
    
    <main class="panel-content">
      <section class="import-section">
        <h2>Import Tracking Data</h2>
        <input type="file" id="tracking-file-input" accept=".json,.ae.json">
        <button id="import-btn" onclick="importTrackingData()">Import</button>
      </section>
      
      <section class="export-section">
        <h2>Export Composition</h2>
        <div class="export-controls">
          <select id="export-format">
            <option value="mp4">MP4 Video</option>
            <option value="mov">QuickTime MOV</option>
            <option value="aep">After Effects Project</option>
          </select>
          <button id="export-btn" onclick="exportComposition()">Export</button>
        </div>
      </section>
      
      <section class="project-info">
        <h2>Project Info</h2>
        <div id="project-details" class="loading">Loading...</div>
      </section>
    </main>
  </div>
  
  <script src="js/main.js"></script>
</body>
</html>
```

### Logique Principale (main.js)
```javascript
class MediaSolutionPanel {
  constructor() {
    this.aeBridge = new AEBridge();
    this.init();
  }
  
  async init() {
    try {
      // Charger les informations du projet AE
      const projectInfo = await this.aeBridge.getProjectInfo();
      this.updateProjectInfo(projectInfo);
      
      // Vérifier si After Effects est prêt
      this.updateStatus('connected');
      
    } catch (error) {
      console.error('Failed to initialize:', error);
      this.updateStatus('error');
    }
  }
  
  async importTrackingData() {
    const fileInput = document.getElementById('tracking-file-input');
    const file = fileInput.files[0];
    
    if (!file) {
      alert('Please select a tracking data file');
      return;
    }
    
    try {
      this.updateStatus('processing');
      const result = await this.aeBridge.importTrackingData(file.path);
      
      if (result.status === 'ok') {
        this.updateStatus('success');
        setTimeout(() => this.updateStatus('connected'), 2000);
      } else {
        this.updateStatus('error');
        alert('Import failed: ' + result.data);
      }
    } catch (error) {
      this.updateStatus('error');
      alert('Import error: ' + error.message);
    }
  }
  
  async exportComposition() {
    const format = document.getElementById('export-format').value;
    
    try {
      this.updateStatus('processing');
      const result = await this.aeBridge.exportComposition(format);
      
      if (result.status === 'ok') {
        this.updateStatus('success');
        alert('Export successful: ' + result.data);
      } else {
        this.updateStatus('error');
        alert('Export failed: ' + result.data);
      }
    } catch (error) {
      this.updateStatus('error');
      alert('Export error: ' + error.message);
    }
  }
  
  updateProjectInfo(info) {
    const details = document.getElementById('project-details');
    details.innerHTML = `
      <div><strong>Name:</strong> ${info.name}</div>
      <div><strong>Items:</strong> ${info.items}</div>
      <div><strong>Duration:</strong> ${info.duration}s</div>
      <div><strong>Frame Rate:</strong> ${info.frameRate}fps</div>
    `;
    details.classList.remove('loading');
  }
  
  updateStatus(status) {
    const indicator = document.getElementById('ae-status');
    indicator.className = `status-indicator status-${status}`;
    indicator.textContent = status.toUpperCase();
  }
}

// Initialiser le panel
document.addEventListener('DOMContentLoaded', () => {
  new MediaSolutionPanel();
});
```

## Débogage CEP

### Outils de Débogage
```bash
# Tester le panel CEP
AE_DEBUG=1 /Applications/Adobe\ After\ Effects/2024/After\ Effects.app

# Logs ExtendScript
# Les logs apparaissent dans Console ExtendScript d'AE
# Utiliser console.log() depuis le panel pour déboguer

# Recharger le panel
# F5 dans AE ou bouton de reload dans le panel

# Simulation sans AE
# Utiliser un navigateur pour tester l'interface HTML/CSS/JS
```

## Déploiement CEP

### Installation
```bash
# Copier le CEP dans le dossier Adobe
cp -r Media-Solution-CEP /Library/Application\ Support/Adobe/CEP/extensions/com.mediasolution.ceppanel

# Nettoyer le cache CEP
rm -rf ~/Library/Application\ Support/Adobe/CEP/extensions/com.mediasolution.ceppanel/CSXS

# Redémarrer After Effects
osascript -e 'tell application "Adobe After Effects 2024" to quit'
```

## Bonnes Pratiques

### 1. **Performance**
- Utiliser `requestAnimationFrame` pour les animations
- Limiter les appels `system.callSystem()`
- Cacher les éléments non visibles

### 2. **Sécurité**
- Valider tous les inputs JSON
- Échapper les chaînes de caractères
- Utiliser `CSInterface` pour la communication sécurisée

### 3. **Compatibilité**
- Tester sur différentes versions d'AE
- Gérer les erreurs de pont gracieusement
- Documenter les prérequis système

Utilisez ce prompt en tapant `/after-effects-cep-panel` dans Continue.
