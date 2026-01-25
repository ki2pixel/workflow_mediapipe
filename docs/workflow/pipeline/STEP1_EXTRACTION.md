# Documentation Technique - Étape 1 : Extraction d'Archives

> **Code-Doc Context** – Part of the 7‑step pipeline; see `../README.md` for the uniform template. Backend hotspots: none directly in STEP1; related security modules are low‑complexity.

---

## Purpose & Pipeline Role

### Objectif
L'Étape 1 constitue le point d'entrée du pipeline de traitement vidéo MediaPipe. Elle est responsable de l'extraction sécurisée et automatisée d'archives contenant des contenus vidéo, en préparant les données pour les étapes suivantes du workflow.

### Rôle dans le Pipeline
- **Position** : Première étape du pipeline (STEP1)
- **Prérequis** : Archives ZIP, RAR, ou TAR contenant des fichiers vidéo
- **Sortie** : Dossiers organisés avec fichiers extraits dans `projets_extraits/`
- **Étape suivante** : Conversion vidéo (STEP2)

### Valeur Ajoutée
- **Automatisation** : Détection et traitement automatique des nouvelles archives
- **Sécurité renforcée** : Protection contre les attaques par path traversal et sanitisation des noms de fichiers
- **Filtrage intelligent** : Traitement sélectif basé sur des mots-clés (par défaut "Camille")
- **Gestion d'état** : Suivi des archives déjà traitées pour éviter les doublons
- **Organisation structurée** : Création d'une hiérarchie de dossiers cohérente pour le pipeline

---

## Inputs & Outputs

### Inputs
- **Archives** : Fichiers ZIP, RAR, TAR/TGZ/TBZ2/TXZ dans le répertoire source
- **Filtres** : Mots-clés optionnels pour filtrer les archives (défaut: "Camille")
- **État** : Fichier de suivi des archives déjà traitées

### Outputs
- **Projets extraits** : Structure `projets_extraits/<nom_projet>/docs/` avec fichiers vidéo
- **Logs** : Journaux détaillés dans `logs/step1/`
- **État mis à jour** : Archives marquées comme traitées

---

## Command & Environment

### Commande WorkflowCommandsConfig
```python
# Exemple de commande (voir WorkflowCommandsConfig pour la commande exacte)
python workflow_scripts/step1/extract_archives.py --source-dir archives_source/ --output-dir projets_extraits/
```

### Environnement Virtuel
- **Environnement utilisé** : `env/` (environnement principal)
- **Activation** : `source env/bin/activate`
- **Partage** : Utilisé également par les étapes 2 et 6

---

## Dependencies

### Bibliothèques Standard Python
```python
import zipfile      # Extraction archives ZIP/ZIPX
import rarfile      # Extraction archives RAR
import tarfile      # Extraction archives TAR/TGZ/TBZ2/TXZ
import pathlib      # Manipulation de chemins
import shutil       # Opérations fichiers/dossiers
import re           # Expressions régulières pour validation
import unicodedata  # Normalisation Unicode
```

### Bibliothèques Externes
```python
import rarfile      # Support RAR (nécessite unrar)
```

### Modules de Sécurité Personnalisés
```python
from utils.filename_security import FilenameSanitizer, validate_extraction_path
```

---

## Configuration

### Variables d'Environnement
- **EXTRACTION_KEYWORD_FILTER** : Mot-clé pour filtrer les archives (défaut: "Camille")
- **EXTRACTION_MAX_DEPTH** : Profondeur maximale d'extraction (défaut: 10)
- **EXTRACTION_ALLOWED_EXTENSIONS** : Extensions de fichiers autorisées

### Paramètres de Sécurité
- **Path Traversal Protection** : Validation systématique des chemins d'extraction
- **Filename Sanitization** : Nettoyage des caractères dangereux dans les noms de fichiers
- **Size Limits** : Limites sur la taille des archives et des fichiers extraits

---

## Known Hotspots

### Complexité Backend
- Aucun hotspot identifié dans les modules STEP1 (complexité faible)
- Modules de sécurité associés sont simples et bien testés

---

## Metrics & Monitoring

### Indicateurs de Performance
- **Débit d'extraction** : Mo/s par archive
- **Taux de succès** : % d'archives extraites avec succès
- **Temps de traitement** : Durée moyenne par archive

