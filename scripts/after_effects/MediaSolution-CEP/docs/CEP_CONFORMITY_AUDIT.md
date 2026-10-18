# Audit de conformité CEP — Media Solution v12.0

**Date : 13/08/2026 — Revue statique contre le dataset officiel `C:\Users\cam-c\Documents\docs_extendscript\cep_dataset_2026\`** (cookbook CEP 9.0 et 11.1, XSD v7.0, CSInterface.d.ts, templates bolt-cep, SYSTEM_PROMPT_CEP).

**Verdict global : conforme à la documentation officielle CEP.** L'architecture, le manifest, le pont IPC et la discipline ES3 sont corrects. Quelques écarts mineurs de modernisation et d'hygiène sont listés en fin de document.

---

## 1. Manifest — `CSXS/manifest.xml`

| Point de contrôle | Attendu (doc officielle) | Constaté | Verdict |
|---|---|---|---|
| Version manifest | « All HTML extensions must use 5.0 or above » (cookbook CEP 11.1) | `Version="5.0"` | ✅ Conforme (le cookbook lui-même utilise 5.0 dans ses exemples) |
| ExtensionBundleId | reverse-DNS unique | `com.workflowmediapipe.mediasolution` | ✅ Conforme |
| Extension Id | unique, référence dans DispatchInfoList | identique au bundle | ✅ Conforme |
| ExtensionBundleVersion | `major.minor.micro` | `12.0.0` | ✅ Conforme |
| HostList | code SAP 4 lettres + plage | `AEFT [13.0,99.9]` | ✅ Conforme (AE 13 = CC 2014, couvre 24/26) |
| LocaleList | `xx_XX` ou `All` | `All` | ✅ Conforme |
| RequiredRuntime | CSXS ≥ 5.0 | `CSXS 5.0` | ✅ Conforme (min. requis) ; ⚠️ voir §7 |
| MainPath | relatif `./` + `/` | `./client/index.html` | ✅ Conforme |
| ScriptPath | relatif, exécuté dans le moteur ExtendScript | `./host/MediaSolution.jsx` | ✅ Conforme (toujours documenté dans le cookbook 11.1, pas déprécié) |
| CEFCommandLine | `--enable-nodejs` + `--mixed-context` pour Node | présents | ✅ Conforme (cookbook §Customize CEF) |
| Lifecycle AutoVisible | `true` pour un Panel | `true` | ✅ Conforme |
| UI Type | Panel | `Panel` | ✅ Conforme |
| Menu | nom affiché | `Media Solution v12.0` | ✅ Conforme |
| Geometry Size | **obligatoire** depuis CEP 9 | 600×800 | ✅ Conforme |
| Validation XSD v7.0 | schéma officiel | échoue sur `Version="5.0"` (le XSD n'accepte que `7.0`) | ⚠️ Écart formel, **non bloquant** : le cookbook autorise explicitement 5.0+ ; le manifest de référence du dataset échoue lui aussi (ordre Size) |

**Conclusion manifest : structure parfaitement conforme ; seule la validation stricte du XSD v7.0 échoue sur l'ancienneté de `Version`.**

---

## 2. Client — `client/` (CEF + Node.js, ES5/ES6)

| Point de contrôle | Attendu | Constaté | Verdict |
|---|---|---|---|
| CSInterface.js | vendored officiel Adobe, non modifié | v8.0.0, copyright Adobe 2013, APIs standard complètes | ✅ Conforme |
| Instanciation CSInterface | une seule fois | `var csInterface = new CSInterface()` au sommet de l'IIFE | ✅ Conforme |
| evalScript | asynchrone, callback, chaînes échappées | utilisé partout, avec `safeString()` et `evalScriptWithTimeout()` | ✅ Conforme (règle §4.1 SYSTEM_PROMPT) |
| addEventListener | types d'événements | `com.workflowmediapipe.mediasolution.hostMessage` + `com.adobe.csxs.events.ThemeChanged` (standard CEP) | ✅ Conforme |
| getHostEnvironment | via `window.__adobe_cep__` | utilisé dans `setupCSInterface()` + sur `ThemeChanged` | ✅ Conforme |
| Node.js | `require` disponible grâce à `--enable-nodejs` | `fs`, `path`, `os`, `child_process`, `net` | ✅ Conforme |
| Chemins Node | absolus (recommandation) | `path.join(os.homedir(), ...)`, `path.join(docDir, ...)` | ✅ Conforme (pas de require relatif) |
| localStorage | config perso | `mediasolution_config` | ✅ Conforme |
| Sérialisation | `JSON.stringify` + échappement avant evalScript | systématique (`config.replace(/\\/g,...)`) | ✅ Conforme |
| CSEvent (dispatch client→host) | via CSInterface | non utilisé (le client ne dispatche pas d'événements) | ✅ Non requis |
| Contexte | `--mixed-context` activé | accès direct à `require`/`process` | ✅ Conforme |

---

## 3. Host — `host/MediaSolution.jsx` (ExtendScript ES3)

| Point de contrôle | Attendu | Constaté | Verdict |
|---|---|---|---|
| Syntaxe ES3 | `var` uniquement, pas de `const/let/=>/forEach/map/filter/reduce/class/Promise/async` | scan regex : **0 occurrence** | ✅ Conforme (discipline exemplaire) |
| IIFE + `'use strict'` | isolation | présent | ✅ Conforme |
| `myJSON` privé | ne pas shadower `JSON` global (ES3 ignore le shadowing) | polyfill privé utilisé partout | ✅ Conforme (leçon DEBUG_CHECKLIST) |
| Retours sérialisés | `JSON.stringify` sur chaque fonction appelable | `myJSON.stringify(...)` systématique | ✅ Conforme |
| try/catch hôte | chaque fonction appelable enveloppée | systématique | ✅ Conforme |
| Export vers CEP | `$.global.<fn> = <fn>` au bas du fichier | ~35 exports, tous les `batchPipe*`, `step3_2*`, `applyComputedCutsToLayer`, etc. | ✅ Conforme |
| CSXSEvent (host→client) | `new ExternalObject("lib:\PlugPlugExternalObject")` puis `new CSXSEvent()`, `type`, `data`, `dispatch()` | exactement ce patron dans `sendToCEP()` | ✅ Conforme (cookbook §Access HTML DOM from extend script) |
| Événement type | doit correspondre au listener client | `com.workflowmediapipe.mediasolution.hostMessage` des deux côtés | ✅ Conforme |
| `app.scheduleTask` | utilisé pour batch asynchrone | présent (batch) | ✅ Conforme |

---

## 4. Structure de l'extension

| Élément | Attendu | Constaté | Verdict |
|---|---|---|---|
| Dossier d'installation | `%APPDATA%\Adobe\CEP\extensions\` (per-user) | installé à cet endroit | ✅ Conforme |
| Dossier racine | pas de `#` dans le chemin (CEF) | `MediaSolution-CEP` | ✅ Conforme |
| `.debug` | requis pour DevTools (dev uniquement) | présent à la racine (port 8088) | ✅ Conforme |
| PlayerDebugMode | `HKCU\Software\Adobe\CSXS.11 = 1` pour non signé | présent (CSXS.11, 9, 10) | ✅ Conforme |
| `.gitignore` | requis | présent | ✅ Conforme (AUDIT H2 résolu) |
| Fichiers `.bak` | interdits | aucun dans le repo | ✅ Conforme (AUDIT H1 résolu) |
| `node_modules` | aucun (pas de dépendances) | absent | ✅ Conforme |

