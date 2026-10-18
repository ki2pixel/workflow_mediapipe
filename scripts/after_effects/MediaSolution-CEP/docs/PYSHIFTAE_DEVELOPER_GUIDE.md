# Développer un panel CEP avec PyShiftAE v1.0.1

**TL;DR** : PyShiftAE et py_aep couvrent le calcul et la manipulation, mais aucun des deux ne touche le DOM d'AE en direct. L'architecture gagnante est un relais : Python calcule, ExtendScript exécute. Le client (Node) parle au démon via le pipe nommé maison, le host ExtendScript via la mailbox.

## Ce que l'écosystème Python sait faire (et ne pas faire)

Deux approches complémentaires :

1. **PyShiftAE (v1.0.1)** : API Python orientée objet de haut niveau, par connexion hôte.
2. **py_aep (v0.13.0)** : manipulation **offline** du binaire `.aep`, sans qu'AE soit ouvert.

**Possible** : création d'objets AE en mode hôte (dossiers, import de métrages); manipulation binaire offline (cuts par duplication de calques et in/out points, rapide); calculs lourds (JSON, CSV, recentrage) dans un démon sans geler l'UI.

**Impossible ou limité** :

- `py_aep.new()` sur AE 2024 et antérieurs : le squelette binaire vient d'AE 2026, l'ouverture dans 2024 échoue avec `chunk in file too big`. La création initiale du projet doit passer par le fallback ExtendScript.
- La position, l'échelle et le point d'ancrage ne se modifient pas en mode hôte v1.0.1 sans ExtendScript.
- Le pont standalone n'a pas accès à l'UI d'AE (ouvrir une comp dans le viewer, par exemple).

## L'architecture hybride : calcul et exécution séparés

```
 CEP Panel (HTML/JS)
  │
  ├── 1. Demande de traitement ──> [ Moteur Python (Calculs) ]
  │                                 - Analyse de fichiers lourds (CSV, JSON)
  │                                 - Snapping et calcul géométrique (centroïdes)
  │                                 - Retourne les coordonnées et timings (JSON)
  │
  └── 2. Reçoit les calculs ─────> [ Hôte ExtendScript (AE DOM) ]
                                    - Duplique les calques
                                    - Modifie les points In/Out
                                    - Applique les positions, scales, labels
```

Pourquoi ça tient : ExtendScript gère 100 % des modifications d'AE nativement (zéro limitation d'API); Python absorbe les calculs lourds sans bloquer l'interface. La mailbox était le transport nominal historique du host ExtendScript (batch) et le reste. **Depuis le 07/08/2026**, `bridge_daemon.py` expose aussi un serveur de pipe nommé Windows maison (`\\.\pipe\mediasolution`, ctypes, thread principal), transport du client (Node) : le client le détecte au health check et bascule automatiquement pipe ↔ mailbox. Le pipe CEPy de PyShiftAE, lui, n'existe dans aucune version (v1.0.1 comprise) — voir [confirmation_diagnostic.md](./confirmation_diagnostic.md). Le client fait le health check via Node, le démon calcule les cuts, ExtendScript applique.

## Exemple : découpe et recentrage

### 1. Python (`core.py`) : calculer, sans toucher à AE

```python
def calculer_decoupe_recentrage(csv_path, comp_width, frame_rate):
    segments_calcules = []
    segments_calcules.append({
        "startTime": 0.0,
        "endTime": 5.0,
        "centerX": 450.0,
        "labelIndex": 3
    })
    return {"status": "computed", "segments": segments_calcules}
```

### 2. Client (`main.js`) : coordonner, puis transmettre

```javascript
sendCommandToPythonMailbox('calculer_decoupe_recentrage', {
    csv_path: "/path/to/cuts.csv",
    comp_width: 1920,
    frame_rate: 25
}, 10000, function(res) {
    if (res && res.ok && res.result.status === "computed") {
        var segmentsJson = JSON.stringify(res.result.segments);
        var escapedJson = segmentsJson.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
        csInterface.evalScript('appliquerSegmentsAE("' + escapedJson + '")', function(jsxRes) {
            console.log("Segments appliqués avec succès !");
        });
    }
});
```

### 3. Host ExtendScript : exécuter

```javascript
function appliquerSegmentsAE(segmentsJson) {
   // ne JAMAIS utiliser JSON.parse natif côté ExtendScript :
   // le global JSON peut être pollué par des plugins tiers. Toujours myJSON.parse
   // (polyfill privé du host, validé par rx_one).
   var segments = myJSON.parse(segmentsJson);
   var comp = app.project.activeItem;
   var targetLayer = comp.layer(1);

   app.beginUndoGroup("Application Hybride");
   for (var i = 0; i < segments.length; i++) {
      var seg = segments[i];
      var newLayer = targetLayer.duplicate();
      // ExtendScript applique ce que Python v1.0.1 ne peut pas :
      newLayer.inPoint = seg.startTime;
      newLayer.outPoint = seg.endTime;
      newLayer.property("Anchor Point").setValue([seg.centerX, targetLayer.height / 2]);
      newLayer.label = seg.labelIndex;
   }
   targetLayer.remove();
   app.endUndoGroup();

   return "{\"success\": true}";
}
```

## Le contrat de réponse du bridge

Le daemon répond **toujours** `ok:true` dès qu'il a traité la requête, même en cas d'échec métier. Les erreurs remontent dans `result.status` (`"error"` / `"fallback"`) avec le détail dans `result.error`. Le host vérifie donc `result.status`, pas le `ok` racine :

```javascript
//   "ok" / "computed"  -> succès
//   "error" / "fallback" -> erreur métier (détail dans result.error)
if (res && res.ok && res.result && res.result.status === "ok") { ... }
```

Depuis la session d'août 2026, `sendToPyShiftBridge()` expose automatiquement `result.error` quand `status` n'est ni `ok` ni `computed` : les logs affichent le vrai message (ex. traceback) au lieu de `unknown`.

## Erreurs connues

1. **`ModuleNotFoundError: No module named 'attrs'`** : dépendance manquante dans l'interpréteur du démon; `py_aep` échoue à l'import → `result.status:"error"` avec traceback. Dépannage dans [PY_AEP_DEVELOPER_GUIDE.md](./PY_AEP_DEVELOPER_GUIDE.md).
2. **Chemins corrompus (accents)** : la mailbox peut corrompre les caractères non-ASCII (`é` → `Ǹ`). Résolution par matching de nom dans `_resolve_tracking_path()`.
3. **`duration=None` en batch** : `targetLayer.duration` peut être `undefined` côté ExtendScript → recentrage par défaut. Double correctif host + Python.
4. **Freeze AE** : ne jamais ré-ouvrir le projet en RAM après un échec du mode binaire.
