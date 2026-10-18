# Orchestration du batch via pipe — mode optionnel

**TL;DR** : le batch multi-dossiers peut être piloté par le client CEP au lieu du host ExtendScript. Le client orchestre la boucle étape par étape et route vers le pipe nommé **uniquement les calculs purs** (cuts, auto-recentrage) ; l'import images, la préparation du calque et l'ouverture des projets restent côté host natif. Le batch host (`startBatchQueue`/`processBatch`) reste la référence et n'est pas modifié.

## Pourquoi ce mode existe

Le batch historique est piloté par le host ExtendScript (`processBatch`), qui bloque le thread AE et parle à Python via la mailbox. Le transport pipe (`\\.\pipe\mediasolution`) apporte un canal basse latence, mais le host ne peut pas ouvrir de pipe Windows : pas de `net` en ExtendScript. La solution est de faire piloter la boucle par le client (Node), qui, lui, sait parler au pipe.

## Architecture

```
Client (main.js)
  startBatchViaPipe()
    ├─ evalScript prepareBatchPipe()          -- init G.STATE sans lancer processBatch
    ├─ pour chaque dossier:
    │    ├─ evalScript batchPipeStep2()       -- performStep2_1+2_2 (créer les AEPs)
    │    └─ pour chaque AEP:
    │         ├─ evalScript batchPipeOpenProject()     -- Step3.1 (ouvrir, sélectionner comp/calque)
    │         ├─ evalScript batchPipeGetProjectContext() -- CSV matchant, tracking JSON, config bridge
    │         ├─ evalScript step3_2ImportImagesForFolder()  -- host natif
    │         ├─ evalScript step3_2PrepareLayerByComp()     -- host natif
    │         ├─ PIPE mediasolution_apply_auto_recentering  -- calcul pur
    │         │    └─ evalScript applyAutoRecenteringCoords() -- applique anchor/pos/label
    │         ├─ PIPE mediasolution_apply_cuts_active_layer  -- calcul pur
    │         │    └─ evalScript applyComputedCutsToLayerByComp() -- applique les segments
    │         ├─ evalScript batchPipeSaveAndClose()  -- save + fermeture propre
    │         └─ progress UI émis par le client
    └─ evalScript batchPipeFinalize()          -- purge mémoire, relâche le verrou
```

## Ce qui passe par le pipe (et pourquoi)

Le daemon `bridge_daemon.py` sert **tout** entrypoint enregistré dans `_HANDLERS` via `_handle_line` → `handle_entrypoint`. Mais plusieurs handlers retournent un fallback (ils délèguent à ExtendScript) :

| Entrypoint | Côté daemon | Utilisé par le mode pipe |
| --- | --- | --- |
| `mediasolution_apply_cuts_active_layer` | calcul pur (`status:"computed"`, segments) | ✅ pipe |
| `mediasolution_apply_auto_recentering` | calcul pur (`status:"computed"`, center_x/label) | ✅ pipe |
| `mediasolution_import_images_from_folder` | `fallback` (délégué à ExtendScript) | ❌ host natif |
| `mediasolution_batch_prepare_active_layer` | `fallback` | ❌ host natif |
| `mediasolution_open_project_and_select_comp` | `fallback` | ❌ host natif |
| `mediasolution_create_base_aep_for_video` | py_aep offline (AE 2026+) | ❌ host natif |
| `mediasolution_apply_cuts_pyaep` | py_aep offline (AE 2026+) | ❌ host natif (non branché dans ce mode) |

La règle : **le pipe ne transporte que les calculs purs** ; tout ce qui touche au DOM d'AE (importer, préparer, ouvrir) reste côté host via les primitives. C'est le pattern « Python calcule, ExtendScript exécute » déjà documenté dans [PYSHIFTAE_DEVELOPER_GUIDE.md](./PYSHIFTAE_DEVELOPER_GUIDE.md).

## Résolution du contexte (point critique)

En batch, aucun viewer n'est ouvert (délibérément, anti-gel), donc `app.project.activeItem` est null. Toute fonction host qui retombe sur `activeItem` échoue. Le mode pipe résout donc le contexte **par nom de comp + index de calque** :

- `batchPipeGetProjectContext(compName, layerIndex)` retourne au client le CSV matchant (comparaison `csvBase === baseName` après retrait du suffixe comp, ex. `_9x16`), le tracking JSON (`findTrackingJsonForVideo`), les infos comp/calque (frameRate, durée, width, inPoint, durée calque via `outPoint - inPoint`, plus fiable que `duration` en batch) et la config bridge (`G.CONFIG.SPREAD_THRESHOLD`, etc.).
- `applyAutoRecenteringCoords(compName, layerIndex, centerX, labelIndex)` et `applyComputedCutsToLayerByComp(compName, layerIndex, segmentsJson)` résolvent la comp par `findCompByName` avant d'appliquer.

Le client ne devine jamais le suffixe comp ni le chemin du tracking : tout vient du host.

## Fallbacks

