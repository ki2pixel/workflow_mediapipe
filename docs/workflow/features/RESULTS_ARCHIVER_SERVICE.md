# Service d'Archivage des Résultats (ResultsArchiver)

## Vue d'Ensemble

Les archives sont maintenant gérées manuellement via le système de fichiers. Chaque projet est archivé avec une structure de dossiers claire :
- `/mnt/cache/archives/{project_name}/`
  - `metadata.json`
  - `scenes/`
  - `audio/`
  - `tracking/`

Les archives sont accessibles directement via le système de fichiers et ne sont plus liées à un système de rapport automatisé.

### Problème Résolu

**Avant ResultsArchiver** :
- L'Étape 7 supprime les dossiers `projets_extraits/` après copie vers `/mnt/cache`
- Les analyses (scenes, audio, tracking) sont perdues si `/mnt/cache` est nettoyé
- Pas de traçabilité historique des analyses
- Risque d'écrasement entre projets homonymes

**Avec ResultsArchiver** :
- Les analyses sont archivées automatiquement par les Étapes 3, 4, 5
- Indexation par **hash SHA-256** du contenu vidéo (résistant aux collisions)
- Persistance dans `ARCHIVES_DIR/` (jamais supprimé par le workflow)
- Traçabilité avec timestamps de création
- Gestion des projets homonymes via dossiers horodatés uniques
- Cache en mémoire pour optimiser les accès disque répétés
- Archivage unique avec suffixe horodaté pour éviter les collisions

---

## Système d'Archivage Unique avec Suffixe Horodaté (v4.1)

### Problème Résolu

Avant l'implémentation du suffixe horodaté, les projets portant des noms identiques (ex: "projet_camille_001") entraient en collision dans `archives/`, causant l'écrasement des analyses précédentes.

### Solution Implémentée

Le système génère automatiquement des dossiers horodatés uniques au format `"<base> YYYY-MM-DD_HH-MM-SS"` pour éviter toute collision entre projets homonymes.

#### Fonctionnement

**Création de dossiers uniques** :
```python
# Dans _get_or_create_archive_project_dir()
def _get_or_create_archive_project_dir(project_name: str, create: bool = True) -> Path:
    """
    Génère un dossier projet unique avec suffixe horodaté.
    
    Args:
        project_name: Nom de base du projet (ex: "projet_camille_001")
        create: Si True, crée le dossier; si False, recherche existant
    
    Returns:
        Path: Dossier unique (ex: "archives/projet_camille_001 2025-10-06_14-45-30/")
    """
    if create:
        # Création: ajoute suffixe horodaté
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        unique_name = f"{project_name} {timestamp}"
        archive_dir = ARCHIVES_DIR / unique_name
        archive_dir.mkdir(parents=True, exist_ok=True)
        # Cache en mémoire pour réutilisation dans la session
        _session_archive_dirs[project_name] = archive_dir
        return archive_dir
    else:
        # Lecture: recherche le dossier le plus récent pour ce projet
        return _find_most_recent_archive_dir(project_name)
```

**Lecture robuste des archives** :
```python
def _list_matching_project_dirs(project_name: str) -> List[Path]:
    """Trouve tous les dossiers d'archives pour un projet donné."""
    pattern = f"{project_name} *"
    return sorted(ARCHIVES_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

def _find_most_recent_archive_dir(project_name: str) -> Optional[Path]:
    """Retourne le dossier d'archive le plus récent pour un projet."""
    matching_dirs = _list_matching_project_dirs(project_name)
    return matching_dirs[0] if matching_dirs else None
```

#### Structure Résultante

```
archives/
├── projet_camille_001 2025-10-06_14-45-30/  # Session 1
│   ├── a7b3c9.../
│   └── f2d8e1.../
├── projet_camille_001 2025-10-06_16-20-15/  # Session 2 (même nom, pas d'écrasement)
│   ├── b9c4d2.../
│   └── e8f7g3.../
└── projet_camille_002 2025-10-06_18-30-45/  # Projet différent
    └── [...]
```

#### Avantages

- **Élimination des collisions** : Projets homonymes peuvent être archivés sans écrasement
- **Traçabilité temporelle** : Chaque archive porte sa date de création
- **Compatibilité ascendante** : Lecture automatique des archives existantes (avec/sans suffixe)
- **Performance** : Cache en mémoire pour éviter les recalculs répétés dans une session

#### Interface Utilisateur

Le `VisualizationService.get_available_projects()` enrichit automatiquement les métadonnées :

```python
{
  "projects": [
    {
      "name": "projet_camille_001",
      "display_base": "projet_camille_001",
      "archive_timestamp": "2025-10-06_16-20-15",
      "archive_path": "/path/to/archives/projet_camille_001 2025-10-06_16-20-15",
      // ... autres métadonnées
    }
  ]
}
```

**Affichage UI** : L'interface cache les suffixes techniques et affiche uniquement le nom de base, avec un tooltip indiquant l'horodatage pour la traçabilité.

---

## API Principale

### 1. `archive_project_analysis(project_name: str) -> dict`

**Description** : Scanne le dossier projet et archive tous les artefacts d'analyse disponibles.

