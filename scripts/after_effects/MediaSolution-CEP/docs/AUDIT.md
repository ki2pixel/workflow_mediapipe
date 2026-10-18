# Audit — Media Solution v12.0 CEP

**Audit statique du 31/07/2026**, revue ligne par ligne de l'ensemble des sources (manifestes, client, host, ponts Python, documentation). Aucun test dynamique (pas de suite de tests dans le repo).

**TL;DR** : l'architecture hybride est solide et la discipline ES3 exemplaire, mais le repo accumule des chemins de machine en dur, un `eval()` non validé sur des fichiers de tracking, deux manifestes divergents, et des docs qui contredisent la réalité du transport (client pipe, host mailbox).

> **Mise à jour (07/08/2026)** : PyShiftAE v1.0.1 installée (migration du 14/07/2026 via `PyShiftBridge/tools/migrate_to_1.0.1.py`), remplaçant la v0.1.1 instable. Les constats M5/M6 (pipe CEPy inopérant, version déclarée fausse) sont résolus de fait : `entry.py` déclare désormais la version réellement installée. Le transport nominal est désormais le **pipe maison** `\\.\pipe\mediasolution` pour le client (Node), avec bascule automatique sur la mailbox; le host ExtendScript continue de passer par la mailbox (batch). Le bug de flush qui rendait le pipe muet a été corrigé le 07/08/2026 (voir `DEBUG_CHECKLIST.md`). Les fichiers `tools/diagnose_pipes.*` et `tools/diagnostic.py` ont été supprimés (artefacts du pipe jamais actif).

## Vue d'ensemble

| Élément | Verdict |
|---|---|
| Architecture générale (hybride CEP / ExtendScript / Python) | Solide et documentée |
| Configuration CEP (manifest.xml) | Fonctionnelle, mais 2 manifestes divergents |
| Frontend (HTML/CSS/JS) | Fonctionnel, avec des chemins durs et du code mort |
| Backend ExtendScript | Correct en ES3, mais des bugs latents |
| Ponts Python (entry.py / manifest.py) | Non fonctionnels en pratique (v0.1.1) |
| Documentation | Incohérences (utilisateur `kidpixel`, versions) |
| Hygiène du repo | Fichiers `.bak` et fichiers fantômes versionnés, pas de `.gitignore` |

Architecture réelle constatée : CEP Panel → `evalScript()` → ExtendScript (moteur AE), retour via CSXSEvent `com.workflowmediapipe.mediasolution.hostMessage` (JSON). Deux transports tentés pour le pont Python — pipe (Node.js `net` vers `\\.\pipe\com.psc.MediaSolution-CEP` / fallback `mediasolution`) puis mailbox (`cep_to_py.json` / `py_to_cep.json` pollés avec `$.sleep`). En pratique, seul la mailbox est fiable : PyShiftAE v0.1.1 (rework déc. 2024) ne supporte plus les extensions CEPy. Le pipeline tourne donc effectivement en ExtendScript natif, les ponts Python servant au health-ping et aux calculs de cuts quand le démon répond.

## Backend — `host/MediaSolution.jsx` (~2290 lignes)

Points forts : conformité ES3 rigoureuse (IIFE, `"use strict"`, polyfills ciblés, `var` systématique); `myJSON` privé, protégé de la pollution du prototype global, utilisé partout; écriture atomique des JSON (tmp + rename) avec repli sur les verrous Windows; pipelines de fallback en cascade (chaque fonction bridge a un équivalent ExtendScript); engine de scan streaming des gros JSON de tracking (seuils `JSON_CHUNK_SIZE_CHARS` / `MAX_FULL_JSON_READ_BYTES`); export `$.global` complet et explicite (14 fonctions + `testConnection`).

Problèmes critiques :