### Patterns de Logging
```python
# Logs de progression
logger.info(f"Extraction de {archive_path} - {current}/{total}")

# Logs de sécurité
logger.warning(f"Tentative de path traversal détectée: {dangerous_path}")

# Logs d'erreur
logger.error(f"Échec d'extraction: {error}")
```

---

## Failure & Recovery

### Modes d'Échec Communs
1. **Archive corrompue** : Retry avec extraction partielle
2. **Path traversal** : Blocage et logging de sécurité
3. **Espace disque insuffisant** : Pause et alerte utilisateur
4. **Permissions refusées** : Tentative avec élévation de privilèges

### Procédures de Récupération
```bash
# Réessayer une archive spécifique
python workflow_scripts/step1/extract_archives.py --retry-failed archive_name.zip

# Nettoyer les échecs
python workflow_scripts/step1/extract_archives.py --cleanup-failed

# Validation post-récupération
python scripts/validate_step1_output.py
```

---

## Related Documentation

- **Pipeline Overview** : `../README.md`
- **Security Guidelines** : `../technical/SECURITY.md`
- **Testing Strategy** : `../technical/TESTING_STRATEGY.md`
- **WorkflowState Integration** : `../core/ARCHITECTURE_COMPLETE_FR.md`

---

*Generated with Code-Doc protocol – see `../cloc_stats.json` and `../complexity_report.txt`.*

### Formats d'Entrée et de Sortie

#### Formats d'Archives Supportés
- **ZIP** : `.zip`, `.zipx`
- **RAR** : `.rar`
- **TAR** : `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tar.xz`
- **7-Zip** : `.7z` (détection uniquement, extraction non implémentée)

#### Structure d'Entrée Attendue
```
source_directory/
├── archive_camille_001.zip
├── projet_camille_video.rar
└── camille_documents.tar.gz
```

#### Structure de Sortie Générée
```
projets_extraits/
├── archive_camille_001/
│   └── docs/
│       ├── video1.mp4
│       ├── video2.mov
│       └── document.pdf
└── projet_camille_video/
    └── docs/
        ├── presentation.mp4
        └── notes.txt
```

### Paramètres de Configuration

#### Configuration Principale
```python
# Fichier de suivi des archives traitées
PROCESSED_ARCHIVES_FILE = "logs/step1/processed_archives.txt"

# Répertoire de travail pour les extractions
WORK_DIR = "projets_extraits"

# Suppression automatique après extraction réussie
DELETE_ARCHIVE_AFTER_SUCCESS = True

# Mot-clé de filtrage des archives
KEYWORD = "Camille"
```

#### Réinitialisation Mensuelle du Suivi des Archives
Pour éviter qu'une archive portant le même nom de fichier soit ignorée d'un mois sur l'autre, une réinitialisation automatique mensuelle du fichier `processed_archives.txt` est implémentée.

- **Marqueur de mois** : `processed_archives.last_reset` (fichier texte contenant le mois au format YYYY-MM)
- **Déclenchement** : Au démarrage du script, vérification du mois courant
- **Actions en cas de changement de mois** :
  - Sauvegarde horodatée du fichier existant (si non vide) dans `logs/step1/`
  - Vidage du fichier `processed_archives.txt`
  - Mise à jour du marqueur avec le nouveau mois
- **Tests unitaires** : Couverture pour les cas même mois, changement de mois, et initialisation

#### Paramètres de Sécurité
```python
# Longueur maximale des noms de fichiers
MAX_FILENAME_LENGTH = 255

# Longueur maximale des chemins complets
MAX_PATH_LENGTH = 4096

# Caractères interdits (Windows/Unix)
FORBIDDEN_CHARS = ['<', '>', ':', '"', '|', '?', '*', '\0']

# Noms réservés Windows
RESERVED_NAMES = ['CON', 'PRN', 'AUX', 'NUL', 'COM1-9', 'LPT1-9']
```

## Architecture Interne

### Structure du Code

#### Module Principal (`extract_archives.py`)
```python
def main():
    """Point d'entrée principal avec parsing des arguments."""
    
def find_archives_to_process(source_dir):
    """Découverte des archives à traiter avec filtrage par mot-clé."""
    
def extract_archive(archive_path, destination_base_dir):
    """Orchestrateur principal de l'extraction sécurisée."""
    
def get_project_folder_name(archive_name):
    """Génération du nom de dossier projet à partir du nom d'archive."""
```

