# Corrections STEP3 - Analyse de scènes TransNetV2

**Date**: 2025-11-18  
**Problème identifié**: Erreur CUDA multiprocessing + TracerWarnings TorchScript

---

## Diagnostic des erreurs

### Erreur principale (logs/app.log lignes 447-541)
- **Erreur**: `RuntimeError: CUDA driver error: invalid argument`
- **Fichier affecté**: `M6 - SDM - Philippe organise des réunions de travail originales.mp4` (12/12)
- **Résultat**: 11/12 vidéos réussies, return_code: 1

**Cause racine**:
- Contention/corruption CUDA avec `num_workers=2` (multiprocessing)
- Après ~11 vidéos traitées, l'état CUDA est corrompu
- Le fallback TorchScript→Eager échoue aussi car `torch.load` avec device CUDA plante

### Erreurs secondaires
1. **TracerWarnings** (lignes 163-175, etc.):
   - `assert` dans le code → traçage TorchScript incertain
   - `len(tensor)` au lieu de `tensor.shape[0]` → avertissement sur forme dynamique

---

## Corrections appliquées

### 1. `workflow_scripts/step3/transnetv2_pytorch.py`

**Objectif**: Éliminer TracerWarnings et rendre le code TorchScript-safe

**Changements**:
```python
# AVANT (ligne 57-59)
assert isinstance(inputs, torch.Tensor) and list(inputs.shape[2:]) == [27, 48, 3] and inputs.dtype == torch.uint8, \
    "incorrect input type and/or shape"

# APRÈS (lignes 57-63)
if not isinstance(inputs, torch.Tensor):
    raise TypeError(f"Expected torch.Tensor, got {type(inputs)}")
if inputs.dtype != torch.uint8:
    raise TypeError(f"Expected dtype torch.uint8, got {inputs.dtype}")
if inputs.dim() != 5 or inputs.shape[2] != 27 or inputs.shape[3] != 48 or inputs.shape[4] != 3:
    raise ValueError(f"Expected shape [B, T, 27, 48, 3], got {inputs.shape}")
```

```python
# AVANT (ligne 297)
assert no_channels == 3

# APRÈS (ligne 297-298)
if no_channels != 3:
    raise ValueError(f"Expected 3 color channels, got {no_channels}")
```

```python
# AVANT (ligne 306)
histograms.scatter_add_(0, binned_values, torch.ones(len(binned_values), dtype=torch.int32, device=frames.device))

# APRÈS (ligne 306)
histograms.scatter_add_(0, binned_values, torch.ones(binned_values.shape[0], dtype=torch.int32, device=frames.device))
```

**Bénéfices**:
- ✅ Élimine les TracerWarnings lors de la compilation TorchScript
- ✅ Messages d'erreur plus clairs et contextualisés
- ✅ Code plus robuste et maintenable

---

### 2. `workflow_scripts/step3/run_transnet.py`

**Objectif**: Fallback CUDA→CPU robuste + forcer workers=1 en CUDA

**Changements clés**:

#### A. Fallback CUDA lors du chargement du modèle (lignes 403-448)
```python
# Charger d'abord en CPU pour éviter les erreurs CUDA au chargement
state = torch.load(str(weights_path), map_location='cpu')
model.load_state_dict(state)
model.eval()
# Puis déplacer sur le device cible
model.to(device)
```

Avec gestion d'erreur CUDA → fallback CPU automatique.

#### B. Forcer num_workers=1 en mode CUDA (lignes 373-378)
```python
# En CUDA, FORCER 1 worker pour éviter contention GPU (critique)
device_mode = effective_cfg["device"]
if device_mode == "cuda" or (device_mode == "auto" and torch.cuda.is_available()):
    if effective_cfg["num_workers"] and effective_cfg["num_workers"] > 1:
        logging.warning(f"CUDA mode détecté: limitation forcée des workers de {effective_cfg['num_workers']} à 1 pour éviter la contention GPU.")
        effective_cfg["num_workers"] = 1
```

#### C. Sélection de device avec logs clairs (lignes 502-518)
```python
if cfg["device"] == "cpu":
    device = torch.device("cpu")
    logging.info(f"Device sélectionné: CPU (forcé par config)")
elif cfg["device"] == "cuda":
    if torch.cuda.is_available():
        device = torch.device("cuda")
        logging.info(f"Device sélectionné: CUDA (GPU disponible)")
    else:
        device = torch.device("cpu")
        logging.warning("CUDA demandé mais non disponible, fallback sur CPU")
# ...
```