- **Au déclenchement** : si le pipe est indisponible (`state.pythonTransport !== 'pipe'` ou `bridgeOk !== true`), le bouton « Batch Pipe » est désactivé et `startBatchViaPipe` bascule sur `startBatchQueue` (batch host). Zéro régression.
- **En cours de route** : si un appel pipe échoue (pipe perdu), l'étape concernée bascule sur le fallback host natif (`step3_2ApplyCutsByComp`, qui réutilise `step3_2_applyCuts`) ; le reste du batch continue.
- **Annulation** : `cancelBatchViaPipe` pose un flag ; chaque étape de la boucle le vérifie et appelle `batchPipeFinalize` (fermeture propre).

## Les trois bugs corrigés pendant le développement

1. **`info AE indisponible`** : le contexte était résolu via `getActiveLayerInfo()`, qui dépend de `app.project.activeItem` (null en batch). Corrigé par `batchPipeGetProjectContext`.
2. **`connect ENOENT` sur les cuts** : `_pipe_serve_one` ferme le handle du pipe après chaque connexion servie puis le recrée dans la boucle `main()`. Pendant cette fenêtre (quelques centaines de ms), un connect client échoue en ENOENT alors que le daemon est vivant (la mailbox continue de répondre). Corrigé par un **retry borné sur ENOENT** dans `sendCommandToPythonPipe` (3 tentatives, 250 ms d'espacement) ; les autres erreurs (timeout, EPIPE) restent des échecs immédiats.
3. **`application AE échouée`** : `applyComputedCutsToLayer` retombait sur `activeItem` quand la comp n'était pas passée. Corrigé par le wrapper `applyComputedCutsToLayerByComp` qui passe la comp explicitement.
4. **`%20` dans les logs py_aep** : `File.name` ExtendScript peut rapporter un nom encodé en URL (espaces en `%20`) alors que le fichier sur disque a un nom propre. Cosmétique uniquement (les AEPs sont bien créés au bon chemin avec les bons noms) ; l'affichage passe par `decodeNameForLog` (avec repli sur le nom brut si le nom contient un `%` littéral).

## Sérialisation des appels pipe

Le daemon sert une connexion pipe à la fois (`_pipe_serve_one` dans le thread principal). La boucle client est donc une **chaîne de callbacks séquentielle** (pas de `for` synchrone) : chaque étape attend la fin de la précédente avant d'appeler la suivante. C'est aussi ce qui permet au retry ENOENT de retomber sur un pipe fraîchement recréé.

## Limites connues

- Le mode pipe ne change pas la nature des étapes host : import images, préparation du calque et ouverture de projet restent natives (le daemon retourne `fallback` pour ces entrypoints). Les avertissements `Images import via PyShiftAE failed` et `Préparation calque via Python indisponible` dans les logs sont attendus et sans impact.
- Avec l'option avancée `enablePythonProjectOpen`, le log peut afficher `Open project via PyShiftAE failed, fallback ExtendScript: PyShiftBridge is running in Standalone mode...`. C'est le garde `IS_STANDALONE` du daemon (`bridge_daemon.py`) qui refuse `open_project_and_select_comp` en mode standalone ; ExtendScript ouvre ensuite le projet nativement. Attendu, sans impact.
- Le throttling des logs (`sendToCEP` limite à 1 log / 500 ms pendant le batch) peut avaler certains logs `Base AEP (py_aep Offline)` quand plusieurs projets sont créés dans la même seconde. Les AEPs, eux, sont bien créés sur disque (vérifiable par timestamp). Ce n'est pas une perte de traitement.
- Le mode `py_aep` (modification binaire offline, AE 2026+) n'est pas branché dans l'orchestration pipe : le calcul des cuts passe par `apply_cuts_active_layer` (segments) puis application AE. Le mode py_aep reste disponible via le batch host.
- La durée du calque en batch peut être `undefined` : `batchPipeGetProjectContext` applique le correctif `outPoint - inPoint` puis repli sur la durée de la comp, comme le fait déjà `applyAutoRecentering` côté host.

## Fichiers et fonctions

- `host/MediaSolution.jsx` : `prepareBatchPipe`, `batchPipeStep2`, `batchPipeOpenProject`, `batchPipeGetProjectContext`, `applyAutoRecenteringCoords`, `applyComputedCutsToLayerByComp`, `batchPipeSaveAndClose`, `batchPipeFinalize`, `step3_2ImportImagesForFolder`, `step3_2PrepareLayerByComp`, `step3_2ApplyCutsByComp` (toutes exportées sur `$.global`).
- `client/main.js` : `startBatchViaPipe`, `runBatchPipeFolder`, `runBatchPipeProject`, `runBatchPipeRecentering`, `runBatchPipeCuts`, `runBatchPipeCutsFallback`, `runBatchPipeSave`, `finishBatchPipe`, `cancelBatchViaPipe` ; retry ENOENT dans `sendCommandToPythonPipe`.
- `client/index.html` : bouton « Batch Pipe » à côté de « Démarrer Batch » (désactivé si le pipe est indisponible).