| # | Fichier:Ligne | Problème | Impact |
|---|---|---|---|
| C1 | `MediaSolution.jsx:118` | `var JSON = myJSON;` tente de masquer le built-in global; le shadowing est silencieusement ignoré en ES3 | Ligne trompeuse; à supprimer |
| C2 | `MediaSolution.jsx:262` | `safeJsonParse` teste `JSON` mais appelle `myJSON` | Logique déroutante |
| C3 | `MediaSolution.jsx:113` | `myJSON.parse` utilise `eval('(' + j + ')')` | Risque d'injection si entrée non-JSON; atténué par le garde `rx_one` |
| C4 | `MediaSolution.jsx:1947` | `readAndParseJsonRoot` fait `eval` sans aucune validation | Un fichier tracking malveillant/corrompu exécuterait du code arbitraire |
| C5 | `MediaSolution.jsx:2119` | Le cas `_ae.json` parse via `readAndParseJsonRoot` sans vérifier `maxFrame`/min/max | Chargement entier possible d'un gros fichier (contourne le streaming) |
| C6 | `MediaSolution.jsx:1130-1140` | Boucle `for (var i...)` déclarée 2× dans la même fonction | Fragile; le second bloc reprend `i` à la valeur finale du premier |
| C7 | `processBatch` (654-738) | `app.scheduleTask` sur un alias global, sans garde de réentrance | OK mais fragile si le JSX est rechargé en cours de batch |
| C8 | `G.STATE.batchRunning` | Jamais remis à `false` si le host crashe en cours de batch | L'UI reste bloquée sur "Annuler" |

Problèmes fonctionnels (modérés) :

- **D9 — Logs fichiers morts** : `currentLogFile` / `logFileOpenedForSession` / `logFileNamePrefix` jamais initialisés; le log fichier n'écrit rien (le README prétend le contraire).
- **D10 — `escapeSystemArg` (ligne 273)** : inutilisée, vestige du script standalone.
- **D11 — CSV naïf** : `line.split(',')` sans gestion des guillemets ni des virgules dans les valeurs.
- **D12 — Matching CSV par `indexOf(baseName)`** : correspondances partielles (`movie_2` matche `movie_20`).
- **D13 — `secondsToTimecode`** : `seconds % 60` sur float peut dépasser 60 à l'arrondi; mineur.
- **D14 — `targetLayer.remove()` sans vérification** : si tous les `duplicate()` échouent, le calque source peut être supprimé quand même.
- **D15 — Blocage UI pendant mailbox** : `sendToPyShiftBridge` boucle `$.sleep(200)` jusqu'à 60 s; l'UI d'AE est gelée (choix assumé pour le batch, mais les cuts manuels bloquent le panel 20 s).
- **D16 — Timecode CSV** : `csvTimecodeToSeconds` suppose `HH:MM:SS.mmm` strictement; les formats `MM:SS` ou `HH:MM:SS,mmm` échouent → segment ignoré.

Robustesse : bonne discipline générale (chaque `catch` logge, fallbacks explicites, objets stringifiés via `myJSON`). Absence totale de tests; l'ES3 n'étant pas exécutable hors AE, un lint ou un parse syntaxique serait utile. Redondance : `G.CONFIG` contient les mêmes 7 flags que le client — deux points de vérité, risque de dérive (déjà constaté dans `startBatch`).

## Frontend — `client/` (index.html, style.css, main.js)

**HTML** (206 lignes) : langue `fr`, UTF-8, `role="status"`/`aria-live`, labels `sr-only`, `<details>` pour les options avancées; aucun script inline; chargement `CSInterface.js` (vendored, ne pas éditer) puis `main.js` dans le bon ordre. F1 : valeur par défaut `pythonCmd` codée en dur (`C:/Python313/python.exe`). F2 : styles inline à déplacer en CSS. F3 : emoji dans le HTML, rendu dépendant de la police CEF.

**CSS** (537 lignes) : thème sombre par défaut + variante claire, variables centralisées, états `.ready/.working/.error`, scrollbar customisée. F4 : `.theme-dark` référencé dans main.js mais jamais défini. F5 : couleurs d'état identiques dans les deux thèmes (acceptable). F6 : `Segoe UI` est Windows-only.

**JavaScript** (1152 lignes) : IIFE + `'use strict'`, état global unique `state`, cache DOM `elements`, init sur `DOMContentLoaded`, health-monitoring du bridge (ping 30 s), config en localStorage (`mediasolution_config`).

Points forts : détection de transport robuste (pipe → internal → mailbox, rétrogradation et respawn du démon via Node); écouteur host unique avec gestion des payloads malformés (`[object Object]`, `undefined`); thème dynamique depuis `getHostEnvironment()` + écoute `ThemeChanged`; échappement systématique des backslashes/guillemets avant `evalScript`; `getEffectiveConfigForHost()` neutralise les flags Python quand le bridge est hors-ligne.

Problèmes :

