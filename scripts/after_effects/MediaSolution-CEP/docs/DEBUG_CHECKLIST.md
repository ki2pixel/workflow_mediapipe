# Checklist de Debug — Media Solution v12.0 CEP

**TL;DR** : si l'extension ne marche pas, dans l'ordre : structure du dossier, manifest, installation, mode debug, puis les tests de diagnostic. Les trois dernières sections documentent les grandes chasses aux bugs de 2026 (pollution du `JSON` global, gels en batch, serveur pipe muet) et ce qu'elles ont appris.

## Diagnostic de base

### 1. Structure

```
MediaSolution-CEP/
├── CSXS/
│   └── manifest.xml          # Doit exister
├── client/
│   ├── index.html            # Doit exister
│   ├── style.css             # Doit exister
│   ├── main.js               # Doit exister
│   └── CSInterface.js        # Doit exister (vendored Adobe, ne pas éditer)
├── host/
│   └── MediaSolution.jsx     # Doit exister
└── .debug                    # Debug DevTools (port 8088, dev uniquement)
```

### 2. Manifest

- Bundle ID unique : `com.workflowmediapipe.mediasolution`
- Version CSXS : 5.0
- Host AEFT : `[13.0,99.9]`
- Chemins relatifs : `./client/index.html` et `./host/MediaSolution.jsx`

### 3. Installation et mode debug

1. Copier vers `%APPDATA%\Adobe\CEP\extensions\MediaSolution-CEP\` (Windows) ou `~/Library/Application Support/Adobe/CEP/extensions/` (macOS).
2. `Help > Enable Debugging`, redémarrer AE.
3. `Help > Open Console` pour vérifier les erreurs CEP.

**Debug DevTools distant** : le fichier `.debug` à la racine de l'extension associe l'extension au port 8088 (port valide 1024–65534). Une fois le panel ouvert, ouvrir `http://localhost:8088/` dans Chrome pour obtenir le DevTools complet (équivalent F12). Ce fichier ne doit être présent qu'en développement, pas dans une distribution signée.

### 4. Tests de diagnostic (console ExtendScript)

```javascript
// Test 1 : le manifest est-il là ?
var f = new File(Folder.userData + "/Adobe/CEP/extensions/MediaSolution-CEP/CSXS/manifest.xml");
$.writeln("Manifest exists: " + f.exists);
if (f.exists) { f.open("r"); $.writeln(f.read()); f.close(); }
```

```javascript
// Test 2 : quelles extensions CEP sont détectées ?
var extensions = [];
var folder = new File(Folder.userData + "/Adobe/CEP/extensions/");
if (folder.exists) {
    var subfolders = folder.getFiles();
    for (var i = 0; i < subfolders.length; i++) {
        if (subfolders[i] instanceof Folder) {
            var manifest = new File(subfolders[i].fsName + "/CSXS/manifest.xml");
            if (manifest.exists) extensions.push(subfolders[i].name);
        }
    }
}
$.writeln("Found extensions: " + extensions.join(", "));
```

### 5. Problèmes courants

| Symptôme | Causes probables | Solutions |
|---|---|---|
| L'extension n'apparaît pas | XML invalide, mauvais emplacement, debug désactivé, CSXS incompatible | Vérifier la syntaxe du manifest, recopier au bon endroit, activer le debug, vérifier `RequiredRuntimeList` |
| Erreur de chargement | Chemins du manifest faux, fichiers manquants, permissions | Vérifier les fichiers, corriger les chemins relatifs, vérifier les droits |
| Interface vide | Erreur JS, CSInterface absent, chemin HTML faux | F12 dans le panel, lire la console, confirmer `CSInterface.js` |
| Rien n'aide | Problème plus profond | Vider `%APPDATA%\Adobe\CEP\logs`, réinstaller, tester avec une extension Adobe officielle |

Si le problème persiste, le plus efficace est de réduire : une extension minimale (manifest 5.0 + un `index.html` qui fait `new CSInterface()`) confirme que CEP et le debug mode fonctionnent, indépendamment de ce repo.

