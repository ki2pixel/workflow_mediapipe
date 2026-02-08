# Réduction JSON

**TL;DR** : Réduit les fichiers JSON de tracking de 74-95% tout en enrichissant les données avec analytics, résumés d'expressions et alignement audio/vidéo. Génère le format standard pour After Effects.

## Le Problème : JSON Tracking Trop Volumineux

Les fichiers JSON de tracking STEP5 contiennent des dizaines de milliers de landmarks et blendshapes par frame, ce qui les rend extrêmement lourds (plusieurs centaines de MB) et lents à traiter dans After Effects. Tu as besoin d'une version optimisée qui conserve les données essentielles tout en étant performante.

## Notre Solution : Réduction Intelligente avec Enrichissement

Nous réduisons drastiquement la taille des fichiers JSON en supprimant les données volumineuses (landmarks 3D, eos.*) tout en ajoutant des analytics avancés. Le système génère un format standardisé optimisé pour After Effects avec des métriques de confidence et des résumés d'expressions.

### ❌ Conservation brute (anti-pattern)
```python
# Approche inefficace - tout conserver
tracking_data = {
    "landmarks": [[x,y,z] for _ in range(468*2500)],  # 300MB !
    "blendshapes": full_data  # 50MB !
}
# Résultat : After Effects plante, chargement 2-3 minutes
```

### ✅ Réduction intelligente (pattern recommandé)
```python
# Approche optimisée - réduire et enrichir
reduced_data = {
    "tracking_analytics": confidence_histogram,  # +1MB
    "expression_summary": key_metrics,           # +0.5MB
    "tracked_objects": centroids_only             # 12MB total
}
# Résultat : After Effects instantané, données enrichies
```

### Flux de Réduction Intelligente

1. **Analyse des fichiers** : Scan des projets avec JSON tracking et audio
2. **Fusion données** : Intégration tracking + audio pour enrichissement
3. **Réduction volumineuse** : Suppression landmarks/blendshapes détaillés
4. **Enrichissement analytics** : Histogrammes confidence, statistiques par objet
5. **Résumé expressions** : Synthèse des blendshapes principaux
6. **Alignement temporel** : Détection désynchronisations audio/vidéo
7. **Écriture atomique** : Sauvegarde sécurisée avec fichier temporaire

## Utilisation Rapide

### Lancement Automatique

```bash
# Via l'interface web
# Clique sur "Étape 6 : Réduction JSON" dans l'interface

# Via API
curl -X POST http://localhost:5000/run/STEP6

# Dans une séquence complète
const steps = ['STEP1', 'STEP2', 'STEP3', 'STEP4', 'STEP5', 'STEP6'];
await apiService.runCustomSequence(steps);
```

### Exécution Manuelle (Debug)

```bash
# Activation environnement principal
source env/bin/activate

# Exécution depuis projets_extraits
cd projets_extraits
python ../workflow_scripts/step6/json_reducer.py

# Monitoring des logs
tail -f logs/step6/json_reducer_*.log
```

### Résultat Attendu

```
# Avant réduction (STEP5)
video1_tracking.json    # 250 MB (landmarks + blendshapes complets)
video1_audio.json       # 15 MB (timeline complète)

# Après réduction (STEP6)
video1_tracking.json    # 12 MB (-95% avec analytics)
video1_audio.json       # 2 MB (-87% essentiel uniquement)
```

## Configuration Essentielle

### Variables d'Environnement

```bash
# Contrôle verbosité STEP5 (impact sur réduction)
STEP5_EXPORT_VERBOSE_FIELDS=0        # 0 = optimisé (défaut), 1 = verbose

# Options STEP6
STEP6_INCLUDE_TRACKING_ANALYTICS=1   # Analytics confidence/statistiques
STEP6_INCLUDE_EXPRESSION_SUMMARY=1    # Résumé blendshapes
STEP6_EXPRESSION_KEYS=jawOpen,mouthSmileLeft,mouthSmileRight  # Blendshapes à inclure

# Filtres et logging
STEP6_KEYWORD_FILTER=Camille           # Filtre projets
STEP6_LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING
```