| # | Ligne | Problème | Impact |
|---|---|---|---|
| C9 | 42-45 | Chemin utilisateur en dur (`C:\Users\kidpixel\...\extendscript_json_debug.log`) écrit à chaque init | Échec silencieux, écriture fantôme, chemin privé committé |
| C10 | 133 | Fallback `F:\Adobe\Adobe After Effects 2024\...\bridge_daemon.py` en dur | Spawn du démon impossible sur toute autre machine |
| C11 | 141 | Default `C:\Users\kidpixel\...\Python311\python.exe` en dur | Idem |
| C12 | 71 | `localStorage.getItem('pyshift_pipe_name')` : clé jamais écrite | Clé morte, fallback `com.psc.MediaSolution-CEP` toujours utilisé |
| C13 | 75-88 | `getPipePath` gère macOS mais manifest + daemon sont Windows-only | macOS non supporté en pratique (la doc prétend le contraire) |
| C14 | 789-797, 1089-1096 | Code JSX injecté par concaténation dans `evalScript` (3 blocs), sans échappement des noms de calques | Risque de syntaxe invalide |
| C15/C16 | 753-757, 1059 | Arrow functions ES6 isolées dans un fichier ES5 | Incohérence de style; casserait CEP < 8 |
| C17 | 556-575 | `updateUI` lit des éléments DOM sans null-check partout | Crash JS potentiel |
| C18 | 1024-1026 | `saveConfig()` sans clé de version | Migrations futures impossibles |
| C19 | 56 | Polling `updateActiveTarget` toutes les 10 s, même panel invisible | Surcharge CEP inutile |
| C20 | 49-56 | `evalScript` simultanés à l'ouverture (30 s + 10 s + init) | Ordre non garanti; mineur |
| C21 | 727-737 | `startBatch` sans callback : erreur silencieuse si le host est hors-ligne | L'utilisateur ne voit rien |
| C22 | 1088-1132 | `updateActiveTarget` sans debounce sur `mouseenter`/`focusin` | Multiples evalScript à l'approche du curseur |

À conserver : le fallback en cascade cuts (pipe → host), la désactivation cohérente des boutons batch, le `cleanup()` du socket pipe.

## Configuration CEP — `CSXS/`

`manifest.xml` (actif) : bundle `com.workflowmediapipe.mediasolution` v12.0.0, host AEFT `[13.0,99.9]`, CSXS 5.0, `AutoVisible`, géométrie 600×800, `--enable-nodejs` + `--mixed-context` (requis pour le bridge Node). M1 : `<ScriptPath>` déprécié en CEP 5+ (fonctionne, à vérifier sur AE 2025/2026). M2 : le menu affiché est "Media Solution v12.0" (sans "CEP"), contrairement à README/INSTALL. M3 : indentation XML mixte.

`manifest_complex.xml` (inactif ?) : ExtensionBundleId identique mais Extension Id différent (`com.workflowmediapipe.mediasolution.panel`), CSXS 6.0, chemins `./../client/...`, menu "Media Solution v12.0 CEP", `<Icons/>` vide. **M4** : deux manifestes incompatibles → confusion au packaging; supprimer ou documenter.

Fichiers CEPy machine : `manifest.py` importe `PyShiftAE` (classe `Manifest` inexistante dans la v0.1.1 installée → import échoue, confirmé par `confirmation_diagnostic.md`); `entry.py` contient des chemins durs `C:\Users\kidpixel\Documents\Scripts` + `py_aep-0.13.0\src`. **M5** : non fonctionnel en l'état, "inoffensif mais inerte". **M6** : `entry.py` déclarait v1.0.1 alors que la v0.1.1 était installée (résolu depuis, cf. mise à jour en tête).

## Documentation — cohérence

