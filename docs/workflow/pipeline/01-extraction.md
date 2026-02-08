# Extraction d'Archives

**TL;DR** : Décompresse automatiquement les archives ZIP/RAR/TAR dans `projets_extraits/` avec sécurité renforcée contre les path traversal. Filtrage par mot-clé "Camille" par défaut.

## Le Problème : Archives Non Sécurisées

Tu reçois des archives ZIP/RAR contenant des vidéos, mais l'extraction manuelle est fastidieuse et dangereuse. Une archive malveillante pourrait essayer d'écrire en dehors du répertoire cible (path traversal) ou utiliser des noms de fichiers problématiques.

## Notre Solution : Extraction Sécurisée et Automatisée

Nous extrayons les archives dans un environnement isolé avec validation systématique de chaque fichier. Chaque nom de fichier est nettoyé, chaque chemin est validé, et tout est journalisé pour la traçabilité.

### ❌ Extraction manuelle (anti-pattern)
```bash
# Approche dangereuse - pas de validation
unzip archive.zip -d /tmp/  # Path traversal possible !
cp -r * projets_extraits/  # Noms dangereux copiés
# Résultat : système compromis
```

### ✅ Extraction sécurisée (pattern recommandé)
```python
# Approche sûre - validation systématique
def extract_archive_securely(archive_path, target_dir):
    # 1. Extraction temporaire isolée
    # 2. Validation path traversal
    # 3. Sanitisation noms de fichiers
    # 4. Déplacement atomique final
    # 5. Nettoyage automatique
```

### Flux d'Extraction Sécurisé

1. **Découverte** : Scan du répertoire source pour les archives
2. **Filtrage** : Ne traite que les archives contenant le mot-clé (défaut: "Camille")
3. **Extraction temporaire** : Dans un dossier isolé
4. **Validation** : Vérification path traversal et noms dangereux
5. **Sanitisation** : Nettoyage des caractères problématiques
6. **Déplacement final** : Vers `projets_extraits/<projet>/docs/`
7. **Nettoyage** : Suppression des fichiers temporaires

## Utilisation Rapide

### Commande de Base

```bash
# Via l'interface web
# Clique sur "Étape 1 : Extraction" dans l'interface

# Via API
curl -X POST http://localhost:5000/run/STEP1

# En ligne de commande (développement)
source env/bin/activate
python workflow_scripts/step1/extract_archives.py --source-dir ~/Downloads/archives
```

### Structure de Sortie

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

## Configuration Essentielle

### Variables d'Environnement

```bash
# Filtrage des archives (défaut: "Camille")
EXTRACTION_KEYWORD_FILTER=Camille

# Limite de profondeur d'extraction
EXTRACTION_MAX_DEPTH=10

# Extensions autorisées
EXTRACTION_ALLOWED_EXTENSIONS=mp4,mov,avi,mkv,wmv,flv,webm

# Suppression automatique des archives après succès
DELETE_ARCHIVE_AFTER_SUCCESS=true
```

### Paramètres de Sécurité

```python
# Longueurs maximales
MAX_FILENAME_LENGTH = 255
MAX_PATH_LENGTH = 4096

# Caractères interdits
FORBIDDEN_CHARS = ['<', '>', ':', '"', '|', '?', '*', '\0']

# Noms réservés Windows
RESERVED_NAMES = ['CON', 'PRN', 'AUX', 'NUL', 'COM1-9', 'LPT1-9']
```

## Formats Supportés

### Archives Acceptées
- **ZIP** : `.zip`, `.zipx`
- **RAR** : `.rar`
- **TAR** : `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tar.xz`
- **7-Zip** : `.7z` (détection uniquement)

### Fichiers Extraits
- Vidéos : `.mp4`, `.mov`, `.avi`, `.mkv`, `.wmv`, `.flv`, `.webm`
- Audio : `.wav`, `.mp3`, `.aac`, `.m4a`
- Documents : `.pdf`, `.txt`, `.docx`, `.jpg`, `.png`

## Sécurité Renforcée

### Protection Path Traversal

```python
# Patterns dangereux détectés
DANGEROUS_PATTERNS = [
    r'\.\.[\\/]',           # ../ ou ..\
    r'^[\\/]',              # Chemins absolus
    r'[\x00-\x1f\x7f]',    # Caractères de contrôle
    r'^(CON|PRN|AUX|NUL)',  # Noms réservés Windows
]
```

### Sanitisation des Noms

```python
def sanitize_filename_component(filename):
    # 1. Détection patterns dangereux
    # 2. Suppression caractères de contrôle
    # 3. Remplacement caractères interdits par '_'
    # 4. Validation noms réservés Windows
    # 5. Normalisation Unicode (NFC)
    # 6. Troncature si trop long
    # 7. Fallback si vide
```

### Exemple de Sanitisation

```
Avant: "../../../etc/passwd"
Après: "etc_passwd"

Avant: "video:dangerous*.mp4"
Après: "video_dangerous_.mp4"
```

## Monitoring et Logs

### Structure des Logs

```
logs/step1/
├── extract_archives_20240120_143022.log
└── processed_archives.txt
```

### Exemple de Logs

```
2024-01-20 14:30:22 - INFO - Extraction ZIP sécurisée de archive_camille_001.zip
2024-01-20 14:30:23 - WARNING - Security issues in ZIP member '../../../etc/passwd': ['Path traversal pattern detected']
2024-01-20 14:30:23 - INFO - Sanitized ZIP member: '../../../etc/passwd' -> 'etc_passwd'
2024-01-20 14:30:24 - INFO - Statistiques de sécurité: 15 fichiers traités, 3 modifiés, 1 problème détecté
```