### Configuration Analytics

```python
# Expression keys par défaut
DEFAULT_EXPRESSION_KEYS = [
    'jawOpen', 'mouthSmileLeft', 'mouthSmileRight',
    'browDownLeft', 'browDownRight', 'eyeBlinkLeft', 'eyeBlinkRight'
]

# Tracking analytics
TRACKING_ANALYTICS_CONFIG = {
    'confidence_histogram_bins': 10,
    'include_object_stats': True,
    'include_temporal_alignment': True
}
```

## Formats de Données

### JSON Tracking Réduit

```json
{
  "video_filename": "video1.mp4",
  "total_frames": 2500,
  "fps": 25.0,
  "tracking_analytics": {
    "confidence_histogram": {
      "0.0-0.1": 45,
      "0.9-1.0": 1245
    },
    "object_stats": {
      "total_objects": 2,
      "avg_confidence": 0.87,
      "detection_rate": 0.92
    },
    "temporal_alignment": {
      "audio_video_mismatch": false,
      "sync_offset_frames": 0
    }
  },
  "expression_summary": {
    "jawOpen": {"min": 0.0, "max": 0.45, "avg": 0.12, "active_frames": 847},
    "mouthSmileLeft": {"min": 0.0, "max": 0.78, "avg": 0.23, "active_frames": 623}
  },
  "tracked_objects": [
    {
      "frame": 1,
      "objects": [
        {
          "id": "person_1",
          "confidence": 0.95,
          "centroid_x": 320.5,
          "centroid_y": 240.2,
          "bbox_width": 120,
          "bbox_height": 150,
          "source": "tracking",
          "label": "person",
          "active_speakers": ["SPEAKER_00"]
        }
      ]
    }
  ]
}
```

### JSON Audio Réduit

```json
{
  "video_filename": "video1.mp4",
  "total_frames": 2500,
  "fps": 25.0,
  "frames_analysis": [
    {
      "frame": 1,
      "audio_info": {
        "is_speech_present": true,
        "num_distinct_speakers_audio": 1,
        "active_speaker_labels": ["SPEAKER_00"],
        "timecode_sec": 0.0
      }
    }
  ]
}
```

## Analytics et Enrichissement

### Tracking Analytics

```python
# Histogramme confidence
confidence_histogram = {
    "0.0-0.1": 45,      # Faible confiance
    "0.1-0.2": 123,     # Moyenne-basse
    "0.8-0.9": 890,     # Haute confiance
    "0.9-1.0": 1245     # Très haute confiance
}

# Statistiques par objet
object_stats = {
    "total_objects": 2,
    "avg_confidence": 0.87,
    "detection_rate": 0.92,
    "frames_with_objects": 2300
}
```

### Expression Summary

```python
# Résumé par blendshape
expression_summary = {
    "jawOpen": {
        "min": 0.0,
        "max": 0.45,
        "avg": 0.12,
        "active_frames": 847,  # Frames où valeur > 0.01
        "dominant_threshold": 0.1
    },
    "mouthSmileLeft": {
        "min": 0.0,
        "max": 0.78,
        "avg": 0.23,
        "active_frames": 623
    }
}
```

### Alignement Temporel

```python
# Détection désynchronisations
temporal_alignment = {
    "audio_video_mismatch": False,  # True si décalage détecté
    "sync_offset_frames": 0,         # Décalage en frames
    "audio_duration_sec": 100.0,
    "video_duration_sec": 100.0,
    "fps_mismatch": False
}
```

## Trade-offs par Mode de Réduction

| Mode STEP5 | Taille originale | Taille réduite | Réduction | Quand l'utiliser |
|------------|-----------------|---------------|-----------|-----------------|
| **Verbose** | 250MB | 65MB | 74% | Debug, développement |
| **Optimisé** | 45MB | 12MB | 95% | Production, After Effects |

## Trade-offs par Enrichissement