#### Fonctions d'Extraction Spécialisées
```python
def secure_extract_zip(zip_path, temp_extract_dir, sanitizer):
    """Extraction sécurisée des archives ZIP avec validation."""
    
def secure_extract_rar(rar_path, temp_extract_dir, sanitizer):
    """Extraction sécurisée des archives RAR avec validation."""
    
def secure_extract_tar(tar_path, temp_extract_dir, sanitizer):
    """Extraction sécurisée des archives TAR avec validation."""
```

#### Module de Sécurité (`utils/filename_security.py`)
```python
class FilenameSanitizer:
    """Sanitiseur complet pour noms de fichiers et chemins."""
    
    def sanitize_archive_member_path(self, member_path):
        """Sanitisation complète d'un chemin d'archive."""
        
    def _sanitize_filename_component(self, filename):
        """Sanitisation d'un composant de nom de fichier."""
```

### Algorithmes et Méthodes

#### Workflow d'Extraction Sécurisée
1. **Validation initiale** : Vérification du format d'archive
2. **Création dossier temporaire** : Extraction dans un environnement isolé
3. **Sanitisation par membre** : Validation et nettoyage de chaque fichier
4. **Validation des chemins** : Protection contre path traversal
5. **Extraction contrôlée** : Copie sécurisée vers destination finale
6. **Nettoyage** : Suppression des fichiers temporaires

#### Algorithme de Sanitisation
```python
def sanitize_path_component(filename):
    # 1. Détection des patterns dangereux (../, ..\, etc.)
    # 2. Suppression des caractères de contrôle et null bytes
    # 3. Remplacement des caractères interdits par '_'
    # 4. Validation des noms réservés Windows
    # 5. Normalisation Unicode (NFC)
    # 6. Troncature si dépassement de longueur
    # 7. Génération de nom de fallback si vide
```

#### Détection de Sécurité
```python
DANGEROUS_PATTERNS = [
    r'\.\.[\\/]',           # Path traversal classique
    r'^[\\/]',              # Chemins absolus
    r'[\x00-\x1f\x7f]',    # Caractères de contrôle
    r'^(CON|PRN|AUX|NUL)',  # Noms réservés Windows
]
```

### Gestion des Erreurs et Logging

#### Niveaux de Logging
```python
logging.INFO    # Opérations normales et progression
logging.WARNING # Problèmes de sécurité détectés
logging.ERROR   # Erreurs d'extraction ou de validation
logging.CRITICAL # Erreurs fatales nécessitant l'arrêt
```

#### Types d'Erreurs Gérées
- **Archives corrompues** : `zipfile.BadZipFile`, `rarfile.BadRarFile`, `tarfile.ReadError`
- **Problèmes de sécurité** : Path traversal, caractères dangereux
- **Erreurs d'E/S** : Permissions, espace disque, fichiers verrouillés
- **Erreurs de validation** : Formats non supportés, noms invalides

#### Structure des Logs
```
logs/step1/extract_archives_20240120_143022.log
```

Exemple de sortie :
```
2024-01-20 14:30:22 - INFO - Extraction ZIP sécurisée de archive_camille_001.zip
2024-01-20 14:30:23 - WARNING - Security issues in ZIP member '../../../etc/passwd': ['Path traversal pattern detected']
2024-01-20 14:30:23 - INFO - Sanitized ZIP member: '../../../etc/passwd' -> 'etc_passwd'
2024-01-20 14:30:24 - INFO - Statistiques de sécurité: 15 fichiers traités, 3 modifiés, 1 problème détecté
```

### Optimisations de Performance

#### Gestion Mémoire
- **Extraction par flux** : Utilisation de `shutil.copyfileobj()` pour éviter le chargement complet en mémoire
- **Dossiers temporaires** : Extraction dans un répertoire temporaire avant déplacement final
- **Nettoyage automatique** : Suppression immédiate des fichiers temporaires

#### Optimisations I/O
- **Validation préalable** : Vérification des formats avant extraction
- **Création de dossiers à la demande** : `mkdir(parents=True, exist_ok=True)`
- **Gestion des permissions** : Préservation des attributs de fichiers quand possible

#### Parallélisation
- **Traitement séquentiel** : Une archive à la fois pour éviter les conflits
- **Extraction par membre** : Traitement individuel de chaque fichier dans l'archive
- **Pas de multiprocessing** : Évite les conflits d'accès aux fichiers

