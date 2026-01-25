# Documentation Technique - Étape 6 : Réduction JSON

> **Code-Doc Context** – Part of the 7‑step pipeline; see `../README.md` for the uniform template. Backend hotspots: low complexity (radon C) in `json_reducer.py`; straightforward data processing.

---

## Purpose & Pipeline Role

### Objectif
L'Étape 6 est une étape intermédiaire cruciale qui optimise les fichiers de métadonnées générés par les analyses vidéo et audio. Son rôle est de réduire la taille de ces fichiers JSON en ne conservant que les informations strictement nécessaires pour les scripts After Effects, améliorant ainsi les performances et la fluidité du processus de post-production.

### Rôle dans le Pipeline
- **Position** : Étape intermédiaire entre le suivi vidéo (STEP5) et la finalisation (STEP7)
- **Prérequis** : Fichiers JSON de tracking (`.json`) et d'analyse audio (`_audio.json`)
- **Sortie** : Fichiers JSON (`.json` et `_audio.json`) modifiés sur place, avec une structure de données allégée
- **Étape suivante** : Finalisation (STEP7)

### Valeur Ajoutée
- **Optimisation des performances** : Réduit significativement le temps de chargement et de traitement des données dans After Effects
- **Réduction de la taille des fichiers** : Économise de l'espace de stockage et facilite le transfert des données
- **Standardisation des données** : Garantit que seuls les champs pertinents sont présents, évitant les erreurs d'interprétation
- **Automatisation complète** : S'intègre de manière transparente dans le workflow sans intervention manuelle

---

## Inputs & Outputs

### Inputs
- **JSON tracking** : Fichiers de tracking vidéo de STEP5 avec landmarks/blendshapes
- **JSON audio** : Fichiers d'analyse audio de STEP4
- **Configuration** : Paramètres de réduction via variables d'environnement

### Outputs
- **JSON réduits** : Fichiers allégés avec champs essentiels uniquement
- **Taille optimisée** : Réduction de 74-95% selon `STEP5_EXPORT_VERBOSE_FIELDS`
- **Logs détaillés** : Journal de réduction dans `logs/step6/`

---

## Command & Environment

### Commande WorkflowCommandsConfig
```python
# Exemple de commande (voir WorkflowCommandsConfig pour la commande exacte)
python workflow_scripts/step6/json_reducer.py --base-dir . --work-dir projets_extraits/ --keyword Camille
```

### Environnement Virtuel
- **Environnement utilisé** : `env/` (environnement principal)
- **Activation** : `source env/bin/activate`
- **Partage** : Utilisé également par les étapes 1, 2 et 6

---

## Dependencies

### Bibliothèques Principales
```python
import json         # Manipulation des fichiers JSON
import os           # Opérations sur le système de fichiers
from pathlib import Path  # Manipulation moderne des chemins
import logging      # Journalisation des opérations
```

### Dépendances Externes
- Aucune dépendance externe complexe
- Traitement purement Python natif

---

## Configuration

### Variables d'Environnement
- **STEP5_EXPORT_VERBOSE_FIELDS** : Contrôle la verbosité des exports STEP5 (false par défaut)
- **STEP6_KEYWORD_FILTER** : Mot-clé pour filtrer les projets (défaut: 'Camille')
- **STEP6_LOG_LEVEL** : Niveau de logging (INFO, DEBUG, WARNING)

### Paramètres de Configuration
- `--base_dir` : Chemin de base du projet
- `--work_dir` : Chemin vers `projets_extraits`
- `--keyword` : Filtre de projets
- `--log_dir` : Répertoire des logs

---

## Known Hotspots

### Complexité Backend
- **`json_reducer.py`** : Complexité faible (radon C) dans `process_directory` et `reduce_video_json`
- **Points d'attention** : Validation de structure JSON, gestion des fichiers corrompus

---

## Metrics & Monitoring

### Indicateurs de Performance
- **Débit de réduction** : Fichiers/seconde traités
- **Taux de compression** : % réduction taille des fichiers
- **Intégrité** : Validation des structures JSON réduites
- **Temps de traitement** : Durée moyenne par projet

