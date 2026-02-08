# Conversion Vidéo

**TL;DR** : Normalise toutes les vidéos à 25 FPS avec accélération GPU NVIDIA. Réduit jusqu'à 70% la taille des fichiers tout en préservant la qualité. Fallback CPU automatique si GPU indisponible.

## Le Problème : Framerates Incohérents

Tu as des vidéos avec des framerates variés (24, 29.97, 30, 60 FPS) qui vont causer des problèmes de synchronisation dans les étapes suivantes du pipeline. La détection de scènes, l'analyse audio et le tracking vidéo ont besoin d'une base temporelle cohérente pour fonctionner correctement.

## Notre Solution : Standardisation GPU Optimisée

Nous convertissons toutes les vidéos à exactement 25 FPS en utilisant l'accélération matérielle NVIDIA. Le processus est intelligent : seules les vidéos qui ne sont pas déjà à 25 FPS sont converties, et l'audio est préservé autant que possible.

### ❌ Conversion brute (anti-pattern)
```bash
# Approche inefficace - tout convertir
ffmpeg -i video.mp4 -r 25 output.mp4  # Perte qualité inutile !fmpeg -i *.mov -r 25 *.mp4  # Blocage I/O, pas de parallélisme
# Résultat : temps perdu, qualité dégradée
```

### ✅ Conversion intelligente (pattern recommandé)
```python
# Approche optimisée - conversion sélective
def convert_video_intelligently(video_path):
    current_fps = get_fps(video_path)
    if abs(current_fps - 25.0) <= 0.1:
        return  # Déjà à 25 FPS, pas de conversion
    
    # GPU prioritaire, fallback CPU
    use_gpu = check_gpu_available()
    convert_with_optimal_settings(video_path, use_gpu)
```

### Flux de Conversion Intelligent

1. **Découverte** : Scan de `projets_extraits/*/docs/` pour les vidéos
2. **Analyse** : Extraction du framerate actuel via FFprobe
3. **Filtrage** : Conversion uniquement si |fps_actuel - 25.0| > 0.1
4. **GPU prioritaire** : Utilisation de `h264_nvenc` si disponible
5. **Audio intelligent** : Copie directe, puis ré-encodage AAC si nécessaire
6. **Remplacement atomique** : Fichier temporaire puis déplacement final

## Utilisation Rapide

### Lancement Automatique

```bash
# Via l'interface web
# Clique sur "Étape 2 : Conversion" dans l'interface

# Via API
curl -X POST http://localhost:5000/run/STEP2

# Dans une séquence complète
const steps = ['STEP1', 'STEP2', 'STEP3', 'STEP4', 'STEP5', 'STEP6'];
await apiService.runCustomSequence(steps);
```

### Exécution Manuelle (Debug)

```bash
source env/bin/activate
cd projets_extraits
python ../workflow_scripts/step2/convert_videos.py
```

### Résultat Attendu

```
# Avant conversion
video_29fps.mov    # 29.97 FPS
video_24fps.mp4    # 24.00 FPS  
video_25fps.avi    # 25.00 FPS (pas de conversion)

# Après conversion
video_29fps.mov    # 25.00 FPS converti
video_24fps.mp4    # 25.00 FPS converti
video_25fps.avi    # 25.00 FPS (inchangé)
```

## Configuration Essentielle

### Variables d'Environnement

```bash
# Framerate cible (défaut: 25)
STEP2_FPS_TARGET=25

# Forcer GPU (true/false)
STEP2_USE_GPU=true

# Qualité vidéo (défaut: 28)
STEP2_QUALITY_CRF=28

# Bitrate audio (défaut: 192k)
STEP2_AUDIO_BITRATE=192000

# Conversions parallèles maximum
STEP2_MAX_CONCURRENT=1
```

### Paramètres d'Encodage

**GPU (NVIDIA NVENC)** :
```bash
-c:v h264_nvenc -preset p5 -tune hq -cq 28 -pix_fmt yuv420p
```

**CPU (Fallback libx264)** :
```bash
-c:v libx264 -preset medium -crf 28 -pix_fmt yuv420p
```

**Audio** :
```bash
# Copie directe (priorité)
-c:a copy

# Fallback ré-encodage
-c:a aac -b:a 192k
```

## Formats Supportés

### Vidéos en Entrée

```python
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv')
```

### Spécifications de Sortie

- **Framerate** : 25.0 FPS exactement
- **Codec vidéo** : H.264 (GPU: h264_nvenc, CPU: libx264)
- **Qualité** : CRF/CQ 28 (équivalent visuel)
- **Format pixel** : yuv420p (compatibilité maximale)
- **Audio** : AAC 192k ou copie directe

