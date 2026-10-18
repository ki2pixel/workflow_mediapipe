# Media Solution v12.0 CEP

Extension CEP pour Adobe After Effects qui transforme le script standalone `Media-Solution-v11.2-production.jsx` en panel moderne. Elle applique des cuts CSV et un auto-recentrage sur des séquences issues du pipeline Workflow MediaPipe v4.1.

**TL;DR** : le panel parle à ExtendScript pour tout ce qui touche au document After Effects, et à un démon Python pour les calculs lourds (cuts, recentrage). Le transport du client (Node) est le pipe nommé maison `\\.\pipe\mediasolution` (basse latence), avec repli automatique sur la mailbox de fichiers JSON; le host ExtendScript, lui, passe par la mailbox. Le pipe CEPy d'origine n'existe pas dans PyShiftAE.

## Le problème que ça résout

Le script v11.2 vivait dans des prompts et des alertes. Chaque batch demandait une validation manuelle, les erreurs passaient par des boîtes de dialogue, et les calculs de cuts s'exécutaient dans le thread d'AE, gelant l'interface pendant les gros traitements.

Le panel déplace l'interface dans le navigateur embarqué de CEP, et délègue les calculs coûteux à un démon Python séparé. After Effects ne fait plus que ce qu'il sait faire : modifier le document.

## Architecture

### Communication client ↔ host

Le panel et l'hôte échangent par deux canaux :

- **Client → Host** : `csInterface.evalScript("fonction(args)")`. Les fonctions sont exportées sur `$.global` à la fin de `host/MediaSolution.jsx`.
- **Host → Client** : événement CSXSEvent `com.workflowmediapipe.mediasolution.hostMessage`, payload JSON stringifié via le polyfill privé `myJSON` (jamais `JSON` natif, qui peut être pollué par des plugins tiers).

### Le pont Python et ses transports

Le pont `PyShiftBridge` a deux modes, et chacun des deux côtés (client, host) a son transport :

1. **Pipe** : pipe nommé maison `\\.\pipe\mediasolution`, serveur ctypes dans `bridge_daemon.py` (thread principal). C'est le transport du **client (Node)** : pings du health check, cuts parser, recentrage. Le client bascule automatiquement pipe ↔ mailbox selon le ping.
2. **Mailbox** : fichiers `cep_to_py.json` / `py_to_cep.json` échangés avec le démon `bridge_daemon.py`, pollés avec `$.sleep`. C'est le transport du **host ExtendScript** pour le batch (import, préparation de calques, application des cuts) : `sendToPyShiftBridge()` (JSX) écrit le fichier et boucle `$.sleep(200)` — un appel synchrone bloquant qui fige l'UI d'AE (assumé).

Le démon calcule les cuts et les recentrages; tout ce qui nécessite l'API After Effects (import, préparation de calques) renvoie `status: "fallback"` et ExtendScript prend le relais nativement. Ces messages de fallback dans les logs sont le fonctionnement normal, pas des erreurs.