### Patterns de Logging
```python
# Logs de progression
logger.info(f"Réduction {project_name} - {current}/{total}")

# Logs de compression
logger.info(f"Compression: {original_size}MB -> {reduced_size}MB ({ratio:.1%} reduction)")

# Logs d'erreur
logger.error(f"Échec réduction {json_file}: {error}")
```

---

## Failure & Recovery

### Modes d'Échec Communs
1. **JSON corrompu** : Logging et passage au fichier suivant
2. **Structure invalide** : Tentative de réduction avec fallback
3. **Permissions insuffisantes** : Pause et alerte utilisateur
4. **Espace disque insuffisant** : Pause et nettoyage

### Procédures de Récupération
```bash
# Réessayer avec logging debug
STEP6_LOG_LEVEL=DEBUG python workflow_scripts/step6/json_reducer.py

# Nettoyer les fichiers temporaires
python workflow_scripts/step6/json_reducer.py --cleanup-temp

# Validation post-réduction
python scripts/validate_step6_output.py
```

---

## Related Documentation

- **Pipeline Overview** : `../README.md`
- **Testing Strategy** : `../technical/TESTING_STRATEGY.md`
- **WorkflowState Integration** : `../core/ARCHITECTURE_COMPLETE_FR.md`
- **STEP5 Configuration** : `../pipeline/STEP5_SUIVI_VIDEO.md`

---

*Generated with Code-Doc protocol – see `../cloc_stats.json` and `../complexity_report.txt`.*
4.  **Réduction Audio (`_audio.json`)** :
    *   Parcourt l'analyse de chaque frame.
    *   Ne conserve que les champs `is_speech_present` et `active_speaker_labels`.
5.  **Sauvegarde sur place** : Les fichiers JSON sont écrasés avec leur version réduite pour optimiser l'espace disque.
6.  **Journalisation** : Chaque action (fichier traité, champs supprimés, erreurs) est consignée dans un fichier de log détaillé.

### Structure des Données Réduites

#### Format `.json` (Réduit)
```json
{
  "frames_analysis": [
    {
      "frame": 42,
      "tracked_objects": [
        {
          "id": "person_123",
          "centroid_x": 320.5,
          "source": "tracking",
          "label": "person",
          "active_speakers": ["speaker_1", "speaker_2"]
        }
      ]
    }
  ]
}
```

#### Format `_audio.json` (Réduit)
```json
{
  "frames_analysis": [
    {
      "frame": 42,
      "audio_info": {
        "is_speech_present": true,
        "active_speaker_labels": ["speaker_1", "speaker_2"]
      }
    }
  ]
}
```

## Intégration et Utilisation

Cette étape est conçue pour être appelée automatiquement par le `WorkflowService` dans le cadre d'une séquence.

```python
# Exemple d'appel via le service
WorkflowService.run_step("STEP6")
```

Elle s'exécute après que le tracking vidéo (STEP5) ait généré ses données et avant que l'étape de finalisation (STEP7) ne rassemble tous les résultats pour l'archivage.

### Notes Techniques
-   Si un fichier audio correspondant à un fichier de tracking n'est pas trouvé, le traitement de cette paire est simplement ignoré.
-   Les erreurs de traitement d'un fichier (ex: JSON corrompu) n'interrompent pas le traitement global ; l'erreur est journalisée et le script passe au fichier suivant.
-   Les fichiers produits par STEP5 peuvent avoir été générés avec STEP5_EXPORT_VERBOSE_FIELDS=false (comportement par défaut). STEP6 reste compatible car utils.tracking_optimizations.apply_tracking_and_management() garantit toujours les champs requis (id, centroid_x, bbox_width, bbox_height, source, active_speakers). Si STEP5_EXPORT_VERBOSE_FIELDS=true, les champs volumineux supplémentaires (landmarks, eos.*) sont simplement ignorés. Les tests tests/unit/test_step5_export_verbose_fields.py couvrent ces variantes.