## Interface et Utilisation

### Paramètres d'Exécution

#### Arguments de Ligne de Commande
```bash
python workflow_scripts/step1/extract_archives.py --source-dir /path/to/archives
```

**Paramètres** :
- `--source-dir` (obligatoire) : Répertoire contenant les archives à traiter

#### Variables d'Environnement
```bash
# Optionnel : personnalisation du répertoire de travail
export WORK_DIR="/custom/path/projets_extraits"

# Optionnel : désactivation de la suppression automatique
export DELETE_ARCHIVE_AFTER_SUCCESS=false
```

### Exemples d'Utilisation

#### Exécution Directe
```bash
# Activation de l'environnement
source env/bin/activate

# Exécution avec répertoire source
python workflow_scripts/step1/extract_archives.py --source-dir ~/Downloads/archives

# Avec logging détaillé
python workflow_scripts/step1/extract_archives.py --source-dir ~/Downloads/archives 2>&1 | tee extraction.log
```

#### Appel via API Workflow
```bash
# Via curl
curl -X POST http://localhost:5000/run/STEP1

# Via interface web
# Cliquer sur "Étape 1 : Extraction" dans l'interface
```

#### Intégration dans Séquence
```javascript
// Frontend - Séquence complète
const steps = ['STEP1', 'STEP2', 'STEP3', 'STEP4', 'STEP5', 'STEP6'];
await apiService.runCustomSequence(steps);
```

### Structure des Fichiers de Sortie

#### Hiérarchie Générée
```
projets_extraits/
├── archive_camille_001/           # Nom basé sur l'archive source
│   └── docs/                      # Dossier standard pour cohérence pipeline
│       ├── video_principale.mp4   # Fichiers extraits
│       ├── video_secondaire.mov
│       ├── audio_track.wav
│       └── metadata.json
├── projet_camille_video/
│   └── docs/
│       ├── presentation.mp4
│       ├── slides.pdf
│       └── notes.txt
└── camille_documents/
    └── docs/
        ├── rapport.docx
        ├── images/
        │   ├── photo1.jpg
        │   └── photo2.png
        └── videos/
            └── demo.mp4
```

#### Fichiers de Métadonnées
```
logs/step1/
├── extract_archives_20240120_143022.log  # Log détaillé de l'exécution
└── processed_archives.txt                # Liste des archives déjà traitées
```

Contenu de `processed_archives.txt` :
```
/home/user/Downloads/archive_camille_001.zip
/home/user/Downloads/projet_camille_video.rar
/home/user/Downloads/camille_documents.tar.gz
```

### Métriques de Progression et Monitoring

#### Indicateurs de Progression
```python
# Sortie console pour l'interface utilisateur
print(f"Trouvé {total_to_process} archive(s) à traiter")
print(f"PROCESSING_ARCHIVE: {i + 1}/{total_to_process}: {archive.name}")
print(f"EXTRACTION_COMPLETE: {successful_count}/{total_to_process} réussies")
```

#### Métriques de Sécurité
```python
# Statistiques de sanitisation
stats = sanitizer.get_stats()
{
    'total_processed': 150,      # Fichiers traités
    'modified_count': 23,        # Fichiers modifiés
    'security_issues_found': 8   # Problèmes détectés
}
```

#### Monitoring via Logs
```python
# Progression détaillée dans les logs
logging.info(f"--- Traitement {i + 1}/{total_to_process}: {archive.name} ---")
logging.info(f"Extraction réussie: {project_folder_name}")
logging.info(f"Statistiques de sécurité: {stats['total_processed']} fichiers traités")
```

## Dépendances et Prérequis

### Logiciels Externes Requis

#### Système d'Exploitation
- **Linux** : Ubuntu 20.04+ (recommandé), Debian 10+, CentOS 8+
- **macOS** : 10.15+ avec Homebrew
- **Windows** : 10/11 avec WSL2 (recommandé) ou natif

#### Utilitaires Système
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install unrar-free p7zip-full

# macOS
brew install unrar p7zip

# Windows (via chocolatey)
choco install 7zip unrar
```

### Versions Spécifiques des Bibliothèques

#### Requirements Python (env/)
```txt
# Archive handling
rarfile>=4.0
pathlib2>=2.3.7  # Pour compatibilité Python < 3.4