| Option | Taille ajoutée | Valeur | Risques | Quand l'utiliser |
|--------|----------------|-------|---------|-----------------|
| **Analytics** | +1MB | Métriques confidence | Surcharge si inutile | Post-production avancée |
| **Expression Summary** | +0.5MB | Stats blendshapes | Calculs supplémentaires | Animation 3D |
| **Alignement Temporel** | +0.1MB | Sync audio/vidéo | Complexité | Contenus synchronisés |

## Analogie : Bibliothèque vs Index

Pense à la réduction comme une **bibliothèque** vs son **index**. Les **données brutes STEP5** sont la bibliothèque complète : tous les livres (landmarks, blendshapes) sur des étagères immenses. Le **JSON réduit STEP6** est l'index : il ne contient que les références essentielles (centroids, confidence) plus des analytics (histogrammes, résumés) qui te permettent de trouver instantanément ce dont tu as besoin.

## Monitoring et Logs

### Structure des Logs

```
logs/step6/
└── json_reducer_20240120_143022.log
```

### Exemple de Logs

```
2024-01-20 14:30:22 - INFO - Processing project: projet_camille_001 (1/3)
2024-01-20 14:30:23 - INFO - Loading tracking data: video1_tracking.json (250MB)
2024-01-20 14:30:24 - INFO - Computing tracking analytics...
2024-01-20 14:30:25 - INFO - Computing expression summary...
2024-01-20 14:30:26 - INFO - Compression: 250MB -> 12MB (95.2% reduction)
2024-01-20 14:30:27 - INFO - Successfully wrote video1_tracking.json
2024-01-20 14:30:28 - INFO - Audio reduction: 15MB -> 2MB (86.7% reduction)
```

### Métriques Clés

```python
# Statistiques de traitement
logging.info(f"Compression: {original_size}MB -> {reduced_size}MB ({ratio:.1%} reduction)")
logging.info(f"Projects processed: {success_count}/{total_count}")
logging.info(f"Total space saved: {space_saved_mb}MB")
```

## Dépendances et Prérequis

### Environnement Principal

```bash
# Activation environnement principal
source env/bin/activate

# Dépendances minimales (Python standard)
# json, os, pathlib, logging
# Aucune dépendance externe requise
```

### Prérequis Fichiers

```bash
# Structure attendue
projets_extraits/
├── projet_camille_001/
│   └── docs/
│       ├── video1.mp4
│       ├── video1_tracking.json    # Généré par STEP5
│       └── video1_audio.json        # Généré par STEP4
```

## Résolution de Problèmes

### JSON Corrompu

```bash
# Diagnostic
python -c "import json; json.load(open('video1_tracking.json'))"

# Solution
# Le système ignore les fichiers corrompus et continue
# Logs détaillés pour identification
```

### Permissions Insuffisantes

```bash
# Diagnostic
ls -la projets_extraits/projet_camille_001/docs/

# Solution
sudo chown -R $USER:$USER projets_extraits/
chmod -R 755 projets_extraits/
```

### Espace Disque Insuffisant

```bash
# Diagnostic
df -h projets_extraits/

# Solution
# Nettoyage fichiers temporaires
find projets_extraits/ -name "*.tmp" -delete

# Monitoring espace
du -sh projets_extraits/*/*_tracking.json
```

### Fichiers Audio Manquants

```bash
# Comportement attendu
# Si _audio.json manquant, le tracking est quand même réduit
# Warning dans les logs mais traitement continue
```

## Tests et Validation

### Test de Fonctionnement

```bash
# Créer fichiers test
mkdir -p test_reduction/docs
# Créer video1_tracking.json volumineux
# Créer video1_audio.json

# Exécuter réduction
source env/bin/activate
cd test_reduction
python ../workflow_scripts/step6/json_reducer.py

# Vérifier réduction
du -h docs/video1_tracking.json
du -h docs/video1_audio.json
```

### Validation Automatique