## Trade-offs par Mode de Conversion

| Mode | Ressources | Risques | Quand l'utiliser |
|------|------------|---------|-----------------|
| **GPU NVENC** | VRAM 2-4GB, rapide | Conflits si multi-workers | Production, vidéos longues |
| **CPU libx264** | 4+ cœurs CPU, lent | Timeout sur vidéos longues | Laptop, GPU indisponible |
| **Hybrid** | GPU + CPU fallback | Complexité configuration | Environnements mixtes |
| **Skip** | Minimal, aucun risque | Framerates incohérentes | Tests rapides, démos |

## Analogie : Studio de Post-Production

Pense à la conversion comme un **studio de post-production**. Le **GPU NVENC** est le monteur expert qui travaille rapidement sur les projets standards. Le **CPU libx264** est l'assistant qui gère les projets spéciaux quand le monteur est occupé. Le **mode intelligent** est le producteur qui décide quel monteur utiliser selon le projet et les ressources disponibles.

### Optimisations FFmpeg

```python
# Paramètres GPU optimisés
GPU_PARAMS = [
    '-preset', 'p5',      # Rapide avec haute qualité
    '-tune', 'hq',        # Optimisation qualité
    '-cq', '28'           # Qualité constante
]

# Gestion audio intelligente
AUDIO_COPY = ['-c:a', 'copy']           # Rapide
AUDIO_REENCODE = ['-c:a', 'aac', '-b:a', '192k']  # Fallback
```

### Gestion Mémoire

- **Fichiers temporaires** : `video.temp_conversion.mov`
- **Remplacement atomique** : `shutil.move()` pour sécurité
- **Nettoyage automatique** : Suppression en cas d'erreur

## Monitoring et Logs

### Structure des Logs

```
logs/step2/
└── convert_videos_20240120_143022.log
```

### Exemple de Logs

```
2024-01-20 14:30:22 - INFO - Recherche de vidéos (.mp4, .mov, .avi, .mkv, .webm, .flv, .wmv)
2024-01-20 14:30:23 - INFO - Conversion requise pour video1.mov (FPS actuel: 29.97)
2024-01-20 14:30:24 - GPU-Worker - INFO - Conversion (GPU) démarrée pour video1.mov
2024-01-20 14:30:45 - GPU-Worker - INFO - Succès (GPU): video1.mov converti et mis à jour
2024-01-20 14:30:45 - INFO - --- Traitement de la vidéo (1/3): video1.mov ---
```

### Métriques Clés

```python
# Progression standardisée
print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
print(f"--- Traitement de la vidéo ({current}/{total}): {video_name} ---")

# Statistiques finales
logging.info(f"Résumé: {successful}/{total} conversion(s) réussie(s)")
```

## Dépendances et Prérequis

### FFmpeg (Obligatoire)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg

# Vérification
ffmpeg -version && ffprobe -version
```

### Support GPU NVIDIA (Recommandé)

```bash
# Vérification du support
nvidia-smi
ffmpeg -encoders | grep nvenc

# Installation drivers (Ubuntu)
sudo apt install nvidia-driver-470
sudo apt install nvidia-cuda-toolkit

# Test GPU
ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=1 -c:v h264_nvenc test_gpu.mp4
```

### Configuration Système

**Ressources minimales** :
- RAM : 4 GB minimum, 8 GB recommandé
- CPU : 4 cœurs minimum (fallback CPU)
- GPU : NVIDIA GTX 1060+ (optionnel)
- Disque : 2x taille vidéos (temporaires)

**Optimisations** :
```bash
# Limite fichiers ouverts
ulimit -n 4096

# Variables CUDA
export CUDA_VISIBLE_DEVICES=0
export NVIDIA_VISIBLE_DEVICES=0
```

## Résolution de Problèmes

### FFmpeg Non Disponible

```bash
# Diagnostic
which ffmpeg
which ffprobe

# Solution
sudo apt install ffmpeg  # Ubuntu
brew install ffmpeg       # macOS
```

### Encodeur NVENC Non Disponible

```bash
# Diagnostic
ffmpeg -encoders | grep nvenc
nvidia-smi

# Solution
sudo apt install nvidia-driver-470
# Fallback CPU automatique sinon
```

### Espace Disque Insuffisant

```bash
# Diagnostic
df -h
du -sh projets_extraits/

# Solution
find projets_extraits/ -name "*.temp_conversion.*" -delete
```

### Permissions Refusées

```bash
# Diagnostic
ls -la projets_extraits/
whoami