**Utilisation typique** : Appelé par l'Étape 7 (Finalisation) avant le nettoyage du dossier projet.

**Implémentation v4.1 avec cache process-level** :

```python
# Cache en mémoire pour réutiliser le même dossier horodaté par session
_PROJECT_ARCHIVE_DIRS: dict[str, Path] = {}

@classmethod
def _get_or_create_archive_project_dir(cls, base_name: str) -> Path:
    """Obtient ou crée le dossier projet horodaté unique pour cette session.
    
    Args:
        base_name: Nom de base du projet (ex: "49 Camille")
    
    Returns:
        Path du dossier horodaté (ex: "archives/49 Camille 2025-10-06_14-45-30/")
    
    Notes:
        - Cache en mémoire: même dossier pour toutes les écritures d'une session
        - Suffixe horodaté au format YYYY-MM-DD_HH-MM-SS
        - Création avec parents=True, exist_ok=True
    """
    if base_name in cls._PROJECT_ARCHIVE_DIRS:
        return cls._PROJECT_ARCHIVE_DIRS[base_name]
    
    ts = ResultsArchiver._format_timestamp()
    proj_dir = config.ARCHIVES_DIR / f"{base_name} {ts}"
    proj_dir.mkdir(parents=True, exist_ok=True)
    cls._PROJECT_ARCHIVE_DIRS[base_name] = proj_dir
    return proj_dir

@staticmethod
def _list_matching_project_dirs(base_name: str) -> list[Path]:
    """Liste tous les dossiers d'archives correspondant au nom de base.
    
    Args:
        base_name: Nom de base du projet
    
    Returns:
        Liste des dossiers triés par date (plus récent en premier)
    
    Matching:
        - Exact match: "49 Camille"
        - Préfixé: "49 Camille 2025-10-06_14-45-30"
    """
    root = config.ARCHIVES_DIR
    if not root.exists():
        return []
    
    candidates: list[Path] = []
    prefix = f"{base_name} "
    
    for d in root.iterdir():
        if not d.is_dir():
            continue
        n = d.name
        if n == base_name or n.startswith(prefix):
            candidates.append(d)
    
    # Sort newest-first (timestamp lexicographique)
    candidates.sort(key=lambda p: p.name, reverse=True)
    return candidates
```

**Exemple** :
```python
from services.results_archiver import ResultsArchiver

# Archiver un projet complet avant finalisation (Étape 7)
summary = ResultsArchiver.archive_project_analysis("49 Camille")

print(f"Projet: {summary['project_name']}")
print(f"Vidéos traitées: {summary['processed']}")
print(f"Fichiers archivés: {summary['copied']}")
for detail in summary['details']:
    print(f"  - {detail['video']}: {detail['copied']}")
```

**Retour** :
```python
{
    "project_name": "49 Camille",
    "processed": 3,
    "copied": 3,
    "details": [
        {
            "video": "docs/video1.mp4",
            "copied": {
                "scenes": True,
                "audio": True,
                "tracking": True,
                "archived": True
            },
            "archive_dir": "/path/to/archives/49 Camille 2025-10-06_14-45-30/a7b3c9.../"
        },
        # ... autres vidéos
    ]
}
```

### 2. `get_archive_paths(project_name: str, video_hash: str, create: bool = False) -> ArchivePaths`

**Description** : Résout les chemins d'archive pour un projet et un hash vidéo.

**Paramètre `create`** :
- `True` : Mode écriture, utilise `_get_or_create_archive_project_dir()` (dossier horodaté unique)
- `False` : Mode lecture, utilise `_list_matching_project_dirs()` (recherche le plus récent)

**Implémentation** :

```python
@staticmethod
def get_archive_paths(project_name: str, video_hash: str, create: bool = False) -> ArchivePaths:
    """Résout les chemins d'archive avec logique écriture/lecture.
    
    Args:
        project_name: Nom de base du projet
        video_hash: Hash SHA-256 de la vidéo
        create: True pour écriture (crée dossier horodaté), False pour lecture
    
    Returns:
        ArchivePaths avec project_dir et video_hash_dir
    """
    if create:
        # Écriture: dossier horodaté unique (cache session)
        project_dir = ResultsArchiver._get_or_create_archive_project_dir(project_name)
    else:
        # Lecture: dossier le plus récent correspondant
        matches = ResultsArchiver._list_matching_project_dirs(project_name)
        project_dir = matches[0] if matches else (config.ARCHIVES_DIR / project_name)
    
    video_hash_dir = project_dir / video_hash
    return ArchivePaths(project_dir=project_dir, video_hash_dir=video_hash_dir)
```

**Exemple écriture** :
```python
video_hash = ResultsArchiver.compute_video_hash(video_path)
paths = ResultsArchiver.get_archive_paths("49 Camille", video_hash, create=True)
# paths.video_hash_dir = archives/49 Camille 2025-10-06_14-45-30/<hash>/
```

**Exemple lecture** :
```python
video_hash = ResultsArchiver.compute_video_hash(video_path)
paths = ResultsArchiver.get_archive_paths("49 Camille", video_hash, create=False)
# paths.video_hash_dir = archives/49 Camille 2025-10-06_16-20-15/<hash>/ (plus récent)
```

{{ ... }}