> **Historique (07/08/2026)** : le pipe maison a été ajouté au daemon après que l'investigation de PyShiftAE v1.0.1 a établi que le plugin n'implémente aucun pipe CEPy. Un bug de flush (la réponse était coupée par `DisconnectNamedPipe` avant d'être vidée) a rendu le pipe muet pendant des semaines : le client restait en mailbox sans le savoir. Corrigé par un court délai après `WriteFile` dans `bridge_daemon.py` (voir `DEBUG_CHECKLIST.md`).
>
> **Historique (20/08/2026)** : fiabilisation du verrou single-instance du démon (`bridge_daemon.py`). L'ancien contrôle basé uniquement sur un PID écrit dans `bridge_daemon.lock` provoquait des blocages persistants (voyant rouge/indisponible) lorsque Windows réassignait ce même PID à un service tiers (ex: antivirus `bduserhost.exe`). Remplacé par un **Mutex Nommé Kernel Windows** (`Local\PyShiftBridge_Daemon_SingleInstance_Mutex`) doublé d'un verrou de fichier OS (`msvcrt.locking`) : libération instantanée et automatique par le noyau à l'arrêt du processus, sans verrou orphelin possible.

Le batch lui-même peut aussi être piloté par le client via le pipe, en mode optionnel (« Batch Pipe ») : l'orchestration route vers le pipe uniquement les calculs purs (cuts, auto-recentrage) et garde le host natif pour le reste. Le détail du flux, des fallbacks et des correctifs est dans [BATCH_PIPE_ORCHESTRATION.md](./BATCH_PIPE_ORCHESTRATION.md).

### Fichiers de tracking

Priorité de lecture : `*_ae.json`, puis `*_tracking.json`, puis `*.json` (format legacy).

### Exclusions batch

L'énumération des vidéos à traiter (Step2) écarte les fichiers listés dans `G.CONFIG.videoSkipNames` (noms exacts) et `G.CONFIG.videoSkipExtensions` (extensions), comparés sans tenir compte de la casse : actuellement `m6+.mp4` et tous les `.mov`. Ces vidéos ne génèrent ni AEP ni traitement Step3, et les compteurs affichés (sélection de dossier, diagnostics) les excluent aussi. `getProcessableVideoFiles()` trace chaque exclusion dans le log (« vidéo(s) ignorée(s) par exclusion batch »).

### Logs de session

`initLogFile()` ouvre, au démarrage du batch, un fichier `MediaSolutionLog_V12.0_CEP_<YYYYMMDD_HHMMSS>.log` (UTF-8) dans le dossier projet traité, avec repli sur `Documents/` si le dossier est introuvable. Un seul fichier par session AE : les batchs suivants l'utilisent en append. Les lignes sont au format `<timestamp> | <message>`, bufferisées par paquets de 5 avec flush immédiat sur les étapes critiques (`logStep`).

Cette écriture disque est pilotée par l'option **« Fichier de logs de session (.log) »** (options avancées du panel, activée par défaut, clé de config `enableLogFile`). Décochée, elle ne coupe que le fichier : les logs du panneau et la console ExtendScript (`$.writeln`) continuent. L'état est réévalué à chaque démarrage de batch, et recocher crée un nouveau fichier horodaté.

Le log du démon Python (`daemon_loop.log`, dossier mailbox) est indépendant de cette option.

## Installation

Copier le dossier dans le répertoire d'extensions CEP, activer le mode debug, redémarrer AE. Le détail complet est dans [INSTALL.md](./INSTALL.md).

## Structure du dépôt

```
MediaSolution-CEP/
├── CSXS/manifest.xml        # Déclaration CEP (AEFT [13.0,99.9], CSXS 5.0)
├── client/                  # Panel HTML/CSS/JS + CSInterface.js vendored
├── host/MediaSolution.jsx   # Logique ExtendScript (ES3, ~2290 lignes)
├── docs/                    # Toute la documentation
├── entry.py / manifest.py   # Fichiers CEPy machine (inoffensifs, inertes avec v1.0.1)
└── check.ps1                # Validation du dépôt (syntaxe, manifest, hygiène)
```

## Développement

### Modifier le client

Les fichiers vivent dans `client/`; après édition, recharger via `Window > Extensions > Reload Extensions` ou redémarrer AE. La console CEP s'ouvre avec F12 dans le panel.

### Modifier le host

`host/MediaSolution.jsx` est du ExtendScript ES3. Trois contraintes, non négociables :

- **Jamais de shadowing des built-ins** : `var JSON = myJSON` est silencieusement ignoré par le moteur ES3. Toujours nommer les polyfills autrement (`myJSON`).
- **Toujours `var`-déclarer les variables de boucle** dans les fonctions récursives (`i`, `k`, `v`, `partial`), sinon la récursion écrase la mémoire de la fonction parente.
- **Exporter sur `$.global`** toute fonction appelée par le panel.

### Les pièges connus

- Le `JSON` natif d'ExtendScript peut être pollué par des plugins tiers installés sur la machine. Le host n'utilise que `myJSON`, validé par regex avant tout `eval` (voir `DEBUG_CHECKLIST.md`).
- Les chemins transmis ExtendScript → JSON → Python peuvent corrompre les caractères non-ASCII (`é` → `Ǹ`). Côté Python, on résout les chemins par matching de nom, jamais par confiance dans le chemin brut.
- Ne jamais ré-ouvrir un projet en RAM après un échec du mode binaire py_aep : gel natif garanti.

## Compatibilité

| Élément | Portée |
|---|---|
| After Effects | 2020 (v17.0+) à 2026+; v13.0+ via fallback. La création binaire offline exige AE 2026+ |
| CEP Runtime | CSXS 5.0; `PlayerDebugMode=1` requis sur AE 2026 / CSXS.11+ |
| Python | 3.10+, interpréteur du démon |
| Systèmes | Windows 10+ (testé); macOS non testé, support non garanti |

## Dépannage rapide

1. **L'extension n'apparaît pas** : installation, mode debug, redémarrage.
2. **Erreur de communication** : redémarrer AE pour purger le cache CEP.
3. **Ponts Python introuvables** : vérifier le chemin de l'exécutable dans la config du panel.
4. **Dossier non reconnu** : il doit contenir un sous-dossier `docs/` avec les vidéos et fichiers de tracking.

La checklist complète est dans [DEBUG_CHECKLIST.md](./DEBUG_CHECKLIST.md).

L'audit de conformité à la documentation officielle CEP (manifest, IPC, ES3, structure) est dans [CEP_CONFORMITY_AUDIT.md](./CEP_CONFORMITY_AUDIT.md).

## Concepts en exploration

- [VISION_CAPTURE_CONCEPT.md](./VISION_CAPTURE_CONCEPT.md) : extension CEP de capture vision (webcam, face mesh, mains) avec réinjection des landmarks dans AE. La faisabilité est détaillée dans deux rapports de recherche complémentaires : [Architecture CEP Motion Capture AE](./recherches/Architecture_CEP_Motion_Capture%20AE.md) (briques techniques et patterns) et [Capture Webcam After Effects](./recherches/Capture_Webcam_After_Effects.md) (limites des flux temps réel dans AE).

## Historique

### v12.0 (CEP)
Adaptation complète du script v11.2 en extension CEP : interface HTML/CSS/JS, ponts Python (cuts parser, auto-recentrage), configuration exportable, logs temps réel, diagnostics intégrés.

### v11.2 (JSX)
Script standalone à prompts, ponts Python pour auto-recentrage et cuts CSV, optimisations batch.

## Licence

Ce projet fait partie du Workflow MediaPipe v4.1 et suit les mêmes termes de licence.