### Métriques Clés

```python
stats = {
    'total_processed': 150,      # Fichiers traités
    'modified_count': 23,        # Fichiers modifiés
    'security_issues_found': 8   # Problèmes détectés
}
```

## Réinitialisation Mensuelle

### Fonctionnement

Le fichier `processed_archives.txt` est automatiquement réinitialisé chaque mois pour permettre le traitement d'archives avec des noms similaires (exports mensuels par exemple).

### Mécanisme

1. **Marqueur temporel** : `processed_archives.last_reset` (format YYYY-MM)
2. **Détection** : Vérification au démarrage si le mois a changé
3. **Sauvegarde** : Copie horodatée avant vidage
4. **Réinitialisation** : Vidage du fichier et mise à jour du marqueur

### Désactivation

Pour désactiver cette fonctionnalité, supprime ou renomme le fichier `processed_archives.last_reset`.

## Résolution de Problèmes

### Archive Corrompue

```bash
# Diagnostic
file archive.zip
hexdump -C archive.zip | head

# Solutions
- Vérifier l'intégrité du téléchargement
- Tester avec un autre outil (7zip, unrar)
- Vérifier que l'extension correspond au format réel
```

### Permission Refusée

```bash
# Diagnostic
ls -la /path/to/file
whoami

# Solution
sudo chown -R $USER:$USER projets_extraits/
chmod -R 755 projets_extraits/
```

### Espace Disque Insuffisant

```bash
# Diagnostic
df -h
du -sh projets_extraits/

# Solution
rm -rf projets_extraits/_temp_*
```

### RAR Non Disponible

```bash
# Diagnostic
which unrar
unrar --version

# Installation
# Ubuntu/Debian
sudo apt install unrar-free
# macOS
brew install unrar
```

## Tests et Validation

### Test de Fonctionnement

```bash
# Créer une archive de test
mkdir test_archive
echo "Test content" > test_archive/test_camille.txt
zip test_camille.zip test_archive/test_camille.txt

# Tester l'extraction
python workflow_scripts/step1/extract_archives.py --source-dir .

# Vérifier
ls -la projets_extraits/test_camille/docs/
```

### Test de Sécurité

```python
# Créer une archive malveillante pour tester
import zipfile
with zipfile.ZipFile('test_security.zip', 'w') as zf:
    zf.writestr('../../../etc/passwd', 'malicious content')
    zf.writestr('normal_file.txt', 'normal content')

# Le fichier malveillant doit être sanitisé
```

### Validation Automatique

```python
def validate_step1_output():
    base_dir = Path("projets_extraits")
    
    if not base_dir.exists():
        print("❌ Répertoire projets_extraits non trouvé")
        return False
    
    projects = list(base_dir.iterdir())
    for project in projects:
        docs_dir = project / "docs"
        if not docs_dir.exists():
            print(f"❌ Dossier docs manquant pour {project.name}")
            return False
    
    print(f"✅ Validation réussie: {len(projects)} projets extraits")
    return True
```

## Trade-offs par Format d'Archive

| Format | Avantages | Risques | Quand l'utiliser |
|--------|-----------|---------|-----------------|
| **ZIP** | Universel, compression bonne | Path traversal facile | Archives clients standard |
| **RAR** | Compression supérieure | Propriétaire, unrar requis | Archives professionnelles |
| **TAR** | Simple, Unix natif | Pas de compression | Backups, transferts serveurs |
| **7-Zip** | Meilleure compression | Moins supporté | Archives techniques optimisées |

## Analogie : Sas de Décontamination

Pense à l'extraction comme un **sas de décontamination**. Les archives entrent dans une zone stérile (`_temp_`), chaque fichier est scanné pour les menaces (path traversal, noms dangereux), nettoyé si nécessaire, puis seulement transféré dans la zone propre (`projets_extraits/`). Rien ne sort du sas sans avoir passé les contrôles de sécurité.

## Intégration Pipeline

### Entrée pour STEP2

L'étape 1 prépare les fichiers pour l'étape 2 (conversion vidéo) :
- Les vidéos sont dans `projets_extraits/<projet>/docs/`
- La structure est cohérente pour le reste du pipeline
- Les métadonnées sont journalisées pour traçabilité

### Monitoring via WorkflowState

```python
# Intégration avec l'état centralisé
ws = get_workflow_state()
ws.update_step_status("STEP1", "running")
ws.set_step_field("STEP1", "current_archive", "archive_camille_001.zip")
ws.update_step_progress("STEP1", current=1, total=5)
```

## Pièges Courants et Solutions

### Piège #1 : Noms de fichiers problématiques
**Solution** : Sanitisation automatique avec validation Unicode et remplacement des caractères dangereux.

### Piège #2 : Path traversal
**Solution** : Validation systématique des chemins et extraction dans environnement temporaire isolé.

### Piège #3 : Archives corrompues
**Solution** : Gestion d'erreurs robuste avec retry et logging détaillé.

### Piège #4 : Espace disque insuffisant
**Solution** : Vérification préalable et nettoyage automatique des temporaires.

L'étape 1 transforme une opération manuelle risquée en un processus automatisé, sécurisé et traçable. Tes vidéos sont prêtes pour la conversion en toute sécurité.

---

## Golden Rule

**Toujours filtrer, sanitiser, archiver avant conversion ; sinon tu exposes ton système à des attaques path traversal.**
