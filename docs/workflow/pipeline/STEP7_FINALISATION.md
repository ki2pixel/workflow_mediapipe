# Documentation Technique - Étape 7 : Finalisation

## Description Fonctionnelle

### Objectif
L'Étape 7 constitue la phase finale du pipeline de traitement vidéo MediaPipe. Elle consolide tous les résultats générés par les étapes précédentes, valide l'intégrité des données, organise les fichiers dans une structure finale cohérente, et effectue le transfert vers la destination de stockage définitive avec nettoyage des fichiers temporaires.

**Note importante** : Cette étape préserve systématiquement le répertoire d'archives (`ARCHIVES_DIR`) qui contient les analyses persistantes pour consultation ultérieure.

### Rôle dans le Pipeline
- **Position** : Septième et dernière étape du pipeline (STEP7)
- **Prérequis** : Projets complets avec tous les fichiers générés (CSV, JSON audio [optionnel], JSON tracking réduits par STEP6)
- **Sortie** : Archives finales organisées dans la destination de stockage
- **Étape suivante** : Aucune (fin du pipeline)

### Valeur Ajoutée
- **Consolidation complète** : Rassemblement de tous les artefacts de traitement en un ensemble cohérent
- **Validation d'intégrité** : Vérification que tous les fichiers requis sont présents et valides
- **Organisation structurée** : Création d'une hiérarchie de fichiers standardisée pour archivage
- **Nettoyage automatique** : Suppression des fichiers temporaires et de travail après transfert réussi
- **Protection des archives** : Préservation systématique du répertoire `ARCHIVES_DIR` qui contient les analyses persistantes
- **Restauration optionnelle** : Possibilité de restaurer les analyses archivées dans le dossier de sortie final
- **Traçabilité** : Logging complet des opérations de finalisation pour audit

## Spécifications Techniques

### Environnement Virtuel
- **Environnement utilisé** : `env/` (environnement principal)
- **Activation** : `source env/bin/activate`
- **Partage** : Utilisé également par les étapes 1 et 2

### Technologies et Bibliothèques Principales

#### Manipulation de Fichiers et Système
```python
import shutil       # Opérations de copie et déplacement de fichiers/dossiers
import os           # Interface système d'exploitation
from pathlib import Path  # Manipulation moderne des chemins
```

#### Compatibilité NTFS/fuseblk (copies sans métadonnées POSIX)

Sur des destinations montées en NTFS via FUSE (`fuseblk`), les opérations `chmod/utime` échouent fréquemment (`EPERM`). Pour garantir la finalisation sans erreurs, la stratégie suivante est appliquée:

1. Détection du support `chmod` sur la destination (création d'un fichier temporaire + tentative `os.chmod`).
2. Si supporté: copie standard via `shutil.copytree()` (préservation métadonnées POSIX).
3. Sinon (mode « sans métadonnées »):
   - Essai `rsync -a --no-perms --no-owner --no-group --no-times` (supprime les warnings `utime`).
   - À défaut, `cp -r --no-preserve=mode,ownership`.
   - À défaut, fallback Python (parcours `os.walk` + `shutil.copyfile`, sans `copystat`).

Implications:
- Le contenu est préservé intégralement; les permissions/propriétaires/timestamps ne sont pas conservés (comportement attendu sur NTFS).
- Les logs détaillent la stratégie retenue.

#### Gestion des Destinations Existantes
Pour améliorer la robustesse lors de la finalisation, l'étape gère automatiquement les cas où le répertoire de destination existe déjà, en appliquant une stratégie de fusion et de repli.

- **Copie tolérante** : Utilisation de `shutil.copytree()` avec `dirs_exist_ok=True` pour permettre la fusion de contenu dans un répertoire cible pré-existant, évitant les erreurs `FileExistsError`.
- **Stratégie de fallback pour suppression** : Si la suppression du répertoire existant échoue (permissions, FS incompatibles), génération automatique d'un chemin alternatif (`_compute_alternative_output_dir`) au format `nom_projet__finalized_YYYYmmdd_HHMMSS[_n]`.
- **Logs détaillés** : Chaque tentative de copie/suppression est consignée, facilitant le diagnostic en cas d'échec.

#### Validation et Logging
```python
import json         # Validation des fichiers JSON générés
import logging      # Logging complet des opérations
from datetime import datetime  # Horodatage des opérations
```

### Formats d'Entrée et de Sortie

#### Structure d'Entrée Attendue
```
projets_extraits/
├── projet_camille_001/
│   └── docs/
│       ├── video1.mp4              # Vidéo traitée
│       ├── video1.csv              # Scènes (STEP3)
│       ├── video1_audio.json       # Analyse audio (STEP4) [optionnel]
│       ├── video1_tracking.json    # Tracking (STEP5) [requis]
│       ├── video2.mov              # Vidéo traitée
│       ├── video2.csv              # Scènes (STEP3)
│       ├── video2_audio.json       # Analyse audio (STEP4) [optionnel]
│       └── video2_tracking.json    # Tracking (STEP5) [requis]
└── projet_camille_002/
    └── docs/
        └── [structure similaire]
```

#### Structure de Sortie Générée
```
${CACHE_ROOT_DIR}/                  # Destination finale (défaut : /mnt/cache)
├── projet_camille_001/
│   └── docs/
│       ├── video1.mp4
│       ├── video1.csv
│       ├── video1_audio.json
│       ├── video1_tracking.json
│       ├── video2.mov
│       ├── video2.csv
│       ├── video2_audio.json
│       └── video2_tracking.json
└── projet_camille_002/
    └── docs/
        └── [structure identique]
```

### Paramètres de Configuration

#### Configuration des Répertoires
```python
# Répertoire de travail (source)
WORK_DIR = Path(os.getcwd())  # projets_extraits/

# Répertoire de destination finale
OUTPUT_DIR = config.CACHE_ROOT_DIR  # Normalisé et imposé par la configuration

# Répertoire de logs
LOG_DIR = BASE_DIR / "logs" / "step7"
```

Notes:
- `CACHE_ROOT_DIR` est résolu au démarrage (ENV, défaut `/mnt/cache`) puis imposé à tous les services (`FilesystemService`, scripts STEP*). STEP7 ne tentera jamais de copier en dehors de ce périmètre.
- Si `OUTPUT_DIR` n'est pas inscriptible (montage lecture seule, permissions), la destination est automatiquement remplacée par:
  1) `FALLBACK_OUTPUT_DIR` (si définie et inscriptible)
  2) `_finalized_output/` dans la racine du dépôt
  Cette sélection est réalisée par une sonde d'écriture/suppression plus fiable que `os.access()`.

#### Modes de finalisation et options
```python
# Mode de finalisation (strict|lenient|videos)
FINALIZE_MODE = os.environ.get("FINALIZE_MODE", "lenient").lower()

# Restauration optionnelle des analyses archivées dans la sortie
# Si activé, recopie les artefacts depuis ARCHIVES_DIR vers OUTPUT_DIR après la copie du projet
RESTORE_ARCHIVES_TO_OUTPUT in ("1", "true", "True")
```
Description des modes:
- **strict**: exige au moins les artefacts de scènes ET tracking pour une vidéo (CSV scènes + JSON tracking).
- **lenient** (défaut): exige au moins un artefact parmi scènes | tracking | audio pour considérer le projet « prêt ».
- **videos**: la présence d'au moins un fichier vidéo suffit.

#### Critères de Validation
```python
# Fichiers requis pour considérer un projet comme "prêt"
REQUIRED_FILES = {
    "csv": True,           # Fichier .csv (scènes) obligatoire
    "tracking_json": True, # Fichier _tracking.json obligatoire
    "audio_json": False    # Fichier _audio.json optionnel (non requis)
}

# Extensions vidéo supportées
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
```

## Architecture Interne

### Structure du Code

#### Module Principal (`finalize_and_copy.py`)
```python
def main():
    """Point d'entrée principal avec validation de destination et traitement des projets."""
    
def find_projects_to_finalize():
    """Découverte et validation des projets prêts pour finalisation."""
    
def finalize_project(project_dir):
    """Finalisation complète d'un projet individuel."""
```

### Algorithmes et Méthodes

