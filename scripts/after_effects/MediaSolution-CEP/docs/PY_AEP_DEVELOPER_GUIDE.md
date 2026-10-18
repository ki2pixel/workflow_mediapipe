# Développer avec py_aep (manipulation binaire offline)

**TL;DR** : py_aep lit et écrit le binaire `.aep` sur disque, sans qu'AE soit ouvert. C'est 300× plus rapide qu'ExtendScript pour les cuts, mais ça impose une orchestration stricte : ExtendScript sauvegarde, py_aep modifie, ExtendScript recharge. Jamais les deux en même temps sur le même projet.

## Ce que py_aep sait faire (et ne pas faire)

**Possible** :

- Modifications directes sur disque : dupliquer 50 calques et ajuster leurs in/out points prend ~0,1 s là où ExtendScript met 30 s.
- Création de projets vierges via `py_aep.new()` (voir la compatibilité ci-dessous).
- Import de médias (`import_file`), création de comps (`add_comp`), ajout de calques.
- Ajustement `inPoint` / `outPoint`, `label`, etc.
- Lecture complète d'un projet existant : dossiers, comps, calques, même complexes.

**Impossible ou limité** :

- **Compatibilité descendante de `py_aep.new()`** : les projets de zéro sont injectés avec un squelette binaire extrait d'AE 2026. Un tel projet refuse de s'ouvrir sur AE 2024 (`chunk in file too big`). Pour les versions anciennes, la création initiale revient à ExtendScript.
- **UI** : py_aep ne peut pas ouvrir une comp dans le viewer, rafraîchir la timeline ou changer la sélection.
- **Conflits disque/RAM** : si ExtendScript modifie le projet en RAM pendant que py_aep écrit sur disque, le projet se désynchronise ou se corrompt. L'orchestration de la sauvegarde est obligatoire.

## Le relais ExtendScript ↔ py_aep

```
 CEP Panel (JavaScript)
  │
  ├── 1. Initialisation ──────> [ ExtendScript (moteur interne AE) ]
  │                              - Crée le projet (si AE 2024)
  │                              - Importe les images
  │                              - SAUVEGARDE LE PROJET (.aep)
  │
  ├── 2. Traitement lourd ────> [ py_aep (démon Python) ]
  │                              - Ouvre le .aep sur le disque
  │                              - Applique les centaines de cuts
  │                              - Modifie Anchor Point et labels
  │                              - Sauvegarde et écrase le .aep
  │
  └── 3. Rafraîchissement ────> [ ExtendScript (moteur interne AE) ]
                                 - Ré-ouvre le .aep modifié
                                 - Ouvre la composition dans le viewer
```

Deux raisons à ce modèle : ExtendScript garde la compatibilité logicielle et l'UI pendant que Python écrase le goulot de performance; et en modifiant un projet existant plutôt qu'en en créant un nouveau, py_aep respecte la version binaire d'origine, donc les coupes offline fonctionnent aussi bien sur AE 2020 que sur AE 2026.

## Exemple : appliquer des cuts en binaire

### Python (hors ligne)

```python
import py_aep

def apply_cuts_offline(aep_path: str, segments: list) -> dict:
    try:
        app = py_aep.open(aep_path)
        comp = app.project.item(1)  # première comp
        video_layer = comp.layer(1)

        for seg in segments:
            new_layer = video_layer.duplicate()
            new_layer.in_point = seg["startTime"]
            new_layer.out_point = seg["endTime"]
            new_layer.label = 3

        video_layer.remove()
        app.project.save()
        return {"status": "ok", "message": "Cuts appliqués en binaire"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

### ExtendScript hôte

```javascript
function executerTraitementBinaire() {
   // 1. Sauvegarde impérative avant l'intervention de py_aep
   app.project.save();
   var aepPath = app.project.file.fsName;

   // 2. Appel au démon Python
   logMessage("Mode py_aep : Sauvegarde et exécution binaire...");
   var pyResult = callPythonBridge("apply_cuts_offline", {
       aep_path: aepPath,
       segments: [...]
   });

   // 3. Ré-ouverture UNIQUEMENT en cas de succès
   if (pyResult.status === "ok") {
       logMessage("Mode py_aep : Réouverture du projet...");
       app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
       app.open(new File(aepPath));
       app.project.activeItem.openInViewer();
       logMessage("Cuts appliqués avec succès !");
   }
}
```

## Dépannage : les quatre pièges connus (août 2026)

### 1. `ModuleNotFoundError: No module named 'attrs'`

`py_aep` est une **copie locale du code source** (`Documents/Scripts/py_aep-0.13.0/src`) ajoutée au `sys.path` par `bridge_daemon.py`; ce n'est pas un package pip. Ses dépendances (`pyproject.toml`) doivent être installées dans **l'interpréteur exact du démon** (vérifiable via `Get-CimInstance Win32_Process` sur `bridge_daemon.py`) :

```bash
python -m pip install attrs PyYAML fonttools uharfbuzz
```

Ne pas supprimer le dossier local `py_aep-0.13.0` : le démon l'importe par chemin relatif.

### 2. Chemins corrompus par la mailbox

La transmission ExtendScript → JSON → Python peut corrompre les caractères non-ASCII : `forcenés` devient `forcenǸs` (U+01F8). `os.path.exists()` échoue silencieusement, le tracking n'est pas lu, recentrage par défaut. **Correctif** : résoudre le chemin par matching de nom dans le dossier cible (normalisation NFD + réduction ASCII + distance de Levenshtein ≤ 2), comme `_resolve_tracking_path()` de `mediasolution/core.py`. Ne jamais faire confiance au chemin brut transmis par le host.

### 3. `duration=None` en batch

`targetLayer.duration` peut être `undefined` côté ExtendScript pendant un batch → le bridge reçoit `duration=None` → `max_frame=0` → aucune frame analysée → `applied:false`. **Correctif en double couche** : le host calcule `layerDuration` avec replis (`duration` → `outPoint - inPoint` → `comp.duration`); côté Python, une durée invalide ou sans frame s'étend à toute la plage du tracking.

### 4. Ne jamais ré-ouvrir un projet après un échec binaire

Après un échec, `app.open(app.project.file)` est interdit : le projet en RAM est la seule source de vérité tant que py_aep n'a pas réussi sa sauvegarde atomique. Ré-ouvrir pendant que le fichier est en cours de modification provoque un **gel natif d'AE**. La ré-ouverture (avec fermeture préalable des viewers) ne se fait qu'en cas de succès.
