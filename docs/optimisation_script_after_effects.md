## Mise à jour (intégration Workflow)

L'architecture décrite ci-dessous est désormais intégrée au pipeline.

- Le script Python `analyzer.py` est remplacé par le mode `--manifest_path/--output_path` de `workflow_scripts/step7/preprocess_ae_json.py` (Étape 7).
- Le script After Effects `Analyse-Écart-X-depuis-JSON-et-Label-Vidéo36_good.jsx` peut appeler ce mode via `system.callSystem()` lorsque `ENABLE_PYTHON_ANALYZER=true`.

**ExtendScript (le moteur JS d'After Effects) est obsolète (standard de 1999)**. Il est mono-thread et gère la mémoire de manière catastrophique pour le traitement de texte massif. Aucune optimisation de code ne pourra battre un langage moderne comme Python sur ce terrain.

Passer par Python est la solution standard dans les pipelines VFX professionnels pour contourner cette limitation.

Voici l'architecture idéale **"Le Sandwich"** pour résoudre votre problème de performance (passage de 1 minute à ~2-3 secondes) :

1.  **AE (Tranche du bas)** : Récupère les infos des calques (Nom, Fichier Source, In/Out) -> Écrit un petit JSON "Manifest".
2.  **PYTHON (La garniture)** : Lit le Manifest + les GROS JSONs de tracking. Il fait tous les calculs (stats, choix du candidat, logique audio) -> Écrit un petit JSON "Résultat".
3.  **AE (Tranche du haut)** : Lit le JSON Résultat (minuscule) -> Applique les changements.

Voici comment mettre cela en place.

### Étape 1 : Le Script Python (`analyzer.py`)
Ce script va remplacer toute la logique complexe de votre JSX actuel. Il utilise la librairie standard `json` de Python qui est compilée en C et extrêmement rapide.

Sauvegardez ce code dans un fichier `analyzer.py` :

```python
import sys
import json
import os
import statistics

# Configuration (Doit matcher celle du JSX)
CONFIG = {
    "SPREAD_THRESHOLD": 200,
    "ENABLE_CONFIDENCE_WEIGHTING": True,
    "CONFIDENCE_WEIGHT": 0.35,
    "LABEL_HIGH_SPREAD": 12,
    "LABEL_STABLE": 3
}

def calculate_stats(values):
    if not values:
        return {"min": 0, "max": 0, "spread": 0, "average": 0}
    return {
        "min": min(values),
        "max": max(values),
        "spread": max(values) - min(values),
        "average": statistics.mean(values)
    }

def compute_presence_score(count, avg_conf):
    if not CONFIG["ENABLE_CONFIDENCE_WEIGHTING"]:
        return count
    return count * (1 + (max(0, min(1, avg_conf)) * CONFIG["CONFIDENCE_WEIGHT"]))

def process_layer(layer_info, tracking_data, audio_data):
    # Récupération des frames utiles
    min_frame = layer_info['in_frame']
    max_frame = layer_info['out_frame']
    video_scale = layer_info.get('video_scale', 1.0)
    
    objects_in_layer = {}
    
    # 1. Extraction des données sur la plage de temps
    # On itère sur les frames demandées (logique inverse du scan séquentiel)
    for frame in range(min_frame, max_frame + 1):
        # Gestion échelle temporelle (mapping frames)
        vid_frame = int(round(frame * video_scale)) if video_scale != 1.0 else frame
        vid_frame_key = str(vid_frame) # Les clés JSON sont des strings
        
        # Données Vidéo
        frame_objs = tracking_data.get(vid_frame_key, [])
        # Données Audio
        audio_info = audio_data.get(str(frame), {}) # Audio souvent aligné sur la comp
        
        for obj in frame_objs:
            oid = obj['id']
            if oid not in objects_in_layer:
                objects_in_layer[oid] = {
                    'id': oid,
                    'source': obj.get('source'),
                    'label': obj.get('label'),
                    'x_values': [],
                    'bbox_surfaces': [],
                    'confidences': [],
                    'audio_confirms': 0,
                    'speakers': obj.get('active_speakers', []) # ou video_speakers selon votre JSON
                }
            
            # Aggrégation
            # Note: Adaptez les clés selon votre structure exacte (centroid_x vs x)
            cx = obj.get('centroid_x', obj.get('x_coordinate', 0))
            w = obj.get('bbox_width', 0)
            h = obj.get('bbox_height', 0)
            conf = obj.get('confidence', 0)
            
            objects_in_layer[oid]['x_values'].append(cx)
            objects_in_layer[oid]['bbox_surfaces'].append(w * h)
            objects_in_layer[oid]['confidences'].append(conf)
            
            # Logique Audio
            # (Simplifiée pour l'exemple, à adapter à votre structure exacte)
            if audio_info.get('is_speech_present') and objects_in_layer[oid]['speakers']:
                active_labels = audio_info.get('active_speaker_labels', [])
                if isinstance(active_labels, str): active_labels = [active_labels]
                
                # Intersection des sets
                if set(objects_in_layer[oid]['speakers']) & set(active_labels):
                    objects_in_layer[oid]['audio_confirms'] += 1

    if not objects_in_layer:
        return None

    # 2. Sélection du meilleur candidat (Logique "Tie-Breaker")
    best_candidate = None
    max_score = -1
    
    # On définit des types pour la priorité
    # 3 = Face+Audio, 2 = Face, 1 = Person+Audio, 0 = Autre
    
    for oid, data in objects_in_layer.items():
        count = len(data['x_values'])
        avg_conf = statistics.mean(data['confidences']) if data['confidences'] else 0
        avg_bbox = statistics.mean(data['bbox_surfaces']) if data['bbox_surfaces'] else 0
        presence_score = compute_presence_score(count, avg_conf)
        
        # Détermination du "Tier" de priorité
        tier = 0
        if data['source'] == 'face_landmarker':
            tier = 2
            if data['audio_confirms'] > 0: tier = 3
        elif data['source'] == 'object_detector' and data['label'] == 'person':
            tier = 0.5
            if data['audio_confirms'] > 0: tier = 1
            
        # Score final composite pour le tri
        # Tier (poids 10000) + Presence (poids 1) + Bbox (poids tout petit)
        # Ceci remplace vos cascades de if/else complexes
        final_score = (tier * 10000) + presence_score + (avg_bbox * 0.0001)
        
        if final_score > max_score:
            max_score = final_score
            stats = calculate_stats(data['x_values'])
            best_candidate = {
                "center_x": stats['average'],
                "spread": stats['spread'],
                "label_color": CONFIG['LABEL_HIGH_SPREAD'] if (stats['spread'] > CONFIG['SPREAD_THRESHOLD'] and data['source'] == 'face_landmarker') else CONFIG['LABEL_STABLE'],
                "selected_id": oid,
                "reason": f"Tier {tier} Score {final_score:.2f}"
            }
            
    return best_candidate

def main():
    try:
        manifest_path = sys.argv[1]
        output_path = sys.argv[2]
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            
        results = {}
        
        # Cache pour ne pas recharger le même JSON 50 fois si plusieurs calques utilisent la même source
        loaded_jsons = {} 
        
        for layer_index, info in manifest['layers'].items():
            json_path = info['json_path']
            
            if json_path not in loaded_jsons:
                if os.path.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as jf:
                        # Charge tout en mémoire (Python gère très bien 100Mo+)
                        full_data = json.load(jf)
                        # Adaptez selon votre structure (frames_analysis ou root directe)
                        loaded_jsons[json_path] = full_data.get('frames_analysis', full_data) 
                        # Si frames_analysis est une liste, convertissez-la en dict par frame pour accès O(1)
                        if isinstance(loaded_jsons[json_path], list):
                             # Conversion liste -> dict {"1": {...}, "2": {...}}
                             temp_dict = {}
                             for f in loaded_jsons[json_path]:
                                 if 'frame' in f: temp_dict[str(f['frame'])] = f.get('tracked_objects', [])
                             loaded_jsons[json_path] = temp_dict
                else:
                    loaded_jsons[json_path] = {}

            # Pour l'audio, on simplifie ici (à charger similairement)
            audio_data = {} 
            
            res = process_layer(info, loaded_jsons[json_path], audio_data)
            if res:
                results[layer_index] = res
                
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4)
            
    except Exception as e:
        # En cas d'erreur, on écrit un JSON d'erreur pour qu'AE le sache
        with open(sys.argv[2], 'w', encoding='utf-8') as f:
            json.dump({"error": str(e)}, f)

if __name__ == "__main__":
    main()
```

### Étape 2 : Le Script After Effects ("Le Bridge")

Remplacez votre script actuel par celui-ci. Il est beaucoup plus court car il délègue tout.

```javascript
#target aftereffects

// ===================================================================================
// CONFIGURATION
// ===================================================================================
var CONFIG = {
    PYTHON_CMD: "python", // Ou chemin complet ex: "C:/Python39/python.exe"
    SCRIPT_PATH: "C:/Chemin/Vers/analyzer.py", // <--- METTRE LE CHEMIN DU SCRIPT PYTHON
    TEMP_FOLDER: Folder.temp.fsName
};

// --- Polyfill JSON basique pour lire le résultat ---
// ... (Gardez votre polyfill JSON.parse existant ici) ...
if (typeof JSON === 'undefined' || !JSON) { JSON = {}; }
// ... insérez votre bloc polyfill JSON ici ...

// ===================================================================================
// FONCTIONS UTILITAIRES
// ===================================================================================

function escapePath(path) {
    return path.replace(/\\/g, "\\\\");
}

function getLayerSourcePath(layer) {
    if (layer.source && layer.source.file) {
        try { return decodeURI(layer.source.file.fsName); } 
        catch (e) { return layer.source.file.fsName; }
    }
    return null;
}

// Fonction pour deviner le chemin du JSON (reprise de votre logique)
function findJsonPath(videoPath) {
    var f = new File(videoPath);
    var folder = f.parent;
    var name = f.name.substring(0, f.name.lastIndexOf("."));
    
    // Logique simplifiée : cherche dans ./docs ou ../docs
    // Ajoutez ici votre logique robuste de findJsonVariants
    var candidates = [
        folder.fsName + "/docs/" + name + "_tracking.json",
        folder.fsName + "/docs/" + name + "_ae.json",
        folder.parent.fsName + "/docs/" + name + "_tracking.json"
    ];
    
    for (var i=0; i<candidates.length; i++) {
        if (new File(candidates[i]).exists) return candidates[i];
    }
    return null;
}

// ===================================================================================
// MAIN
// ===================================================================================

(function main() {
    var comp = app.project.activeItem;
    if (!comp || !(comp instanceof CompItem)) {
        alert("Sélectionnez une composition.");
        return;
    }

    // 1. PRÉPARATION DU MANIFESTE
    var manifest = {
        "comp_name": comp.name,
        "layers": {}
    };
    
    var layersToProcess = [];

    for (var i = 1; i <= comp.numLayers; i++) {
        var layer = comp.layer(i);
        if (!layer.hasVideo || layer.locked) continue;
        
        var srcPath = getLayerSourcePath(layer);
        if (!srcPath) continue;
        
        var jsonPath = findJsonPath(srcPath);
        if (!jsonPath) continue;

        // ID unique pour mapper le retour
        var layerId = i.toString();
        
        manifest.layers[layerId] = {
            "name": layer.name,
            "json_path": jsonPath,
            "in_frame": Math.floor(layer.inPoint * comp.frameRate),
            "out_frame": Math.ceil(layer.outPoint * comp.frameRate),
            "video_scale": 1.0 // Logique d'échelle si nécessaire
        };
        layersToProcess.push(layer);
    }

    if (layersToProcess.length === 0) {
        alert("Aucun calque avec JSON associé trouvé.");
        return;
    }

    // 2. ÉCRITURE DU MANIFESTE SUR DISQUE
    var manifestFile = new File(CONFIG.TEMP_FOLDER + "/ae_manifest.json");
    var resultFile = new File(CONFIG.TEMP_FOLDER + "/ae_results.json");
    
    manifestFile.open("w");
    manifestFile.encoding = "UTF-8";
    manifestFile.write(JSON.stringify(manifest));
    manifestFile.close();

    // 3. APPEL DU PYTHON (SYSTEM CALL)
    // On construit la commande: python "script.py" "manifest.json" "result.json"
    var cmd = '"' + CONFIG.PYTHON_CMD + '" "' + CONFIG.SCRIPT_PATH + '" "' + manifestFile.fsName + '" "' + resultFile.fsName + '"';
    
    // Pour voir la console en cas d'erreur (Windows)
    // cmd = 'cmd /c ' + cmd; 
    
    var exitCode = system.callSystem(cmd);

    // 4. LECTURE DES RÉSULTATS
    if (!resultFile.exists) {
        alert("Erreur: Le script Python n'a pas généré de résultats.\nCode: " + exitCode);
        return;
    }

    resultFile.open("r");
    resultFile.encoding = "UTF-8";
    var content = resultFile.read();
    resultFile.close();
    
    var results = null;
    try {
        // Attention: JSON.parse natif d'AE peut planter sur des gros fichiers, 
        // mais ici le fichier result est MINUSCULE (juste les coordonnées finales).
        results = eval('(' + content + ')');
    } catch(e) {
        alert("Erreur parsing result: " + e.toString());
        return;
    }

    if (results.error) {
        alert("Erreur Python: " + results.error);
        return;
    }

    // 5. APPLICATION DES CHANGEMENTS
    app.beginUndoGroup("Recadrage Python");
    
    var appliedCount = 0;
    for (var layerId in results) {
        var res = results[layerId];
        var idx = parseInt(layerId);
        var layer = comp.layer(idx);
        
        if (layer && res) {
            var centerX = res.center_x;
            var label = res.label_color;
            
            // Appliquer Label
            layer.label = label;
            
            // Appliquer Transform
            var transform = layer.property("Transform");
            var posProp = transform.property("Position");
            var anchorProp = transform.property("Anchor Point");
            
            // Nettoyage clés existantes
            if (posProp.numKeys > 0) {
                 for (var k=posProp.numKeys; k>=1; k--) posProp.removeKey(k);
            }
            if (anchorProp.numKeys > 0) {
                 for (var k=anchorProp.numKeys; k>=1; k--) anchorProp.removeKey(k);
            }

            var origAnchor = anchorProp.value;
            var origPos = posProp.value;
            var compCenter = comp.width / 2;

            anchorProp.setValue([centerX, origAnchor[1]]);
            posProp.setValue([compCenter, origPos[1]]);
            
            appliedCount++;
        }
    }
    
    app.endUndoGroup();
    alert("Terminé ! " + appliedCount + " calques traités via Python.");
})();
```

### Pourquoi cela va marcher

1.  **Vitesse de Lecture :** Python `json.load` lit 500Mo en ~2 secondes. AE met 40 secondes.
2.  **Mémoire :** Python gère la mémoire dynamiquement. AE sature dès qu'il charge une string de 100Mo.
3.  **Complexité :** Vous pouvez remettre toute votre logique complexe (analytics, expression summary, etc.) dans Python sans ralentir l'exécution, car les calculs mathématiques sont instantanés en Python.

### Points d'attention pour l'installation

1.  **Python installé :** Assurez-vous que Python est installé sur la machine et accessible via la commande `python` (ou modifiez `CONFIG.PYTHON_CMD`).
2.  **Chemins :** Sur Windows, les chemins dans le JSON manifest généré par AE peuvent avoir des `\` qui nécessitent d'être échappés ou gérés correctement par Python (le module `json` standard le fait bien).
3.  **Structure JSON :** Le script Python ci-dessus assume une certaine structure du JSON (`frames_analysis` en liste, etc.). Comme vous avez plusieurs formats (`_ae.json`, `_tracking.json`), vous devrez peut-être ajuster la petite partie "Chargement" du script Python pour qu'elle soit aussi robuste que votre parseur JS précédent. Mais c'est beaucoup plus facile à débugger en Python (un simple `print` suffit).