#### Workflow de Finalisation
```python
def finalization_workflow():
    """
    Workflow complet de finalisation.
    
    1. Validation de la destination de stockage
    2. Découverte des projets prêts
    3. Validation de l'intégrité de chaque projet
    4. Copie vers la destination finale
    5. Vérification de l'intégrité après copie
    6. Suppression des fichiers source
    7. Logging des résultats
    """
    
    # Phase 1: Validation de l'environnement
    validate_output_directory()
    
    # Phase 2: Découverte des projets
    projects_to_finalize = find_projects_to_finalize()
    
    # Phase 3: Traitement séquentiel
    for project in projects_to_finalize:
        success = finalize_project(project)
        track_completion_status(project, success)
    
    # Phase 4: Rapport final
    generate_completion_report()
```

#### Validation de projet selon FINALIZE_MODE
```python
def validate_project_readiness(project_dir, mode: str) -> bool:
    """Valide qu'un projet est prêt pour finalisation selon FINALIZE_MODE."""
    for video_file in project_dir.rglob("*.mp4"):
        stem = video_file.stem
        scenes_csv = next(project_dir.rglob(f"{stem}_scenes.csv"), None) or video_file.with_suffix('.csv')
        tracking_json = next(project_dir.rglob(f"{stem}_tracking.json"), None)
        audio_json = next(project_dir.rglob(f"{stem}_audio.json"), None)

        if mode == "strict":
            if scenes_csv and scenes_csv.exists() and tracking_json and tracking_json.exists():
                return True
        elif mode == "videos":
            return True
        else:  # lenient
            if (scenes_csv and scenes_csv.exists()) or (tracking_json and tracking_json.exists()) or (audio_json and audio_json.exists()):
                return True
    return False
```

#### Archivage avant suppression et copie sécurisée
```python
def finalize_project(source_project_dir, destination_dir):
    """
    Archive d'abord les artefacts d'analyse puis copie le projet; protège ARCHIVES_DIR; suppression source en fin.
    
    Workflow:
    1. Archivage des artefacts disponibles (scènes/audio/tracking) via ResultsArchiver
    2. Copie complète du dossier projet vers OUTPUT_DIR
    3. (Optionnel) Restauration des artefacts archivés dans la sortie si RESTORE_ARCHIVES_TO_OUTPUT
    4. Protection: ne jamais supprimer un chemin situé sous ARCHIVES_DIR
    5. Suppression du dossier source (hors ARCHIVES_DIR)
    """
    
    project_name = source_project_dir.name
    output_project_dir = destination_dir / project_name
    
    try:
        # Phase 1: Préparation
        if output_project_dir.exists():
            logging.warning(f"Destination '{output_project_dir}' existe déjà. Écrasement.")
            shutil.rmtree(output_project_dir)
        
        # Phase 2: Copie complète
        shutil.copytree(source_project_dir, output_project_dir)
        logging.info(f"Projet '{project_name}' copié vers '{output_project_dir}'")
        
        # Phase 3: Validation post-copie
        if validate_copied_project(output_project_dir):
            # Phase 3b: Restauration optionnelle depuis ARCHIVES_DIR
            if os.environ.get("RESTORE_ARCHIVES_TO_OUTPUT", "0") in ("1", "true", "True"):
                try:
                    restore_archived_analysis(project_name, output_project_dir)
                except Exception as e:
                    logging.warning(f"Restauration des analyses archivées échouée: {e}")

            # Phase 4: Protection ARCHIVES_DIR puis suppression source
            try:
                source_project_dir.resolve().relative_to(config.ARCHIVES_DIR.resolve())
                logging.error(f"Refus de suppression: '{source_project_dir}' est sous ARCHIVES_DIR")
                return True
            except Exception:
                pass
            shutil.rmtree(source_project_dir)
            logging.info(f"Dossier source '{source_project_dir}' supprimé.")
            return True
        else:
            # Rollback en cas d'échec de validation
            shutil.rmtree(output_project_dir)
            logging.error(f"Validation post-copie échouée pour '{project_name}'")
            return False
            
    except Exception as e:
        logging.error(f"Erreur lors de la copie de '{project_name}': {e}")
        # Tentative de nettoyage en cas d'erreur
        if output_project_dir.exists():
            try:
                shutil.rmtree(output_project_dir)
            except:
                pass
        return False
```