---

## Le bug du pont Python (juillet 2026) : pollution du JSON global

### Symptômes

- Statut du pont **rouge** (timeout) dans le panel.
- `cep_to_py.json` corrompu et incomplet : `{"args":{}}` (les propriétés `id` et `entrypoint` manquent).
- Des daemons Python lancés en boucle toutes les 30 s (processus orphelins).

### Causes racines

1. **Pollution du prototype global** : un script ou plugin tiers a pollué le `JSON` global d'ExtendScript avec un `toJSON` / `hasOwnProperty` bogué.
2. **Shadowing impossible en ES3** : `var JSON = myJSON;` dans une portée de fonction est silencieusement ignoré par le moteur Adobe (globaux intégrés en lecture seule).
3. **Bug d'écrasement récursif** : dans le polyfill json2.js, `i`, `k`, `v`, `partial` étaient déclarés dans la fonction parente `stringify` mais pas dans la fonction récursive `str`. Chaque appel récursif écrasait la mémoire du parent et vidait `partial` (d'où la perte de `id` et `entrypoint`).

### Corrections

- **`myJSON` privé** : tous les `JSON.stringify` / `JSON.parse` du host remplacés par `myJSON.stringify` / `myJSON.parse`.
- **Portée sanctuarisée** : `var i, k, v, partial;` déclaré à l'intérieur de `str`.
- **Plus de check `toJSON`** dans le sérialiseur (inutile pour nos payloads et vulnérable à la pollution).
- **`myJSON.parse` validé par `rx_one`** : le `eval` ne s'exécute qu'après validation stricte (les chaînes sont remplacées par `]`, il ne reste que de la structure JSON pure, aucun code exécutable ne peut passer).
- **Démon autonome** : `client/main.js` lance le démon en processus détaché via Node quand le health check échoue (un thread d'arrière-plan d'AE est détruit brutalement à la fin d'un script).

### Leçon d'août 2026 : ne jamais filtrer un JSON avant de le parser

Une tentative de remplacer le `eval` de `myJSON.parse` par un filtre de caractères (`rx_literal`) a causé des **gels AE en batch** : la regex supprimait les lettres des chaînes JSON (timecodes, noms), corrompant toutes les réponses du daemon. Le host les considérait en échec, retombait sur le fallback ExtendScript lourd, et AE gelait. **La validation `rx_one` + `eval` est le design sûr**; filtrer les caractères, jamais.

### Bonnes pratiques

- **Jamais de shadowing des built-ins** (`JSON`, `Math`, `String`) dans ExtendScript. Toujours un nom unique (`myJSON`).
- **Toujours `var`-déclarer les variables de boucle** dans les fonctions récursives.
- **Démon en processus autonome**, jamais dans un sous-interpréteur d'AE.

### Lire les traces de fallback

```
Images import via PyShiftAE failed, fallback ExtendScript
Préparation calque via Python indisponible, fallback ExtendScript
```

C'est le comportement normal. Le démon tourne hors d'AE, il n'a pas accès aux APIs internes (`PyFx`, `pyshiftae`) : pour toute opération qui touche au document, il répond `{"status": "fallback"}` et ExtendScript prend le relais. Les cuts, eux, sont calculés par le démon (`status: "computed"` avec les segments) puis appliqués par ExtendScript. C'est le cœur du modèle hybride, pas une panne.

---

## Session d'août 2026 : options py_aep et gels en batch

### Symptômes

Avec les 4 options expérimentales Python activées (auto-recentrage, ouverture projet, création base AEP, cuts py_aep offline) sur un batch à **noms de fichiers accentués** :

- Toutes les options retombaient en fallback avec `ModuleNotFoundError: No module named 'attrs'`.
- Les logs affichaient `fallback ExtendScript: unknown` au lieu du vrai message.
- **Freeze d'AE** pendant le batch.
- L'auto-recentrage appliquait le centre par défaut au lieu de celui du tracking, malgré les `*_tracking.json` / `*_ae.json` présents.

### Causes et corrections

| # | Cause | Correctif | Fichier |
|---|---|---|---|
| 1 | `attrs` absente de l'interpréteur du démon; `py_aep` déclare `attrs`, `PyYAML`, `fonttools`, `uharfbuzz` mais l'installation était incomplète | `python -m pip install attrs PyYAML fonttools uharfbuzz` dans l'interpréteur du démon | Environnement Python (hors repo) |
| 2 | Le daemon répond `ok:true` avec une erreur métier dans `result.status`; le host ne lisait que le champ `error` racine → `unknown` | `sendToPyShiftBridge()` expose `result.error` quand `status` n'est ni `ok` ni `computed` | `host/MediaSolution.jsx` (~ligne 428) |
| 3 | Ré-ouverture du projet en RAM après un échec py_aep (fichier modifié sur disque pendant l'opération → conflit, gel natif) | Ré-ouverture **uniquement en cas de succès**, avec fermeture des viewers d'abord | `host/MediaSolution.jsx` (flux `mediasolution_apply_cuts_pyaep`) |
| 4 | Le `é` de `forcenés` arrivait corrompu en `Ǹ` (U+01F8) dans le JSON de la mailbox; `os.path.exists()` échouait, tracking vide → recentrage par défaut | `_resolve_tracking_path()` : matching par normalisation Unicode (NFD + ASCII) + Levenshtein ≤ 2 si le chemin exact n'existe pas | `mediasolution/core.py` (hors repo) |
| 5 | `targetLayer.duration` undefined en batch → `max_frame = 0` → aucune frame analysée | Host : replis `duration` → `outPoint - inPoint` → `comp.duration`. Python : durée invalide → plage complète du tracking | `host/MediaSolution.jsx` + `mediasolution/core.py` |

### Comportement attendu après correctifs

```
Base AEP (py_aep Offline): <nom>.aep          création binaire
Auto-recentering (PyShiftAE CEPy hybride): ok  centre calculé depuis le tracking
Cuts (py_aep Offline batch): 27 créés et recentrés en binaire !  cuts binaires
```

Les messages `Open project via PyShiftAE failed` / `Images import via PyShiftAE failed` restent **normaux** (mode Standalone, fallback ExtendScript) mais affichent désormais la vraie raison au lieu de `unknown`.

---

## Session du 07/08/2026 : le serveur pipe muet (bug flush `DisconnectNamedPipe`)

### Symptômes

- Le transport affichait toujours `Transport PyShiftBridge: mailbox`, même après "Relancer le bridge".
- Le log du démon (`daemon_loop.log`) montrait `[pipe] Connexion pipe traitee: mediasolution` toutes les 30 s, mais le client ne recevait **jamais** de réponse : `read EPIPE` côté Node, `BYTES=0` côté .NET.
- Le pipe était bien créé (`\\.\pipe\mediasolution` présent), le démon single-instance tournait, et le mailbox continuait de fonctionner (le batch s'exécutait, mais via la mailbox du host).

### Piège de diagnostic : le log du démon est trompeur

`Connexion pipe traitee` est loggé **après** `ConnectNamedPipe`, avant la lecture. Une connexion loggée ne prouve pas qu'une réponse a été écrite : le serveur peut accepter puis fermer sans répondre. Pour trancher, il faut tester le pipe en client isolé avec le **même payload que le CEP** :

```json
{"endpoint": "Response", "functionName": "ping", "args": {"param1": "{}"}}
```

Réponse attendue : `{"ok": true, "result": {"status": "ok", ..., "transport": "pipe"}, "error": null}`. `EPIPE` ou zéro octet = serveur muet.

### Cause racine

Dans `_pipe_serve_one()` (bridge_daemon.py), la séquence était :

```
_write_pipe(handle, response)   # WriteFile retourne ok : données en buffer
...
DisconnectNamedPipe(handle)     # déconnexion immédiate
```

`WriteFile` retourne `ok` dès que les données sont **en buffer**, pas quand le client les a reçues. `DisconnectNamedPipe` coupait la connexion **avant** que Windows ait vidé le buffer de sortie → le client ne recevait rien (EPIPE), le serveur croyait avoir répondu.

### Correction

`time.sleep(0.05)` après `_write_pipe(handle, response)`, avant le `finally` qui déconnecte : le buffer a le temps d'être vidé vers le client. Validé par 6/6 pings pipe OK (contre 10/10 échecs avant).

### Pourquoi le debug "réparait" par magie

Pendant l'investigation, l'ajout de logs (`_log()` écrivant dans `daemon_loop.log`) entre `_write_pipe` et la déconnexion faisait passer les tests. Ce n'était pas le contenu des logs : c'était la **latence** qu'ils introduisaient, qui laissait le buffer se vider. Un symptôme classique de bug de flush : une instrumentation qui le masque.

### Ce qu'il faut retenir

- `WriteFile` sur un pipe nommé n'est pas un flush : la réponse peut être coupée par `DisconnectNamedPipe`/`CloseHandle` si on déconnecte trop vite.
- Le transport `pipe` n'était pas utilisé par le batch : les `mediasolution_*` du log daemon viennent du **host ExtendScript via la mailbox** (architectural). Le client (Node) n'utilise le pipe que pour les pings de santé, le cuts parser interactif et le recentrage.

---

## Session du 20/08/2026 : Démon indisponible et verrou orphelin par collision de PID (PID recycling)

### Symptômes

- Le statut du pont Python dans le panel CEP reste bloqué sur « Indisponible » (voyant rouge), même après avoir cliqué sur « Relancer ».
- Les fonctionnalités expérimentales (cuts pipe, auto-recentrage pipe) sont inaccessibles.
- En lançant `bridge_daemon.py` manuellement dans un terminal, le script affiche immédiatement :
  ```
  PyShiftBridge daemon already running (single-instance lock held).
  ```
  alors qu'aucun processus Python n'est en cours d'exécution.

### Cause racine : recyclage de PID sous Windows

1. Lors d'un arrêt antérieur non gracieux (redémarrage du PC, fermeture forcée), `bridge_daemon.py` avait laissé son PID dans `Documents/PyShiftAE_CEP_Bridge/bridge_daemon.lock` (ex: `22192`).
2. Sous Windows, les PIDs sont continuellement recyclés et réattribués aux nouveaux processus lancés par le système ou les applications d'arrière-plan (antivirus comme `bduserhost.exe`, navigateurs, services Windows).
3. L'ancienne fonction `_pid_alive(pid)` se contentait d'appeler `tasklist /FI "PID eq {pid}" /NH` et de tester si la sous-chaîne `str(pid)` était présente dans la sortie.
4. Dès lors qu'un processus tiers héritait de ce PID, `_pid_alive` retournait `True`, le verrou refusait tout démarrage et le démon s'arrêtait immédiatement.

### Correctif appliqué

1. **Mutex Nommé Kernel Windows** : `_kernel32.CreateMutexW(None, True, "Local\\PyShiftBridge_Daemon_SingleInstance_Mutex")`.
   - Si une instance est déjà active, `GetLastError()` retourne `ERROR_ALREADY_EXISTS` (183).
   - Si le processus meurt (crash, kill, arrêt Windows), **le noyau Windows détruit automatiquement le handle du Mutex** : aucun verrou résiduel ne peut subsister.
2. **Verrou de fichier OS** : `msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)` sur le descripteur de fichier `bridge_daemon.lock`, maintenu ouvert pendant la durée de vie du démon.
3. **Sécurisation de `_pid_alive`** : validation explicite que l'image de processus trouvée dans `tasklist /FO CSV` commence bien par `python` ou `py`.
4. **Nettoyage et sécurité I/O** : enregistrement `atexit` pour supprimer le fichier lock, et encapsuleur `_safe_print()` pour éviter tout plantage sous `pythonw` ou `stdio: 'ignore'` où `sys.stdout` est `None`.