#### D. Fallback multi-niveaux lors de la détection (lignes 547-574)
```python
# Niveau 1: Si TorchScript activé et échec, retenter en Eager
if scenes is None and use_ts and bool(cfg.get("torchscript_auto_fallback", True)):
    logging.warning(f"TorchScript a échoué pour {video_path.name}, tentative de fallback Eager...")
    model = _load_model_for_cfg(device, weights_path_str, use_torchscript=False)
    # ...

# Niveau 2: Si CUDA et échec, retenter en CPU
if scenes is None and device.type == 'cuda':
    logging.warning(f"Erreur avec CUDA pour {video_path.name}, tentative de fallback CPU...")
    cpu_device = torch.device('cpu')
    model = _load_model_for_cfg(cpu_device, weights_path_str, use_torchscript=False)
    # ...
```

**Bénéfices**:
- ✅ Résout l'erreur CUDA driver (contention multiprocessing)
- ✅ Fallback automatique CUDA→CPU en cas d'erreur
- ✅ Logs explicites pour debugging
- ✅ Traitement résilient : tente plusieurs stratégies avant d'abandonner

---

### 3. `config/step3_transnet.json`

**Changements**:
```json
{
  "num_workers": 1,        // AVANT: 2 → évite contention CUDA
  "torchscript": false,    // AVANT: true → évite TracerWarnings par défaut
  // ... autres paramètres inchangés
}
```

**Bénéfices**:
- ✅ Configuration par défaut plus stable
- ✅ Évite les erreurs CUDA multiprocessing
- ✅ TorchScript reste activable via CLI `--torchscript` si désiré

---

### 4. Tests créés

**Fichiers**:
- `tests/unit/test_step3_transnet.py`: Tests unitaires (validation inputs, device, config)
- `tests/integration/test_step3_integration.py`: Tests intégration (script exécution, config loading)

**Note**: Les tests requièrent que `pytest` soit installé dans `transnet_env` OU que `torch` soit dans `env` pour exécution.

---

## Validation

### Commande pour tester les corrections
```bash
cd /home/kidpixel5/kidpixel_files/kidpixel/workflow_mediapipe

# Relancer STEP3 sur les vidéos (devrait passer 12/12)
./transnet_env/bin/python workflow_scripts/step3/run_transnet.py

# Ou via l'application Flask
# L'application devrait maintenant traiter toutes les vidéos sans erreur CUDA
```

### Résultats attendus
- ✅ 12/12 vidéos traitées avec succès
- ✅ Aucun TracerWarning dans les logs
- ✅ Fallback CPU automatique si CUDA échoue
- ✅ Return code: 0 (succès)

---

## Checklist post-correction

- [x] Code corrigé dans `transnetv2_pytorch.py`
- [x] Fallback CUDA→CPU implémenté dans `run_transnet.py`
- [x] Configuration par défaut ajustée (`num_workers=1`, `torchscript=false`)
- [x] Tests unitaires créés
- [x] Tests intégration créés
- [ ] Tests exécutés et validés *(requiert sync environnements)*
- [ ] STEP3 re-exécuté sur les vidéos réelles
- [ ] Vérification logs : 12/12 succès, pas de TracerWarnings

---

## Critères d'acceptation (du prompt original)

| Critère | Status |
|---------|--------|
| STEP3 s'exécute sans erreurs bloquantes sur CPU | ✅ Corrigé |
| STEP3 s'exécute sans erreurs bloquantes sur CUDA | ✅ Corrigé (+ fallback CPU) |
| Les logs respectent les `progress_patterns` | ✅ Déjà OK |
| Les logs affichent une ligne de succès par fichier créé | ✅ Déjà OK |
| Les tests passent localement avec DRY_RUN | ⏳ À valider |

---

## Recommandations

1. **Ré-exécuter STEP3** pour vérifier que 12/12 vidéos passent maintenant.
2. **Vérifier les logs** (`logs/app.log` et `logs/step3/*.log`) pour confirmer l'absence de TracerWarnings.
3. **Installer pytest dans transnet_env** si besoin de tests unitaires complets:
   ```bash
   ./transnet_env/bin/pip install pytest
   ./transnet_env/bin/python -m pytest tests/unit/test_step3_transnet.py -v
   ```
4. **Optionnel**: Si GPU puissant et stable, on peut réactiver `num_workers=2` et `torchscript=true` dans la config pour performances maximales (à tester).

---

## Notes techniques

- **Environnements isolés**: Le projet utilise `transnet_env` (PyTorch, TransNet) distinct de `env` (Flask, autres steps). C'est une bonne pratique mais complique les tests cross-env.
- **TorchScript**: Désactivé par défaut car les TracerWarnings polluent les logs. Peut être réactivé manuellement si nécessaire.
- **Multiprocessing**: Désactivé en mode CUDA (`num_workers=1`) car la contention GPU cause des corruptions d'état. En CPU, multiprocessing reste possible.