| Fichier | Constat |
|---|---|
| `README.md` | Bonne vue d'ensemble. Faux : logs "sauvegardés dans le dossier projet" (D9), événement host `com.adobe.host.event.message` (c'est `com.workflowmediapipe.mediasolution.hostMessage`), "exporter les fonctions dans `this`" (c'est `$.global`) |
| `INSTALL.md` | Bon guide. Prétend macOS supporté (C13); chemins `kidpixel` partout; présente le mode pipe CEPy comme opérationnel |
| `DIRECTORY_LAYOUT.md` | Cartographie claire (mermaid), mais schéma basé sur des chemins machine |
| `DEBUG_CHECKLIST.md` | Très complet (racines du bug myJSON). Contient des chemins `file:///c:/Users/kidpixel/...`; recommandation "CEP 5.0 au lieu de 6.0/7.0" non sourcée |
| `PY_AEP_DEVELOPER_GUIDE.md` / `PYSHIFTAE_DEVELOPER_GUIDE.md` | Excellents guides. Exemples de code avec `JSON.parse`/`JSON.stringify` natifs dans un contexte ExtendScript où c'est précisément interdit; "Double transport transparent" contredit par `confirmation_diagnostic.md` |
| `confirmation_diagnostic.md` | Le plus honnête : état réel du transport. Non daté; devrait être promu dans README/INSTALL |

## Hygiène du repo & sécurité

- **H1** : 4 fichiers `.bak` commités (`client/*.bak`, `host/MediaSolution.jsx.bak`).
- **H2** : pas de `.gitignore`.
- **H3** : pas de test, lint ni build; un simple `node --check client/main.js` + un parse syntaxique du JSX attraperaient 90 % des erreurs.
- **H4** : chemins privés committés (`kidpixel`, `F:\Adobe\...`, `C:/Python313`) dans main.js, entry.py, index.html et les docs. Prévoir une configuration utilisateur (le champ `pythonCmd` existe déjà).
- **H5** : `eval()` sur contenu fichier (C4) — principal risque de sécurité.
- **H6** : `--enable-nodejs` + `--mixed-context` donnent au panel un accès Node complet (fs, net, child_process). Requis par l'architecture, mais c'est la surface d'attaque maximale d'une extension CEP.
- **H7** : pas de `Content-Security-Policy`; aucun script inline présent, mais à verrouiller.

## Synthèse des risques par priorité

**Critique** : C4 (`eval` non validé sur les JSON de tracking); C9-C11/H4 (chemins durs, extension non portable); M5 (la doc présente le pipe comme fonctionnel alors que la réalité est mailbox + fallback); C21 (`startBatch` sans callback, aucune erreur visible).

**Important** : C1/C2 (ligne `var JSON = myJSON` trompeuse + test incohérent); D9 (log fichier mort); C19/C22 (polling agressif sans debounce ni visibilité); M4 (double manifeste); D11/D12/D16 (parseur CSV naïf); C14 (JSX injecté par concaténation).

**Amélioration** : C15/C16 (arrow functions isolées); F4 (`.theme-dark` sans définition); H1-H3 (nettoyage `.bak`, `.gitignore`, validation minimale); C18 (versioning localStorage); D15 (gel UI 20-60 s pendant la mailbox, à documenter au moins).

## Points positifs à préserver

- L'architecture hybride (calculs Python / exécution ExtendScript) avec fallback systématique est le bon design.
- La discipline `myJSON` (pas de shadowing, `var` local en récursion) est exemplaire pour l'ES3.
- Écriture atomique + retries du daemon (file lock Windows).
- Le monitoring de santé du bridge (pipe → mailbox → respawn daemon) est robuste.
- L'accessibilité de base du panel (aria-live, labels sr-only) est au-dessus de la moyenne des extensions CEP.
- La documentation de debug (DEBUG_CHECKLIST, confirmation_diagnostic) est d'une qualité rare.

## Recommandations (ordre d'exécution)

1. Supprimer les 4 `.bak`, créer le `.gitignore`.
2. Remplacer l'`eval` de `readAndParseJsonRoot` par `myJSON.parse` (validé par `rx_one`).
3. Supprimer `var JSON = myJSON;`, corriger le test dans `safeJsonParse`.
4. Externaliser les chemins machine (daemon, python) dans la config du panel.
5. Ajouter un callback à `startBatch` et un wrapper `safeEvalScript`.
6. Debounce `updateActiveTarget` + couper le polling si `document.hidden`.
7. Activer ou supprimer le log fichier ExtendScript (D9).
8. Unifier les manifestes : supprimer `manifest_complex.xml` ou le documenter.
9. Mettre à jour README/INSTALL : transport réel, événement host correct, `$.global`, retirer les mentions macOS/pipe non supportés.
10. Ajouter `node --check client/main.js` + validation XML dans un script `check.ps1`.

*Les constats sur le comportement runtime de PyShiftAE s'appuient sur `confirmation_diagnostic.md` (document interne du repo).*
