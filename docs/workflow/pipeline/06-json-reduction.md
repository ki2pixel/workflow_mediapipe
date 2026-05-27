# STEP6 JSON Reduction Documentation

## TL;DR
STEP6 réduit les JSON volumineux de STEP4/STEP5 en format optimisé After Effects, calculant analytics tracking, alignement temporel, et statistiques expressions tout en préservant compatibilité STEP7.

## Contexte Métier
Les JSON bruts contiennent des données denses (frames-by-frame, blendshapes détaillés) inutiles pour post-production. STEP6 optimise pour After Effects : réduction objets trackés, calculs agrégés, alignement audio/vidéo.

## Architecture Pipeline

### Flux de données
1. **Scan projets** : Dossiers `projets_extraits/*{keyword}*`
2. **Résolution paires** : `{stem}_audio.json` + `{stem}_tracking.json`
3. **Réduction tracking** : Filtrage objets, calcul analytics/expressions
4. **Réduction audio** : Timeline parole simplifiée
5. **Alignement temporel** : Synchronisation audio/vidéo
6. **Écriture atomique** : Remplacement sécurisé

### Fonctions Clés

#### `stream_reduce_video_json(tracking_in, tracking_out, legacy_path, audio_meta)` (Complexité F)
**Rôle** : Réduit en flux continu le JSON volumineux de tracking de STEP5 en format After Effects-compatible tout en conservant une empreinte RAM stable de O(1).

**Algorithme détaillé** :
1. **Parsing itératif (`ijson.parse`)** : Lecture du fichier d'entrée sous forme de flux d'événements SAX pour extraire les métadonnées (FPS, total_frames) sans charger le JSON en mémoire.
2. **Streaming des frames (`ijson.items`)** : Parcours itératif de la liste volumineuse `frames_tracking` ou `tracked_objects` objet par objet.
3. **Filtrage à la volée** : Pour chaque objet détecté, conservation des propriétés essentielles (`id`, `centroid_x`, `centroid_y`, `source`, `label`, `confidence`, `bbox_*`, `active_speakers`).
4. **Résolution active_speakers** : Fusion directe à la volée avec les données de `speaking_sources.audio` extraites de `audio_meta`.
5. **Calculs statistiques incrémentaux** : Calcul des moyennes/max des expressions (blendshapes) par objet sans conserver l'historique complet en RAM.
6. **Écriture streaming** : Écriture progressive des frames réduites dans un fichier temporaire.

**Optimisations** :
- **Consommation RAM O(1)** : L'utilisation d'`ijson` maintient une mémoire tampon constante, indépendamment de la durée de la vidéo ou du nombre d'objets détectés.
- **Skip sélectif** : Ignore instantanément les blendshapes non requis pour économiser les I/O disque.
- **Écriture atomique** : Remplacement sécurisé via `os.replace` après écriture complète du fichier temporaire.

#### `_compute_tracking_analytics(reduced_tracking)` (Complexité F)
**Rôle** : Calcule statistiques agrégées sur tracking pour diagnostics qualité.

**Métriques calculées** :
- **Histogramme confiance** : Buckets (0-0.25, 0.25-0.5, etc.)
- **Stats objets** : Nombre total, par frame, durée vie, densité
- **Stats labels** : Distribution classes détectées
- **Stats spatiales** : Centroides moyens, variances bbox

**Algorithme** :
1. **Indexation frames** : Map frame_num → objets pour accès O(1)
2. **Calculs temporels** : Durée vie objets, transitions frames
3. **Agrégations statistiques** : Moyennes/variances par label
4. **Histogrammes** : Distribution valeurs confiance/tailles

## Gestion Erreurs

### Schémas JSON incompatibles
- **Comportement** : Skip fichier, log warning, continuation
- **Validation** : `_is_raw_tracking_schema()` / `_is_reduced_tracking_schema()`

### Données manquantes/corrompues
- **Comportement** : Fallbacks gracieux, valeurs par défaut
- **Logging** : Warnings non-bloquants

### Échecs écriture
- **Comportement** : Atomic writes avec cleanup temp files
- **Récupération** : os.replace() préserve intégrité

## Optimisations Performance

### Indexation objets
- Map frame→objets pour accès rapide
- Calculs statistiques en une passe

### Traitement batch
- Scan récursif dossiers projets
- Progress logging pour monitoring

### Réduction mémoire
- **Streaming itératif (`ijson`)** : Utilisation du parseur `ijson` pour lire et filtrer les données frame par frame en flux continu; la RAM reste en O(1) même sur des tracking de plusieurs centaines de mégaoctets; évite les crashs par manque de mémoire (OOM) fréquents sur les architectures traditionnelles.
- **Libération immédiate** : Les références aux anciens dictionnaires de frames sont immédiatement éliminées pour permettre le ramasse-miettes (GC) régulier.

## Trade-offs

### ❌ Réduction agressive vs ❌ Fidélité données
- **Choix** : Conservation ciblée (centroids, speakers, expressions)
- **Coût** : Perte données détaillées (blendshapes complets)
- **Bénéfice** : JSON 10x plus petits, parsing AE rapide

### ❌ Calculs lourds vs ❌ Métriques utiles
- **Choix** : Analytics optionnels (flag `STEP6_INCLUDE_TRACKING_ANALYTICS`)
- **Coût** : Overhead computationnel pour diagnostics
- **Bénéfice** : Insights qualité tracking sans outils externes

### ❌ Complexité logique vs ❌ Maintenabilité
- **Choix** : Logique centralisée dans fonctions complexes
- **Coût** : Tests difficiles, edge cases nombreux
- **Bénéfice** : Pipeline robuste, évolutif

## Golden Rule
**Les JSON réduits doivent rester compatibles STEP7** : modifications schéma nécessitent tests régression complets et mise à jour scripts consommateurs.

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
```</content>
<parameter name="path">/home/kidpixel/workflow_mediapipe/docs/workflow/pipeline/step6-json-reduction.md