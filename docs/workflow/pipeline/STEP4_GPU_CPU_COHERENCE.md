# STEP4 - Cohérence GPU vs CPU en Diarisation Audio

## Problème Identifié (2025-12-15)

### Symptôme
Une **divergence massive** a été observée entre les sorties GPU et CPU pour la même vidéo :

| Mode | Frames avec parole | % Parole | Première détection | 
|------|-------------------|----------|-------------------|
| GPU (AMP=1) | 262 / 4374 | 5.99% | Frame 4061 (162.4s) |
| CPU (FP32) | 3762 / 4374 | 86.0% | Frame 12 (0.44s) |

**Décalage : +162 secondes et 3500 frames manquantes sur GPU**

### Cause Racine

**AMP (Automatic Mixed Precision, FP16) sur GPU change drastiquement les scores de diarisation pyannote :**

- Le profil `gpu_optimized` active `AUDIO_ENABLE_AMP=1` pour réduire l'usage VRAM
- AMP utilise FP16 (précision réduite) au lieu de FP32
- Les scores de confiance de la diarisation sont **sensibles à la précision numérique**
- Résultat : **faux négatifs massifs** (segments de parole non détectés)

### Impact Fonctionnel

- **STEP5 (Tracking)** utilise `is_speech_present` pour optimiser la détection de visages parlants
- Une sous-détection de parole dégrade la qualité du tracking final
- Le comportement GPU/CPU devient **non déterministe** et **non reproductible**

## Solution Implémentée (v4.1.2+)

### 1. Profil `gpu_fp32` (Recommandé en Production)

Configuration optimale pour la cohérence et les performances :

```bash
# Dans .env ou configuration du service
AUDIO_PROFILE=gpu_fp32
PYANNOTE_BATCH_SIZE=auto  # Ajustement automatique
PYANNOTE_DEVICE=cuda     # Utilisation du GPU si disponible
```

**Améliorations clés :**
- **Précision FP32 complète** : Désactive AMP pour éviter les faux négatifs
- **Gestion automatique de la mémoire** : Ajustement dynamique du `batch_size`
- **Instrumentation avancée** : Métriques de performance détaillées
- **Cohérence garantie** entre les exécutions CPU/GPU

**Logs de diagnostic :**
```
[INFO] [PROFILING] AudioService: Profil gpu_fp32 activé (FP32, no AMP)
[INFO] [PROFILING] Mémoire GPU disponible: 12.4 Go, batch_size=8
[INFO] [PROFILING] Pyannote inference: 38.2ms/segment (moyenne)
[WARNING] [PROFILING] Taux de détection bas (15%), vérifier le modèle
```

### 2. Profils et Configuration

#### Profils Disponibles

| Profil | Device | AMP | Batch Size | Usage Recommandé |
|--------|--------|-----|------------|------------------|
| `gpu_fp32` | CUDA | ❌ | Auto | **Production** - Meilleure cohérence |
| `gpu_optimized` | CUDA | ✅ | 16 | Performance maximale (risque de faux négatifs) |
| `cpu` | CPU | ❌ | 1 | Débogage - Cohérence de référence |

#### Variables d'Environnement

```bash
# Configuration de base
AUDIO_PROFILE=gpu_fp32  # Profil à utiliser
AUDIO_DEVICE=auto       # 'auto', 'cuda', 'cpu'

# Optimisation des performances
PYANNOTE_BATCH_SIZE=auto  # 'auto' ou nombre fixe
PYANNOTE_NUM_WORKERS=4    # Workers pour le prétraitement

# Logging et monitoring
AUDIO_LOG_LEVEL=INFO      # DEBUG, INFO, WARNING, ERROR
ENABLE_AUDIO_PROFILING=1  # Active les métriques détaillées

# Seuils de détection
SPEECH_DETECTION_THRESHOLD=0.5  # Seuil de confiance (0-1)
MIN_SPEECH_DURATION_MS=300      # Durée minimale des segments

#### 3. Monitoring et Détection des Problèmes

#### Vérification de Cohérence

1. **Au Démarrage** :
   ```
   [INFO] Vérification de la cohérence GPU/CPU...
   [INFO] Test de cohérence réussi (décalage max: 2ms)
   [WARNING] Détection de divergence GPU/CPU, passage en mode FP32
   ```

2. **Pendant l'Exécution** :
   - Surveillance continue du taux de détection
   - Détection des baisses de performances
   - Ajustement dynamique des paramètres

#### Alertes Automatiques

| Condition | Action | Exemple de Log |
|-----------|--------|----------------|
| Taux de détection < 5% | Warning + fallback CPU | `[WARNING] Taux de détection faible (3%), activation du fallback CPU` |
| Délai d'inférence > 100ms | Ajustement batch_size | `[INFO] Optimisation: réduction batch_size de 16→8 (trop lent)` |
| Erreur CUDA | Fallback CPU automatique | `[ERROR] Erreur CUDA, passage en mode CPU: out of memory` |

#### Fichiers de Diagnostic

- `logs/audio_metrics_*.csv` : Métriques détaillées par session
- `debug/audio_inconsistencies.log` : Incohérences détectées
- `profiling/audio_perf_*.json` : Données de performance brutes

#### Commande de Vérification

```bash
# Vérifier la configuration actuelle
python -c "from services.audio_service import AudioService; print(AudioService().get_config())"