# Logging et utilitaires
colorlog>=6.7.0  # Logs colorés (optionnel)
```

#### Dépendances Système
```bash
# Vérification des dépendances
python -c "import zipfile, tarfile, rarfile; print('All archive libraries available')"

# Test unrar
unrar --version

# Test 7zip (optionnel)
7z --version
```

### Configuration Système Recommandée

#### Ressources Minimales
- **RAM** : 2 GB minimum, 4 GB recommandé
- **CPU** : 2 cœurs minimum
- **Espace disque** : 5 GB libre minimum (pour extractions temporaires)
- **IOPS** : SSD recommandé pour performances I/O

#### Permissions Système
```bash
# Permissions sur répertoires de travail
chmod 755 projets_extraits/
chmod 755 logs/step1/

# Permissions d'exécution
chmod +x workflow_scripts/step1/extract_archives.py
```

#### Limites Système
```bash
# Augmentation des limites de fichiers ouverts (si nécessaire)
ulimit -n 4096

# Vérification de l'espace disque
df -h projets_extraits/
```

## Debugging et Résolution de Problèmes

### Erreurs Courantes et Solutions

#### 1. Erreur : "Archive corrompue ou invalide"
```python
# Erreur
zipfile.BadZipFile: File is not a zip file

# Diagnostic
file archive.zip  # Vérifier le type réel du fichier
hexdump -C archive.zip | head  # Examiner les premiers octets

# Solutions
- Vérifier l'intégrité du téléchargement
- Tester l'ouverture avec un autre outil (7zip, unrar)
- Vérifier que l'extension correspond au format réel
```

#### 2. Erreur : "Permission denied"
```bash
# Erreur
PermissionError: [Errno 13] Permission denied: '/path/to/file'

# Diagnostic
ls -la /path/to/file
whoami
groups

# Solutions
sudo chown -R $USER:$USER projets_extraits/
chmod -R 755 projets_extraits/
```

#### 3. Erreur : "No space left on device"
```bash
# Erreur
OSError: [Errno 28] No space left on device

# Diagnostic
df -h
du -sh projets_extraits/

# Solutions
# Nettoyer les fichiers temporaires
rm -rf projets_extraits/_temp_*
# Augmenter l'espace disque ou changer de répertoire
```

#### 4. Erreur : "rarfile.RarCannotExec"
```bash
# Erreur
rarfile.RarCannotExec: Cannot find working rar/unrar command

# Diagnostic
which unrar
unrar --version

# Solutions
# Ubuntu/Debian
sudo apt install unrar-free
# ou pour version complète
sudo apt install unrar

## Réinitialisation Mensuelle des Archives Traitées

### Fonctionnement

À compter d'octobre 2025, le fichier `logs/step1/processed_archives.txt` est automatiquement réinitialisé au début de chaque mois civil. Cette fonctionnalité permet de s'assurer que les archives avec des noms similaires (par exemple, des exports mensuels) puissent être traitées à nouveau lors des mois suivants.

### Mécanisme

1. **Marqueur Temporel** :
   - Un fichier `logs/step1/processed_archives.last_reset` stocke le mois de la dernière réinitialisation au format `YYYY-MM`.
   - Exemple : `2025-10` pour octobre 2025.

2. **Processus de Réinitialisation** :
   - Au démarrage du script, le système vérifie si le mois actuel diffère de celui enregistré.
   - En cas de changement de mois :
     1. Un fichier de sauvegarde horodaté est créé (ex: `processed_archives_2025-10_backup_20251003_120000.txt`).
     2. Le fichier `processed_archives.txt` est vidé (truncated).
     3. Le marqueur est mis à jour avec le mois en cours.

### Considérations Techniques

- **Sécurité des Données** : Les sauvegardes conservent un historique des archives traitées.
- **Journaux** : Des entrées de log détaillent chaque opération de réinitialisation.
- **Tests** : Couverture par des tests unitaires dans `tests/unit/test_step1_monthly_reset.py`.

### Désactivation

Pour désactiver cette fonctionnalité, il suffit de supprimer ou renommer le fichier `processed_archives.last_reset`.

### Exemple de Logs