# Solution
sudo chown -R $USER:$USER projets_extraits/
chmod -R 755 projets_extraits/
```

## Tests et Validation

### Test de Fonctionnement

```bash
# Créer vidéo test (30 FPS)
ffmpeg -f lavfi -i testsrc=duration=5:size=640x480:rate=30 -c:v libx264 test_30fps.mp4

# Placer dans structure
mkdir -p test_project/docs
mv test_30fps.mp4 test_project/docs/

# Exécuter conversion
cd test_project
python ../workflow_scripts/step2/convert_videos.py

# Vérifier résultat
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 docs/test_30fps.mp4
# Doit retourner: 25/1
```

### Validation Automatique

```python
def validate_step2_output():
    """Vérifie que toutes les vidéos sont à 25 FPS."""
    import subprocess
    from pathlib import Path
    
    base_dir = Path("projets_extraits")
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']
    
    for video_file in base_dir.rglob("*"):
        if video_file.suffix.lower() in video_extensions:
            # Vérifier framerate
            cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                   '-show_entries', 'stream=r_frame_rate', '-of',
                   'default=noprint_wrappers=1:nokey=1', str(video_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            framerate_str = result.stdout.strip()
            if '/' in framerate_str:
                num, den = map(int, framerate_str.split('/'))
                fps = num / den if den != 0 else 0
            else:
                fps = float(framerate_str)
            
            if abs(fps - 25.0) > 0.1:
                print(f"❌ {video_file}: FPS incorrect ({fps:.2f})")
                return False
    
    print("✅ Validation réussie: toutes les vidéos sont à 25 FPS")
    return True
```

### Test Performance GPU vs CPU

```bash
# Test GPU
time python workflow_scripts/step2/convert_videos.py

# Test CPU (désactiver GPU)
CUDA_VISIBLE_DEVICES="" time python workflow_scripts/step2/convert_videos.py
```

## Monitoring et Alertes

### Surveillance GPU

```bash
# Monitoring continu
watch -n 1 nvidia-smi

# Log utilisation GPU
while true; do
    echo "$(date): $(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits)"
    sleep 5
done > gpu_usage.log
```

### Surveillance Espace Disque

```bash
# Alertes espace disque
while true; do
    usage=$(df -h projets_extraits/ | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ $usage -gt 90 ]; then
        echo "ALERTE: Espace disque critique ($usage%)"
    fi
    sleep 30
done
```

### Métriques de Performance

```bash
# Calcul débit conversion
start_time=$(date +%s)
python workflow_scripts/step2/convert_videos.py
end_time=$(date +%s)
duration=$((end_time - start_time))

video_count=$(find projets_extraits/ -name "*.mp4" -o -name "*.mov" -o -name "*.avi" | wc -l)
throughput=$(echo "scale=2; $video_count / $duration" | bc)
echo "Débit de conversion: $throughput vidéos/seconde"
```

## Intégration Pipeline

### Entrée pour STEP3

L'étape 2 prépare des vidéos standardisées pour la détection de scènes :
- Framerate uniforme : 25.0 FPS
- Codec optimisé : H.264 haute qualité
- Taille réduite : jusqu'à 70% d'économie
- Audio préservé : AAC 192k ou copie directe

### WorkflowState Integration

```python
# Intégration avec l'état centralisé
ws = get_workflow_state()
ws.update_step_status("STEP2", "running")
ws.set_step_field("STEP2", "current_video", "video1.mov")
ws.update_step_progress("STEP2", current=1, total=5)
```

## Pièges Courants et Solutions

### Piège #1 : Conversions inutiles
**Solution** : Détection intelligente du framerate avec tolérance de 0.1 FPS.

### Piège #2 : Conflits GPU VRAM
**Solution** : Un seul worker GPU séquentiel pour éviter les conflits.

### Piège #3 : Perte qualité audio
**Solution** : Copie directe prioritaire, ré-encodage AAC seulement si nécessaire.

### Piège #4 : Corruption fichiers
**Solution** : Remplacement atomique avec fichiers temporaires et nettoyage automatique.

L'étape 2 transforme tes vidéos hétérogènes en un ensemble cohérent et optimisé, prêt pour l'analyse automatisée des scènes. La standardisation temporelle garantit que toutes les étapes suivantes travailleront avec des données parfaitement synchronisées.

---

## Golden Rule

**Standardiser 25 FPS avant tout traitement ; sinon tu crées des désynchronisations temporelles dans tout le pipeline.**