#### Validation Post-Copie
```python
def validate_copied_project(copied_project_dir):
    """
    Valide l'intégrité d'un projet après copie.
    
    Vérifications:
    1. Structure de dossiers correcte
    2. Présence de tous les fichiers requis
    3. Intégrité des fichiers JSON
    4. Tailles de fichiers cohérentes
    """
    
    try:
        docs_dir = copied_project_dir / "docs"
        if not docs_dir.exists():
            logging.error(f"Dossier 'docs' manquant dans {copied_project_dir}")
            return False
        
        # Vérification des fichiers vidéo et métadonnées
        video_files = list(docs_dir.glob("*.mp4")) + list(docs_dir.glob("*.mov"))
        if not video_files:
            logging.error(f"Aucun fichier vidéo trouvé dans {docs_dir}")
            return False
        
        for video_file in video_files:
            # Vérification des fichiers associés
            csv_file = video_file.with_suffix('.csv')
            tracking_file = video_file.with_name(f"{video_file.stem}_tracking.json")
            
            if not csv_file.exists():
                logging.error(f"Fichier CSV manquant: {csv_file}")
                return False
            
            if not tracking_file.exists():
                logging.error(f"Fichier tracking manquant: {tracking_file}")
                return False
            
            # Validation JSON
            if not validate_json_file(tracking_file):
                logging.error(f"Fichier JSON invalide: {tracking_file}")
                return False
        
        logging.info(f"Validation post-copie réussie pour {copied_project_dir}")
        return True
        
    except Exception as e:
        logging.error(f"Erreur lors de la validation de {copied_project_dir}: {e}")
        return False
```

### Gestion des Erreurs et Logging

#### Niveaux de Logging
```python
logging.INFO     # Progression normale et opérations réussies
logging.WARNING  # Écrasement de destinations existantes
logging.ERROR    # Échecs de copie ou validation
logging.CRITICAL # Destination inaccessible, erreurs fatales
```

#### Types d'Erreurs Gérées
- **Destination inaccessible** : Répertoire de destination non accessible ou en lecture seule
- **Espace disque insuffisant** : Vérification avant copie des gros projets
- **Erreurs de permissions** : Problèmes d'accès aux fichiers source ou destination
- **Corruption de données** : Validation d'intégrité des fichiers JSON
- **Interruptions système** : Gestion gracieuse des interruptions pendant la copie

#### Structure des Logs
```
logs/step7/
├── finalize_20240120_143022.log    # Log détaillé de l'opération
├── finalize_20240120_150045.log    # Logs précédents
└── finalize_20240120_162130.log    # Historique complet
```

Exemple de sortie :
```
2024-01-20 14:30:22 - INFO - --- Démarrage du script de Finalisation et Nettoyage ---
2024-01-20 14:30:23 - INFO - Le répertoire de destination est: /mnt/cache
2024-01-20 14:30:24 - INFO - Recherche de projets à finaliser dans: /path/projets_extraits
2024-01-20 14:30:25 - INFO - Projet 'projet_camille_001' est prêt (basé sur 'video1.mp4').
2024-01-20 14:30:26 - INFO - 2 projet(s) à finaliser
2024-01-20 14:30:27 - INFO - Finalisation du projet: projet_camille_001
2024-01-20 14:30:30 - INFO - Projet 'projet_camille_001' copié avec succès vers '/mnt/cache/projet_camille_001'
2024-01-20 14:30:31 - INFO - Dossier source '/path/projets_extraits/projet_camille_001' supprimé avec succès.
2024-01-20 14:30:32 - INFO - Finalisation terminée pour 'projet_camille_001'
2024-01-20 14:30:33 - INFO - --- Finalisation terminée ---
2024-01-20 14:30:34 - INFO - Résumé: 2/2 projet(s) finalisé(s) et déplacé(s) avec succès.
```

### Optimisations de Performance

#### Optimisations I/O
- **Copie par blocs** : Utilisation de `shutil.copytree()` optimisé pour gros volumes
- **Validation parallèle** : Vérification d'intégrité pendant la copie
- **Nettoyage différé** : Suppression source uniquement après validation complète

#### Gestion Mémoire
- **Traitement séquentiel** : Un projet à la fois pour éviter la surcharge mémoire
- **Libération immédiate** : Nettoyage des ressources après chaque projet
- **Validation par chunks** : Lecture des gros fichiers JSON par segments