# Lancer un test de cohérence
pytest tests/audio/test_gpu_cpu_consistency.py -v
```
  - Speech frames: 3872 (86.0%)
  - Avg inference: 42.1ms/segment
  - GPU mem: 8.2/12.0 GB (68%)
  - Batch size: 8 (auto-tuned)
  - First detection: frame 12 (0.4s)
  - Warnings: None
```
| `gpu_optimized` | CUDA | ✅ | 1 | VRAM très faible (<4GB) - **Qualité réduite** |
| `gpu_no_amp` | CUDA | ❌ | 1 | Alias de `gpu_fp32` |
| `cpu_only` | CPU | ❌ | - | Debug / Baseline |

### 3. Harmonisation Fallback CPU

Le fallback CPU (en cas d'OOM GPU) utilise maintenant :
- Mêmes paramètres que le mode GPU principal (`batch_size`)
- **Forçage FP32** (pas d'AMP)
- Logs explicites du nombre de segments détectés

### 4. Instrumentation Diagnostique

Logs ajoutés pour faciliter le debug :

```
INFO - Diarisation: 42 segment(s) détecté(s)
INFO - Timeline audio: 3762/4374 frames avec parole (86.0%)
```

## Migration / Configuration

### Dans `.env`

**Avant (par défaut, problématique) :**
```bash
AUDIO_PROFILE=gpu_optimized  # ⚠️ AMP=1, faux négatifs
```

**Après (recommandé) :**
```bash
AUDIO_PROFILE=gpu_fp32  # ✅ FP32, cohérence CPU
```

### Validation

Après migration, relancer STEP4 et vérifier les logs :

```
INFO - AUDIO_PROFILE=gpu_fp32 appliqué (AMP=0, batch_size=1, FP32 pur - cohérence CPU)
INFO - Diarisation: X segment(s) détecté(s)
INFO - Timeline audio: Y/Z frames avec parole (W%)
```

Le % de frames avec parole doit être **cohérent** entre runs GPU et CPU (~±5%).

## Tests de Non-Régression

### Protocole de Test

1. **Test GPU FP32** (nouveau standard)
   ```bash
   AUDIO_PROFILE=gpu_fp32 [lancer STEP4 depuis UI]
   ```

2. **Test CPU baseline**
   ```bash
   AUDIO_PROFILE=cpu_only [lancer STEP4 depuis UI]
   ```

3. **Comparer les sorties**
   ```bash
   python3 debug/compare_audio_json.py \
     "projets_extraits/.../video_audio.json" \
     "projets_extraits/.../video_audio_cpu.json"
   ```

**Critères d'acceptation :**
- Décalage première détection : **< 2 secondes**
- Différence % parole : **< 5%**
- Cohérence segments/locuteurs

## Impact Performance

### GPU FP32 vs GPU AMP

| Métrique | GPU FP32 | GPU AMP (optimized) |
|----------|----------|---------------------|
| VRAM utilisée | ~3.5 GB | ~2.8 GB |
| Temps inférence | ~7s | ~6s |
| Qualité diarisation | ✅ Haute | ⚠️ Dégradée |
| Cohérence CPU | ✅ Oui | ❌ Non |

**Trade-off :** FP32 consomme +25% VRAM mais garantit la **qualité** et la **reproductibilité**.

## Références

- Script : `workflow_scripts/step4/run_audio_analysis.py`
- Comparateur : `debug/compare_audio_json.py`
- Historique debug : `debug/history_debug_step_4_audio.md`
- Logs : `logs/step4/audio_analysis_*.log`

## Notes Techniques

### Pourquoi pyannote est sensible à AMP ?

Pyannote utilise des **scores de confiance** continus (floats) pour :
- Détection de parole (Voice Activity Detection)
- Séparation de locuteurs (embeddings)
- Seuils décisionnels

En FP16 (AMP) :
- Perte de précision sur les scores proches du seuil
- Accumulation d'erreurs numériques dans les embeddings
- **Faux négatifs** : segments légitimes rejetés par seuils inadaptés

### Pourquoi batch_size=1 ?

Sur GPU faible VRAM (<6GB), `batch_size > 1` provoque des OOM. Le batch_size=1 :
- Réduit la mémoire pic pendant l'inférence
- Reste compatible avec toutes les versions pyannote (v2/v3)
- N'impacte pas la qualité (traitement séquentiel)

### Fallback CPU harmonisé

Avant : fallback CPU utilisait des paramètres par défaut → divergence.
Après : fallback CPU hérite `batch_size` et force FP32 → cohérence.