---

## 5. Pont Python (spécifique au repo, hors doc officielle CEP)

Le cookbook ne couvre pas les ponts externes, mais la doc interne (`BATCH_PIPE_ORCHESTRATION.md`, `confirmation_diagnostic.md`) est alignée sur la réalité : pipe nommé maison `\\.\pipe\mediasolution` + mailbox en repli. Le client gère la détection, le respawn du démon et le fallback ExtendScript — ce sont des **extensions** au-dessus de la plateforme CEP, pas des violations. Les constats de l'AUDIT antérieur (chemins utilisateur et de machine en dur, `eval` non validé sur les JSON de tracking) sont **déjà résolus** dans l'état actuel du repo : `check.ps1` (scan dédié) et le scan manuel ne trouvent plus aucune de ces références, et `myJSON.parse` valide par regex (`rx_one`) avant tout `eval`.

---

## 6. Conformité runtime (AE 2026)

- AE installé : **26.2** (2026) et 24.x. Le cookbook CEP 11.1 cible AE 18.4+ ; AE 2026 intègre CEP 11 (CEF 88, Chromium 88, Node 15.9, NW.js 0.50.1).
- Le manifest `AEFT [13.0,99.9]` couvre AE 26.2 ✅.
- `--enable-nodejs` + `--mixed-context` : activés, requis pour le pont Node (fs/net/child_process) ✅.
- CSInterface.js v8.0.0 : rétrocompatible avec CEP 11 (les API utilisées existent toutes dans la v8) ✅.