#### Optimisations Réseau (si destination réseau)
```python
# Configuration pour destinations réseau
NETWORK_COPY_BUFFER_SIZE = 64 * 1024  # 64KB buffer
NETWORK_RETRY_ATTEMPTS = 3
NETWORK_TIMEOUT = 300  # 5 minutes timeout

## Interface et Utilisation

### Paramètres d'Exécution

#### Exécution Automatique via Workflow
```python
# Via WorkflowService
result = WorkflowService.run_step("STEP7")

# Via API REST
curl -X POST http://localhost:5000/run/STEP7
```

#### Exécution Manuelle (Debug)
```bash
# Activation de l'environnement principal
source env/bin/activate

# Exécution depuis le répertoire projets_extraits
cd projets_extraits
python ../workflow_scripts/step7/finalize_and_copy.py

# Avec logging détaillé
cd projets_extraits
python ../workflow_scripts/step7/finalize_and_copy.py 2>&1 | tee finalization.log
```

#### Variables d'Environnement Optionnelles
```bash
# Personnalisation de la destination
export OUTPUT_DIR="/custom/destination/path"

# Personnalisation du répertoire de logs
export LOG_DIR="/custom/logs/path"

# Mode debug pour logging verbeux
export DEBUG=true
```

### Exemples d'Utilisation

#### Test de Finalisation sur Projet Unique
```bash
# Préparation d'un test complet
mkdir -p test_finalization_complete/docs
echo "Test video content" > test_finalization_complete/docs/test.mp4
echo "No,Timecode In,Timecode Out,Frame In,Frame Out" > test_finalization_complete/docs/test.csv
echo '{"metadata":{"video_path":"test.mp4","total_frames":100},"frames":[]}' > test_finalization_complete/docs/test_tracking.json

# Vérification de la structure
ls -la test_finalization_complete/docs/

# Exécution de la finalisation
source env/bin/activate
cd test_finalization_complete
python ../workflow_scripts/step7/finalize_and_copy.py

# Vérification du résultat
ls -la /mnt/cache/test_finalization_complete/docs/
echo "Test completed successfully"
```

#### Intégration dans Séquence Complète
```javascript
// Frontend - Séquence complète avec finalisation
const fullWorkflow = ['STEP1', 'STEP2', 'STEP3', 'STEP4', 'STEP5', 'STEP7'];
await apiService.runCustomSequence(fullWorkflow);

// Monitoring spécifique de l'étape 7
pollingManager.startPolling('step7Status', async () => {
    const status = await apiService.getStepStatus('STEP7');
    if (status.status === 'running') {
        updateFinalizationProgress(status.progress);
    }
}, 1000);
```

#### Vérification Post-Finalisation
```bash
# Vérification de l'intégrité après finalisation
find /mnt/cache -name "*.mp4" -exec echo "Checking {}" \; -exec ls -la {} \;

# Vérification des fichiers JSON
find /mnt/cache -name "*_tracking.json" -exec python -m json.tool {} \; > /dev/null && echo "All JSON files valid"

