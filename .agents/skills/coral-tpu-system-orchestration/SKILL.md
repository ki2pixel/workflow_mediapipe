---
name: coral-tpu-system-orchestration
description: Expert du pont matériel Google Coral Edge TPU. Gère le pilote Gasket, la configuration PCIe/ASPM, l'allocation /dev/apex_0 et le routeur asynchrone (coral_tpu_orchestrator).
trigger: coral, tpu, gasket, apex_0, aspm, pcie, orchestrator, sram
---

# Coral TPU System Orchestration Skill

Ce skill est dédié à la maintenance et au diagnostic de l'intégration matérielle du Google Coral M.2 PCIe TPU et de son routeur applicatif.

## 🎯 Rôle
Maintenir l'intégrité du pont matériel TPU-Système. Gérer la configuration du noyau (pilote `feranick/gasket-driver`, paramètres ASPM/AER), surveiller l'allocation `/dev/apex_0` et diagnostiquer la gestion du double niveau de verrouillage/sérialisation :
- **Macro** : Le singleton `coral_tpu_orchestrator.py` qui sérialise les étapes globales sur la SRAM PCIe (8 Mo).
- **Micro** : Le thread lock local `_tpu_lock` au sein de `run_audio_diarization_tpu.py` pour sécuriser les exécutions concurrentes de YAMNet.
- **Asynchrone** : L'architecture Producer-Consumer (`threading`, `queue`) dans `run_scene_detect_tpu.py` qui parallélise l'I/O FFmpeg et l'inférence TPU sans surcharger l'ASIC.

## 📋 Checklist de Préparation
Avant toute intervention, vérifiez :
- [ ] Les arguments GRUB (désactivation de la gestion d'énergie défaillante) : `cat /proc/cmdline | grep pcie_aspm=off`
- [ ] La présence du nœud matériel : `ls -l /dev/apex_0`
- [ ] L'activation environnementale : `ENABLE_CORAL_TPU_ACCELERATION=true` dans le `.env`
- [ ] L'environnement virtuel : Activation de `coral_env`

## 🛠 Commandes Types
- Vérification des logs système du pilote :
  ```bash
  dmesg | grep gasket
  ```
- Vérification du module chargé :
  ```bash
  lsmod | grep apex
  ```

## 🚑 Checklist Diagnostique & Résolution

### Incident 1 : TPU non détecté
- **Symptôme** : `/dev/apex_0` introuvable ou erreur d'initialisation.
- **Action** : Confirmer que `pcie_aspm=off pci=noaer` est bien appliqué au boot pour éviter le power-state mismatch. Relancer le service `udev` si nécessaire.

### Incident 2 : Out of Memory (OOM) sur le TPU
- **Symptôme** : Crash lors de l'allocation d'un tenseur sur le TPU.
- **Action** : Inspecter la taille des batchs dans `coral_tpu_orchestrator.py` (doit être `batch=1` pour MobileNetV2) et purger la file asynchrone. Le TPU M.2 ne dispose que de 8 Mo de SRAM, toute sur-allocation provoque un crash matériel.

## ⚠️ Séparation des Responsabilités
Contrairement à `pipeline-diagnostics` qui s'occupe de la santé générale du workflow, ce skill est l'expert exclusif de l'interface bas-niveau avec l'ASIC Coral et de la gestion de sa mémoire limitée via le singleton applicatif.