```python
def validate_step6_output():
    """Vérifie que tous les JSON réduits sont valides."""
    import json
    from pathlib import Path
    
    base_dir = Path("projets_extraits")
    
    for json_file in base_dir.rglob("*_tracking.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)
            
            # Vérifier structure minimale
            required_keys = ['video_filename', 'total_frames', 'fps', 'tracked_objects']
            if not all(key in data for key in required_keys):
                print(f"❌ {json_file}: Structure JSON invalide")
                return False
            
            # Vérifier cohérence frames
            total_frames = data['total_frames']
            tracked_objects = data['tracked_objects']
            
            if len(tracked_objects) != total_frames:
                print(f"❌ {json_file}: Incohérence frames ({len(tracked_objects)} vs {total_frames})")
                return False
            
            # Vérifier analytics si activé
            if 'tracking_analytics' in data:
                analytics = data['tracking_analytics']
                if 'confidence_histogram' not in analytics:
                    print(f"❌ {json_file}: Analytics incomplets")
                    return False
            
            # Vérifier taille raisonnable
            file_size_mb = json_file.stat().st_size / (1024*1024)
            if file_size_mb > 50:  # Plus de 50MB = problème
                print(f"⚠️ {json_file}: Fichier volumineux ({file_size_mb:.1f}MB)")
            
            print(f"✅ {json_file}: {total_frames} frames, {file_size_mb:.1f}MB")
            
        except Exception as e:
            print(f"❌ Erreur lecture {json_file}: {e}")
            return False
    
    print("✅ Validation réussie: tous les JSON réduits sont valides")
    return True
```

### Test Performance

```bash
# Mesurer temps de traitement
time python workflow_scripts/step6/json_reducer.py

# Comparer tailles avant/après
du -sh projets_extraits/*/*_tracking.json.bak  # Avant
du -sh projets_extraits/*/*_tracking.json      # Après
```

## Intégration Pipeline

### Entrée pour STEP7

L'étape 6 prépare les données optimisées pour After Effects :
- **JSON standardisé** : Format compatible avec scripts AE
- **Analytics** : Métriques de confidence et expressions
- **Taille réduite** : Chargement rapide dans AE
- **Alignement temporel** : Synchronisation audio/vidéo validée

### WorkflowState Integration

```python
# Intégration avec l'état centralisé
ws = get_workflow_state()
ws.update_step_status("STEP6", "running")
ws.set_step_field("STEP6", "current_project", "projet_camille_001")
ws.update_step_progress("STEP6", current=1, total=3)
```

### Compatibilité After Effects

Le format réduit est optimisé pour les scripts AE :
```javascript
// Script After Effects
var trackingData = JSON.parse(file.readContents("video1_tracking.json"));

// Accès rapide aux données essentielles
for (var i = 0; i < trackingData.tracked_objects.length; i++) {
    var frame = trackingData.tracked_objects[i];
    var objects = frame.objects;
    
    for (var j = 0; j < objects.length; j++) {
        var obj = objects[j];
        // Utilisation centroid_x, centroid_y, bbox_width, bbox_height
        // Pas de landmarks volumineux à traiter
    }
}
```

## Pièges Courants et Solutions

### Piège #1 : Fichiers toujours volumineux
**Solution** : Vérifier `STEP5_EXPORT_VERBOSE_FIELDS=0` dans l'environnement STEP5.

### Piège #2 : Analytics manquants
**Solution** : Activer `STEP6_INCLUDE_TRACKING_ANALYTICS=1` et `STEP6_INCLUDE_EXPRESSION_SUMMARY=1`.

### Piège #3 : Alignement audio/vidéo incorrect
**Solution** : Vérifier les logs `temporal_alignment` et ajuster si nécessaire.

### Piège #4 : Perte de données essentielles
**Solution** : Le système préserve toujours les champs requis (id, centroid_x, bbox_width/height, confidence).

### Piège #5 : Fichiers temporaires résiduels
**Solution** : Écriture atomique avec nettoyage automatique des fichiers `.tmp`.

L'étape 6 transforme les données brutes de tracking en un format optimisé et enrichi, réduisant drastiquement la taille des fichiers tout en ajoutant des analytics précieux pour la post-production. Les scripts After Effects peuvent maintenant charger et traiter les données instantanément.

---

## Golden Rule

**Réduis avant d'enrichir ; sinon tu obtiens des fichiers volumineux avec des données inutiles qui ralentissent After Effects.**
