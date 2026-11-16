---
trigger: model_decision
description: Workflow MediaPipe v4.x mandatory coding standards, architectural rules, and anti-patterns
---

# Workflow MediaPipe v4.x — Normes Architecturales & Standards de Code

> Référence normative transversale. Spécifications par étape déportées dans [pipeline-standards.md](file:///home/kidpixel/workflow_mediapipe/.agents/rules/pipeline-standards.md). Déviation → `decisionLog.md`.

## 1. Stack & Architecture Système
- **Backend** : Flask (Python 3.10). Blueprints minces dans `routes/` (uniquement validation I/O, décorateur `@measure_api`, appel service et retour JSON).
- **Logique Métier** : Fonctions pures et services isolés dans `services/`. Singletons accessibles via `get_workflow_state()`.
- **Thread-Safety** : État global géré exclusivement par `WorkflowState` sous verrou `RLock`. Interdiction formelle de dictionnaires globaux mutables type `PROCESS_INFO`.
- **Environnements & Dépendances** : Isolation stricte par virtualenv (`transnet_env/`, `audio_env/`, `tracking_env_slim/`, `insightface_env/`, `coral_env/`, `*_cv5_env/`).
- **Configuration** : `.env` $\rightarrow$ `config/settings.py` $\rightarrow$ `WorkflowCommandsConfig`. Zéro secret ou chemin absolu en dur.
- **Stockage Données** : SQLite via `CSVService` est l'unique base active. MySQL est obsolète (`USE_MYSQL=false`). Streaming JSON O(1) obligatoire via `ijson` et `StreamingJSONOutput`.

## 2. Règles Concurrence & Matériel
- **OpenCV 5.0 Multiprocessing** : Contexte `spawn` obligatoire (`multiprocessing.get_context("spawn")`, bannir `fork`). Limitation stricte à 1 thread par worker via `cv2.setNumThreads(1)` contre l'oversubscription CPU. Exception : STEP 2 séquentiel.
- **Google Coral Edge TPU** : Toute inférence sur TPU (`/dev/apex_0`) doit impérativement transiter par la file FIFO séquentielle de `services/coral_tpu_orchestrator.py` pour préserver les 8 Mo de SRAM contre l'éviction de cache.
- **I/O Système** : Fichiers et dossiers ouverts exclusivement via `FilesystemService.open_path_in_explorer()` avec verrous d'exclusion mutuelle.

## 3. Frontend Immuable & Cycle de Vie
- **État** : Immuabilité stricte via `AppState.setState()` avec diff superficiel.
- **DOM** : Rendu planifié uniquement par `DOMBatcher.scheduleUpdate()`. Échappement systématique des entrées dynamiques via `DOMUpdateUtils.escapeHtml()`.
- **DOMDiff** : Morphing des listes dynamiques (`<li>`) obligatoirement encapsulé dans des balises parentes stables (`<ul>`).
- **Polling & Synchronisation** : Orchestration exclusive par `PollingManager` (bannir tout `setInterval` orphelin).

## 4. ExtendScript ES3 (After Effects & CEP)
- **Moteur ES3 Pur** : `var` exclusif, boucles `for` classiques, encapsulation IIFE systématique, polyfill `JSON2`. Interdiction absolue de la syntaxe ES6 (`const`, `let`, `=>`, `map`, templates).
- **Passerelle & Sécurité** : `system.callSystem()` avec chemins nettoyés et arguments validés. Batching des opérations Timeline dans `app.beginUndoGroup()` / `endUndoGroup()`.

## 5. Pipeline par Étape
Pour les détails exhaustifs des étapes STEP1 à STEP8 (moteur ONNX GPU, YAMNet Split TPU, d-vectors ECAPA, cascade BlazeFace, hiérarchie 4 paliers, EffectCraft CLI), consulter :
👉 [pipeline-standards.md](file:///home/kidpixel/workflow_mediapipe/.agents/rules/pipeline-standards.md)

## 6. Anti-Patrons Formels
- Écrire de la logique métier ou des calculs lourds dans les routes Flask.
- Manipuler le DOM sans `DOMUpdateUtils.escapeHtml` ou interroger le DOM dès l'importation de modules JS.
- Utiliser des `setInterval` non déclarés dans `PollingManager`.
- Hardcoder des chemins locaux ou réseaux (utiliser `WorkflowCommandsConfig`).
- Charger un fichier JSON volumineux entièrement en mémoire avec `json.load()` (utiliser `ijson`).
- Exécuter des inférences TPU concurrentes hors de `coral_tpu_orchestrator.py`.
- Lancer des workers multiprocessing OpenCV 5.0 sans contexte `spawn` ou sans `cv2.setNumThreads(1)`.
- Utiliser du JavaScript moderne (ES6+) dans les fichiers ExtendScript `.jsx`.
