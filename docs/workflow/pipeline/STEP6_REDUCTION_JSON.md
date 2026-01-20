# Documentation Technique - Étape 6 : Réduction JSON

## Description Fonctionnelle

### Objectif
L'Étape 6 est une étape intermédiaire cruciale qui optimise les fichiers de métadonnées générés par les analyses vidéo et audio. Son rôle est de réduire la taille de ces fichiers JSON en ne conservant que les informations strictement nécessaires pour les scripts After Effects, améliorant ainsi les performances et la fluidité du processus de post-production.

### Rôle dans le Pipeline
- **Position** : Étape intermédiaire entre le suivi vidéo (STEP5) et la finalisation (STEP7)
- **Prérequis** : Fichiers JSON de tracking (`.json`) et d'analyse audio (`_audio.json`)
- **Sortie** : Fichiers JSON (`.json` et `_audio.json`) modifiés sur place, avec une structure de données allégée
- **Étape suivante** : Finalisation (STEP7)

### Valeur Ajoutée
- **Optimisation des performances** : Réduit significativement le temps de chargement et de traitement des données dans After Effects.
- **Réduction de la taille des fichiers** : Économise de l'espace de stockage et facilite le transfert des données.
- **Standardisation des données** : Garantit que seuls les champs pertinents sont présents, évitant les erreurs d'interprétation.
- **Automatisation complète** : S'intègre de manière transparente dans le workflow sans intervention manuelle.

## Spécifications Techniques

### Environnement Virtuel
- **Environnement utilisé** : `env/` (environnement principal)
- **Activation** : `source env/bin/activate`
- **Partage** : Utilise le même environnement que les étapes 1, 2 et 6.

### Technologies et Bibliothèques Principales
```python
import json         # Manipulation des fichiers JSON
import os           # Opérations sur le système de fichiers
from pathlib import Path  # Manipulation moderne des chemins
import logging      # Journalisation des opérations
```

### Paramètres de Configuration
Le script `json_reducer.py` accepte les paramètres suivants en ligne de commande pour plus de flexibilité :
- `--base_dir` : Chemin de base du projet (contenant `projets_extraits`).
- `--work_dir` : Chemin explicite vers le répertoire `projets_extraits`.
- `--keyword` : Mot-clé pour filtrer les dossiers de projet (par défaut : 'Camille').
- `--log_dir` : Répertoire pour stocker les fichiers de logs (par défaut : `logs/step6`).

## Architecture et Algorithmes

### Workflow de Réduction
1.  **Découverte des projets** : Le script scanne le répertoire de travail à la recherche de projets correspondant au mot-clé.
2.  **Identification des paires de fichiers** : Pour chaque vidéo, il recherche les fichiers `.json` et `_audio.json` correspondants.
3.  **Réduction Vidéo (`.json`)** :
    *   Parcourt l'analyse de chaque frame.
    *   Pour chaque objet suivi, il ne conserve que les champs essentiels : `id`, `centroid_x`, `source`, `label`, `active_speakers`.
    *   Les données volumineuses comme les `landmarks` et `blendshapes` sont supprimées.
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