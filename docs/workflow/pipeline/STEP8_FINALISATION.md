# Documentation Technique - Étape 8 : Finalisation

> Remplace l’ancienne « Étape 7 : Finalisation » après l’ajout de STEP7 (pré‑traitement AE).

---

## Purpose & Pipeline Role

### Objectif
L’Étape 8 constitue la phase finale du pipeline. Elle :
- archive les artefacts d’analyse (via `ResultsArchiver`) avant toute suppression,
- copie ensuite le dossier projet vers la destination finale,
- normalise la structure `docs/` en sortie,
- et supprime le dossier source (hors `ARCHIVES_DIR`).

### Rôle dans le Pipeline
- **Position** : dernière étape (STEP8)
- **Prérequis** : artefacts issus des étapes précédentes (au minimum vidéos ; idéalement scènes+tracking, audio optionnel)
- **Sortie** : projets finalisés dans `OUTPUT_DIR`

---

## Command & Environment

### Commande (WorkflowCommandsConfig)
- Interpréteur : `env/bin/python`
- Script : `workflow_scripts/step8/finalize_and_copy.py`
- Logs : `logs/step8/`

---

## Configuration

Variables principales :
- `OUTPUT_DIR` : destination finale (défaut `/mnt/cache`)
- `FALLBACK_OUTPUT_DIR` : destination de repli si `OUTPUT_DIR` est RO/non inscriptible
- `FINALIZE_MODE` : `lenient` (défaut), `strict`, `videos`
- `RESTORE_ARCHIVES_TO_OUTPUT` : `1` pour restaurer les analyses archivées dans la sortie

---

## Notes

- Compatibilité NTFS/FUSE : copie sans préservation des permissions si `chmod` non supporté.
- Sécurité : refuse de supprimer un répertoire source situé sous `ARCHIVES_DIR`.
