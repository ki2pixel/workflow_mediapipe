# STEP6 — Réduction JSON et Analytics v4.2

## Vue d'Ensemble
Le réducteur STEP6 consolide les métadonnées des étapes précédentes (audio, tracking) en fichiers JSON optimisés pour la post-production.

## Fonctionnalités v4.2
- **Tracking enrichi** : Fichier `*_tracking.json` standardisé
- **Analytics** : Histogramme de confidence et statistiques par objet
- **Expression Summary** : Résumé léger des blendshapes (optionnel)
- **Alignement temporel** : Validation et warnings audio/vidéo

## Complexité
- **Score Radon** : F (3 méthodes critiques)
- **Méthodes chaudes** : 
  - `reduce_video_json()` (F) : Traitement principal
  - `_compute_tracking_analytics()` (F) : Calcul analytics
  - `process_directory()` (E) : Gestion batch

## Configuration
```bash
# Flags d'activation
STEP6_INCLUDE_TRACKING_ANALYTICS=1
STEP6_INCLUDE_EXPRESSION_SUMMARY=1
STEP6_EXPRESSION_KEYS=mouth_open,eye_blink,head_pose
```

## Sorties
- `*_tracking.json` : Tracking standardisé (prioritaire After Effects)
- `*_audio.json` : Audio et embeddings locuteurs
- `metadata.json` : Métadonnées consolidées du projet

## Architecture du Pipeline

### Flux de Données
```
STEP5 (tracking) → STEP6 (réduction) → After Effects
STEP4 (audio)   → STEP6 (fusion)     → Post-production
```

### Étapes de Réduction

#### 1. Consolidation Tracking
- Fusion des données workers multiprocessés
- Normalisation des coordonnées et timestamps
- Enrichissement avec métadonnées (fps, résolution)

#### 2. Analytics (Optionnel)
```json
{
  "tracking_analytics": {
    "confidence_histogram": [0.1, 0.2, 0.3, 0.4],
    "object_stats": {
      "face_1": {"avg_confidence": 0.85, "frame_count": 150},
      "face_2": {"avg_confidence": 0.72, "frame_count": 120}
    }
  }
}
```

#### 3. Expression Summary (Optionnel)
```json
{
  "expression_summary": {
    "mouth_open": {"avg": 0.3, "max": 0.8, "frames_active": 45},
    "eye_blink": {"count": 12, "avg_duration": 0.15}
  }
}
```

## Patterns d'Usage

### Script After Effects
Le script `Analyse-Écart-X-depuis-JSON-et-Label-Vidéo36_good.jsx` utilise :
1. **Priorité STEP6** : Recherche `*_tracking.json` en premier
2. **Fallback STEP5** : Parsing streaming si STEP6 indisponible
3. **Pondération confidence** : `ENABLE_CONFIDENCE_WEIGHTING=1`

### Validation d'Alignement
```python
# Vérification synchronisation audio/vidéo
if audio_duration != video_duration:
    warnings.append("Décalage temporel détecté")
```

## Performance

### Optimisations
- Streaming JSON pour éviter les pics mémoire
- Parallélisation par projet
- Cache des métadonnées vidéo

### Complexité Algorithmique
- **reduce_video_json()** : O(n) où n = nombre de frames
- **_compute_tracking_analytics()** : O(m) où m = nombre d'objets
- **process_directory()** : O(p) où p = nombre de projets

## Gestion des Erreurs

### Robustesse
- Fallback silencieux sur les données manquantes
- Validation des schémas JSON
- Logs détaillés pour le debugging

### Cas Limites
- Vidéos sans tracking : JSON vide mais valide
- Audio sans embeddings : champs `embeddings` omis
- Décalage temporel : warnings dans `temporal_alignment`

## Intégrations

### Services Dépendants
- **WorkflowState** : Accès aux métadonnées du projet
- **FilesystemService** : Lecture/écriture sécurisée des JSON
- **ResultsArchiver** : Archivage des résultats finaux

### Sorties Externes
- **After Effects** : Scripts JSX de post-production
- **Analytics Dashboard** : Métriques de performance
- **API REST** : Endpoints de consultation des résultats

## Tests

### Tests Unitaires
- Validation des schémas JSON
- Calcul des analytics et expressions
- Gestion des cas d'erreur

### Tests d'Intégration
- Pipeline complet STEP4→STEP5→STEP6
- Compatibilité avec scripts After Effects
- Performance sur vidéos de différentes tailles

## Évolution Future

### v4.3 (Planifié)
- Support multi-track audio
- Analytics avancés (trajectoires, vitesses)
- Export format CSV pour analytics tools

### Améliorations Possibles
- Compression delta pour les longues séquences
- Indexation par timestamp pour accès aléatoire
- Validation croisée audio/vidéo automatique
