# Contexte Actif (Active Context)

## Tâche en Cours
Aucune tâche active. Optimisation I/O pour STEP6/STEP7 (streaming JSON) complétée avec succès.

## Objectifs
- Maintenir l'intégrité du repo.
- Préparer pour le développement futur.

## Décisions Récentes
- [2026-05-27 18:52:00] Alignement complet de la documentation avec le codebase réel via le workflow `docs-updater` : documentation de `ijson` (streaming O(1) RAM) pour STEP6/STEP7 et des safeguards de démarrage sécurisé de production et de `validate_startup.py` dans le guide de sécurité.
- [2026-05-27 18:40:00] Implémentation de la recommandation d'audit "Optimisation I/O pour STEP6/STEP7". Utilisation de `ijson` pour parser les fichiers de tracking en flux. Refonte de `json_reducer.py` et `preprocess_ae_json.py` pour un maintien de la RAM O(1).
- [2026-05-27 18:28:00] Implémentation de la recommandation d'audit "Sécurité en Production". L'application Flask (app_new.py) et le script de validation (validate_startup.py) crashent désormais fermement en production (DEBUG=False) si des secrets/tokens par défaut (dev-*) sont configurés.
- [2026-05-27 18:08:00] Validation (commit) et publication (push) du nettoyage des fichiers non suivis/obsolètes et de l'ajout du rapport d'audit d'architecture.
- [2026-03-13 18:29:00] Rollback Git vers commit 11482b2 ("docs: Replace Kaggle/Google Colab docs with Lightning AI documentation") suite à problème avec la feature STEP5 remote Lightning.
- [2026-03-13 18:29:00] Suppression des fichiers non suivis : services/step5_remote_lightning_service.py, tests associés, et répertoire .shrimp_task_manager/.
- [2026-03-13 18:27:00] Clôture du chantier STEP5 remote Lightning après implémentation, tests, mise à jour de la documentation pipeline et synchronisation complète de la Memory Bank (avant rollback).

## Questions Ouvertes
- Évaluer si la feature STEP5 remote Lightning doit être réimplémentée ou abandonnée.
- Vérifier l'état de la documentation Lightning AI après rollback.

## Prochaines Étapes
- Vérifier le fonctionnement du repo après le commit et push de nettoyage.
- Reprendre le développement selon les besoins.