---

## 7. Écarts mineurs et recommandations

| # | Constat | Recommandation |
|---|---|---|
| 1 | `Version="5.0"` et `RequiredRuntime CSXS 5.0` (minimum) | Moderniser vers `Version="7.0"` + `CSXS 11.0` pour coller au template bolt-cep et au SYSTEM_PROMPT_CEP, **si** le panel n'a pas besoin de tourner sous CSXS < 11 (AE < 2020). Sans cela, laisser 5.0 (conforme). |
| 2 | `.debug` absent | **Résolu (13/08/2026)** : fichier `.debug` créé à la racine de l'extension (port AEFT 8088), conforme au cookbook CEP 11.1 (« Create a .debug file to the extension root directory »). À retirer d'une distribution signée. |
| 3 | Pas de `Content-Security-Policy` | Le panel est 100 % local (aucun script inline, aucune ressource distante) : risque faible. Ajouter une CSP minimale `default-src 'self'` en durcissement. |
| 4 | `--mixed-context` + Node complet | Surface d'attaque maximale (fs/net/child_process) — assumé par l'architecture ; restreindre les droits si distribution. |
| 5 | Validation XSD v7.0 | Le manifest actuel échoue sur `Version="5.0"` (et le manifest de référence du dataset échoue aussi sur l'ordre Size). La validation XSD n'est donc pas un critère absolu ; documenter ce point si un outil de CI la réclame. |
| 6 | Menus : `Media Solution v12.0` vs docs | L'AUDIT notait M2 (menu sans « CEP ») — vérifier que README/INSTALL sont alignés (ils le sont dans l'état actuel). |

---

## 8. Sources de référence utilisées

- `C:\Users\cam-c\Documents\docs_extendscript\cep_dataset_2026\manifest\CEP_11.1_HTML_Extension_Cookbook.md`
- `C:\Users\cam-c\Documents\docs_extendscript\cep_dataset_2026\manifest\CEP_9.0_HTML_Extension_Cookbook.md`
- `C:\Users\cam-c\Documents\docs_extendscript\cep_dataset_2026\manifest\ExtensionManifest_v_7_0.xsd`
- `C:\Users\cam-c\Documents\docs_extendscript\cep_dataset_2026\manifest\manifest.xml` + `.debug`
- `C:\Users\cam-c\Documents\docs_extendscript\cep_dataset_2026\templates\cep.config.ts` + `README.md`
- `C:\Users\cam-c\Documents\docs_extendscript\SYSTEM_PROMPT_CEP.md`
- `C:\Users\cam-c\Documents\docs_extendscript\cep_dataset_2026\llms.txt`
- Sources du panel : `CSXS/manifest.xml`, `client/*`, `host/MediaSolution.jsx`, `check.ps1`, `docs/AUDIT.md`, `docs/DEBUG_CHECKLIST.md`