# Calcul de l'espace utilisé
du -sh /mnt/cache/*
```

### Structure des Fichiers de Sortie

#### Hiérarchie Finale
```
/mnt/cache/                         # Destination de stockage finale
├── projet_camille_001/
│   └── docs/
│       ├── video1.mp4              # Vidéo traitée (25 FPS)
│       ├── video1.csv              # Scènes détectées
│       ├── video1_audio.json       # Analyse audio (optionnel)
│       ├── video1_tracking.json    # Données de tracking
│       ├── video2.mov              # Vidéo traitée (25 FPS)
│       ├── video2.csv              # Scènes détectées
│       ├── video2_audio.json       # Analyse audio (optionnel)
│       └── video2_tracking.json    # Données de tracking
├── projet_camille_002/
│   └── docs/
│       └── [structure similaire]
└── projet_camille_003/
    └── docs/
        └── [structure similaire]
```

#### Métadonnées de Finalisation
```
logs/step7/
├── finalize_20240120_143022.log    # Log détaillé de l'opération
├── finalize_20240120_150045.log    # Logs précédents
└── finalize_20240120_162130.log    # Historique complet
```

#### Validation de l'Intégrité
```bash
# Script de validation post-finalisation
#!/bin/bash
for project in /mnt/cache/*/; do
    project_name=$(basename "$project")
    echo "Validating $project_name..."

    # Vérifier la structure
    if [ ! -d "$project/docs" ]; then
        echo "❌ Missing docs directory in $project_name"
        continue
    fi

    # Vérifier les fichiers vidéo et métadonnées
    video_files=("$project/docs"/*.mp4 "$project/docs"/*.mov)
    if [ ${#video_files[@]} -eq 0 ]; then
        echo "❌ No video files found in $project_name"
        continue
    fi

    for video_file in "${video_files[@]}"; do
        # Vérifier CSV
        csv_file="$video_file".csv
        if [ ! -f "$csv_file" ]; then
            echo "❌ CSV file missing: $csv_file"
            continue
        fi

        # Vérifier tracking JSON
        tracking_file="${video_file%.*}"_tracking.json
        if [ ! -f "$tracking_file" ]; then
            echo "❌ Tracking JSON file missing: $tracking_file"
            continue
        fi
    done

    echo "✅ $project_name: All video files have complete metadata"
done
```

### Métriques de Progression et Monitoring

#### Indicateurs de Progression Console
```python
# Sortie standardisée pour l'interface utilisateur
print(f"{total_projects} projet(s) à finaliser")
print(f"Finalisation en cours pour '{project_name}'...")
print(f"Finalisation terminée pour '{project_name}'")
```

#### Métriques de Performance
```python
# Statistiques de finalisation
logging.info(f"{total_projects} projet(s) à finaliser")
logging.info(f"Projet '{project_name}' copié avec succès vers '{output_project_dir}'")
logging.info(f"Dossier source '{project_dir}' supprimé avec succès.")
logging.info(f"Résumé: {successful_count}/{total_projects} projet(s) finalisé(s) et déplacé(s) avec succès.")

# Temps de traitement
start_time = time.time()
success = finalize_project(project)
processing_time = time.time() - start_time
```

#### Monitoring via Logs Structurés
```python
# Progression détaillée
logging.info(f"--- Démarrage du script de Finalisation et Nettoyage ---")
logging.info(f"Le répertoire de destination est: {OUTPUT_DIR.resolve()}")
logging.info(f"Recherche de projets à finaliser dans: {WORK_DIR}")
logging.info(f"Finalisation du projet: {project_name}")
logging.info(f"--- Finalisation terminée ---")
```

## Dépendances et Prérequis

### Logiciels Externes Requis

#### Système de Fichiers
```bash
# Vérification de l'accès à la destination
ls -la /mnt/cache/
df -h /mnt/cache/

# Permissions d'écriture
touch /mnt/cache/test_write && rm /mnt/cache/test_write && echo "Write access OK"
```

#### Utilitaires Système
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install coreutils  # Pour shutil et opérations de fichiers

# Vérification de l'espace disque
df -h /mnt/cache/
```

### Versions Spécifiques des Bibliothèques

#### Requirements Python (env/)
```txt
# Aucune dépendance externe spécifique
# Utilise uniquement la bibliothèque standard Python 3.8+

# Modules standard utilisés:
# - shutil (copie de fichiers)
# - pathlib (manipulation de chemins)
# - json (validation JSON)
# - logging (journalisation)
# - os (interface système)
```

#### Vérification des Dépendances
```bash
# Test des modules requis
python -c "import shutil, pathlib, json, logging, os; print('All standard modules available')"

# Test des opérations de fichiers
python -c "
import shutil, tempfile, pathlib
with tempfile.TemporaryDirectory() as tmp:
    src = pathlib.Path(tmp) / 'src'
    dst = pathlib.Path(tmp) / 'dst'
    src.mkdir()
    (src / 'test.txt').write_text('test')
    shutil.copytree(src, dst)
    print('File operations test: OK')
"
```

### Configuration Système Recommandée

#### Ressources Minimales
- **RAM** : 2 GB minimum, 4 GB recommandé
- **CPU** : 2 cœurs minimum
- **Espace disque destination** : 2x la taille des projets source (pour sécurité)
- **IOPS** : SSD recommandé pour performances I/O

#### Configuration de la Destination
```bash
# Création de la destination si nécessaire
sudo mkdir -p /mnt/cache
sudo chown $USER:$USER /mnt/cache
chmod 755 /mnt/cache

# Vérification de l'espace disponible
df -h /mnt/cache

# Test de performance I/O
dd if=/dev/zero of=/mnt/cache/test_io bs=1M count=100 && rm /mnt/cache/test_io
```

#### Optimisations Système
```bash
# Optimisation pour gros transferts de fichiers
echo 'vm.dirty_ratio = 5' | sudo tee -a /etc/sysctl.conf
echo 'vm.dirty_background_ratio = 2' | sudo tee -a /etc/sysctl.conf

# Optimisation du cache de fichiers
echo 'vm.vfs_cache_pressure = 50' | sudo tee -a /etc/sysctl.conf
```

## Debugging et Résolution de Problèmes

### Erreurs Courantes et Solutions

#### 1. Erreur : "Destination inaccessible"
```python
# Erreur
PermissionError: [Errno 13] Permission denied: '/mnt/cache'

# Diagnostic
ls -la /mnt/cache/
whoami
groups

# Solutions
sudo chown -R $USER:$USER /mnt/cache/
chmod -R 755 /mnt/cache/

# Ou utiliser une destination alternative
export OUTPUT_DIR="/tmp/workflow_output"
```

#### 2. Erreur : "No space left on device"
```bash
# Erreur
OSError: [Errno 28] No space left on device

# Diagnostic
df -h /mnt/cache/
du -sh projets_extraits/*

# Solutions
# Nettoyer l'espace disque
sudo apt autoremove
sudo apt autoclean

# Ou changer de destination
export OUTPUT_DIR="/path/to/larger/storage"
```

#### 3. Erreur : "Aucun projet à finaliser"
```python
# Message
Aucun projet à finaliser. Fin du script.

# Diagnostic
ls -la projets_extraits/
find projets_extraits/ -name "*.csv" -o -name "*_tracking.json"

# Solutions
# Vérifier que les étapes précédentes ont été exécutées
python -c "
import pathlib
for p in pathlib.Path('projets_extraits').iterdir():
    if p.is_dir():
        videos = list(p.rglob('*.mp4'))
        csvs = list(p.rglob('*.csv'))
        trackings = list(p.rglob('*_tracking.json'))
        print(f'{p.name}: {len(videos)} videos, {len(csvs)} CSV, {len(trackings)} tracking')
"
```

#### 4. Erreur : "Fichier JSON invalide"
```python
# Erreur
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

# Diagnostic
find projets_extraits/ -name "*_tracking.json" -exec python -m json.tool {} \; > /dev/null

# Solutions
# Identifier les fichiers corrompus
for json_file in projets_extraits/*/docs/*_tracking.json; do
    if ! python -m json.tool "$json_file" > /dev/null 2>&1; then
        echo "Corrupted JSON: $json_file"
        # Régénérer le fichier si possible ou exclure du traitement
    fi
done
```

### Logs Spécifiques à Surveiller

#### Logs de Progression
```bash
# Progression de la finalisation
grep "projet(s) à finaliser" logs/step7/finalize_*.log
grep "Finalisation terminée pour" logs/step7/finalize_*.log
grep "Résumé:" logs/step7/finalize_*.log
```

#### Logs d'Erreurs
```bash
# Erreurs de copie
grep "Erreur lors de la finalisation" logs/step7/finalize_*.log
grep "Permission denied" logs/step7/finalize_*.log
grep "No space left" logs/step7/finalize_*.log
```

#### Logs de Validation
```bash
# Validation des projets
grep "est prêt" logs/step7/finalize_*.log
grep "copié avec succès" logs/step7/finalize_*.log
grep "supprimé avec succès" logs/step7/finalize_*.log
```

### Tests de Validation et Vérification

#### Test de Fonctionnement Basique
```bash
# Créer un projet de test complet
mkdir -p test_finalization_complete/docs
echo "Test video content" > test_finalization_complete/docs/test.mp4
echo "No,Timecode In,Timecode Out,Frame In,Frame Out" > test_finalization_complete/docs/test.csv
echo '{"metadata":{"video_path":"test.mp4","total_frames":100},"frames":[]}' > test_finalization_complete/docs/test_tracking.json

# Exécuter la finalisation
source env/bin/activate
cd test_finalization_complete
python ../workflow_scripts/step7/finalize_and_copy.py

# Vérifier le résultat
ls -la /mnt/cache/test_finalization_complete/docs/
echo "Test completed successfully"
```

#### Test de Gestion d'Erreurs
```bash
# Test avec destination en lecture seule
sudo chmod 444 /mnt/cache/
python workflow_scripts/step7/finalize_and_copy.py
# Doit échouer gracieusement

# Restaurer les permissions
sudo chmod 755 /mnt/cache/
```

#### Validation de l'Intégrité Complète
```python
#!/usr/bin/env python3
"""Script de validation pour l'étape 7."""

def validate_step7_output():
    """Valide la finalisation complète."""
    import json
    from pathlib import Path

    output_dir = Path("/mnt/cache")
    if not output_dir.exists():
        print("❌ Répertoire de destination non trouvé")
        return False

    projects = [p for p in output_dir.iterdir() if p.is_dir()]
    if not projects:
        print("❌ Aucun projet finalisé trouvé")
        return False

    for project in projects:
        docs_dir = project / "docs"
        if not docs_dir.exists():
            print(f"❌ Dossier docs manquant pour {project.name}")
            return False

        # Vérifier les fichiers vidéo et métadonnées
        video_files = list(docs_dir.glob("*.mp4")) + list(docs_dir.glob("*.mov"))
        if not video_files:
            print(f"❌ Aucun fichier vidéo dans {project.name}")
            return False

        for video_file in video_files:
            csv_file = video_file.with_suffix('.csv')
            tracking_file = video_file.with_name(f"{video_file.stem}_tracking.json")

            if not csv_file.exists():
                print(f"❌ Fichier CSV manquant: {csv_file}")
                return False

            if not tracking_file.exists():
                print(f"❌ Fichier tracking manquant: {tracking_file}")
                return False

            # Validation JSON
            try:
                with open(tracking_file, 'r') as f:
                    json.load(f)
            except json.JSONDecodeError:
                print(f"❌ JSON invalide: {tracking_file}")
                return False

        print(f"✅ {project.name}: {len(video_files)} vidéos avec métadonnées complètes")

    print(f"✅ Validation réussie: {len(projects)} projets finalisés")
    return True

if __name__ == "__main__":
    validate_step7_output()
```

### Monitoring et Alertes

#### Surveillance de l'Espace Disque
```bash
# Monitoring continu de l'espace disque
while true; do
    usage=$(df -h /mnt/cache | tail -1 | awk '{print $5}' | sed 's/%//')
    available=$(df -h /mnt/cache | tail -1 | awk '{print $4}')
    echo "$(date): Espace utilisé: $usage%, Disponible: $available"

    if [ $usage -gt 90 ]; then
        echo "ALERTE: Espace disque critique ($usage%)"
    fi
    sleep 60
done
```

#### Surveillance des Opérations de Finalisation
```bash
# Monitoring des logs en temps réel
tail -f logs/step7/finalize_*.log | grep -E "(Finalisation|Erreur|Résumé)"

# Calcul du débit de finalisation
start_time=$(date +%s)
# ... après finalisation ...
end_time=$(date +%s)
duration=$((end_time - start_time))
project_count=$(ls -1d /mnt/cache/*/ | wc -l)
throughput=$(echo "scale=2; $project_count / $duration" | bc)
echo "Débit de finalisation: $throughput projets/seconde"
```

#### Métriques de Qualité
```bash
# Analyse de la complétude des projets finalisés
for project in /mnt/cache/*/; do
    project_name=$(basename "$project")
    video_count=$(find "$project" -name "*.mp4" -o -name "*.mov" | wc -l)
    csv_count=$(find "$project" -name "*.csv" | wc -l)
    tracking_count=$(find "$project" -name "*_tracking.json" | wc -l)
    audio_count=$(find "$project" -name "*_audio.json" | wc -l)

    completeness_ratio=$(echo "scale=2; ($csv_count + $tracking_count) / ($video_count * 2)" | bc)
    echo "$project_name: Videos=$video_count, CSV=$csv_count, Tracking=$tracking_count, Audio=$audio_count, Complétude=$completeness_ratio"
done
```