```
INFO: Réinitialisation mensuelle: sauvegarde créée 'processed_archives_2025-10_backup_20251003_120000.txt'.
INFO: Réinitialisation mensuelle: fichier 'processed_archives.txt' vidé.
INFO: Marqueur de réinitialisation mis à jour pour le mois: 2025-10
```

# macOS
brew install unrar

# Configuration manuelle
export UNRAR_TOOL="/usr/bin/unrar"
```

### Logs Spécifiques à Surveiller

#### Logs de Sécurité
```bash
# Recherche de problèmes de sécurité
grep "Security issues" logs/step1/extract_*.log
grep "Path traversal" logs/step1/extract_*.log
grep "Unsafe extraction path" logs/step1/extract_*.log
```

#### Logs d'Erreurs
```bash
# Erreurs d'extraction
grep "ERROR" logs/step1/extract_*.log
grep "Failed to extract" logs/step1/extract_*.log
grep "BadZipFile\|BadRarFile\|ReadError" logs/step1/extract_*.log
```

#### Logs de Performance
```bash
# Statistiques de traitement
grep "Statistiques de sécurité" logs/step1/extract_*.log
grep "fichiers traités" logs/step1/extract_*.log
grep "Résumé:" logs/step1/extract_*.log
```

### Tests de Validation et Vérification

#### Test de Fonctionnement Basique
```bash
# Créer une archive de test
mkdir test_archive
echo "Test content" > test_archive/test_camille.txt
zip test_camille.zip test_archive/test_camille.txt

# Tester l'extraction
python workflow_scripts/step1/extract_archives.py --source-dir .

# Vérifier le résultat
ls -la projets_extraits/test_camille/docs/
```

#### Test de Sécurité
```python
# Script de test de sécurité
import zipfile
import os

# Créer une archive avec path traversal
with zipfile.ZipFile('test_security.zip', 'w') as zf:
    zf.writestr('../../../etc/passwd', 'malicious content')
    zf.writestr('normal_file.txt', 'normal content')

# Tester l'extraction sécurisée
# Le fichier malveillant doit être sanitisé
```

#### Test de Performance
```bash
# Mesurer les performances d'extraction
time python workflow_scripts/step1/extract_archives.py --source-dir large_archives/

# Surveiller l'utilisation des ressources
htop  # ou top
iotop  # pour I/O
```

#### Validation de l'Intégrité
```bash
# Vérifier que tous les fichiers ont été extraits
find projets_extraits/ -name "*.mp4" -o -name "*.mov" -o -name "*.avi" | wc -l

# Comparer avec le contenu des archives originales
unzip -l archive.zip | grep -E "\.(mp4|mov|avi)$" | wc -l
```

#### Script de Validation Automatique
```python
#!/usr/bin/env python3
"""Script de validation pour l'étape 1."""

def validate_step1_output():
    """Valide la sortie de l'étape 1."""
    base_dir = Path("projets_extraits")

    if not base_dir.exists():
        print("❌ Répertoire projets_extraits non trouvé")
        return False

    projects = list(base_dir.iterdir())
    if not projects:
        print("❌ Aucun projet extrait trouvé")
        return False

    for project in projects:
        docs_dir = project / "docs"
        if not docs_dir.exists():
            print(f"❌ Dossier docs manquant pour {project.name}")
            return False

        files = list(docs_dir.rglob("*"))
        if not files:
            print(f"❌ Aucun fichier dans {project.name}/docs")
            return False

    print(f"✅ Validation réussie: {len(projects)} projets extraits")
    return True

if __name__ == "__main__":
    validate_step1_output()
```

### Monitoring et Alertes

#### Surveillance des Ressources
```bash
# Script de monitoring des ressources
#!/bin/bash
while true; do
    echo "$(date): Disk usage: $(df -h projets_extraits/ | tail -1 | awk '{print $5}')"
    echo "$(date): Memory usage: $(free -h | grep Mem | awk '{print $3"/"$2}')"
    sleep 60
done
```

#### Alertes de Sécurité
```bash
# Surveillance des problèmes de sécurité
tail -f logs/step1/extract_*.log | grep -i "security\|traversal\|dangerous" --color=always
```

#### Métriques de Succès
```bash
# Calcul du taux de succès
total_archives=$(ls archives_source/ | wc -l)
successful_extractions=$(ls projets_extraits/ | wc -l)
success_rate=$((successful_extractions * 100 / total_archives))
echo "Taux de succès: ${success_rate}%"
```
