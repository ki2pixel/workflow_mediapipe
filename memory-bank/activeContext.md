# Contexte Actif (Active Context)

## Tâche en Cours
Aucune tâche active. La centralisation et la synchronisation des scripts TPU avec le frontend et les environnements virtuels sont terminées, et tous les tests unitaires et d'intégration sont au vert.

## Objectifs
- Maintenir l'intégrité du repo.
- Préparer pour le développement futur.

## Décisions Récentes
- [2026-06-11 19:25:00] **Centralisation et Synchronisation TPU-Frontend (COMPLET)** : Centralisation des scripts expérimentaux TPU de `scripts/workflow_scripts/` vers `workflow_scripts/` pour aligner la résolution des chemins des modèles (`assets/`) et des fichiers journaux (`logs/stepX/`) avec le frontend. Ajout du fallback de détection de l'environnement virtuel dans `settings.py` pour localiser `coral_env` à la racine si inexistant sur le disque externe. Correction et validation des imports dans la suite de tests unitaires TPU (Steps 3, 4 et 5).
- [2026-06-11 18:50:00] **Architecture Hybride TPU/CPU** : Intégration optionnelle d'un routeur asynchrone vers le TPU Coral activable via `.env`, isolant cette expérimentation des process de production standards. Les réseaux incompatibles ont été remplacés par des alternatives INT8 avec une gestion des compromis mathématiques (ex: Filtre de Kalman) effectuée sur CPU.
- [2026-06-11 13:15:00] **Validation Matérielle Google Coral M.2 TPU (COMPLET)** : Diagnostic matériel et logiciel du module Coral TPU sur architecture Threadripper X399. Contournement des bugs ASPM/AER via GRUB (`pcie_aspm=off pci=noaer`) et installation du pilote patché `feranick/gasket-driver` pour assurer la compatibilité avec le noyau Linux 6.8. Nœud `/dev/apex_0` opérationnel.
- [2026-06-04 13:15:00] **Validation Finale et Correction du Script de Tests STEP5 (COMPLET)** : Résolution d'une erreur de syntaxe/guillemets dans `scripts/run_step5_tests.sh`. Exécution réussie de la suite de tests STEP5 (32 tests passés, 1 skip) sous `tracking_env_slim` et validation du démarrage de l'application Flask via `validate_startup.py` (Validation PASSED).
- [2026-06-04 13:10:00] **Audit et Harmonisation de la Documentation et Suite de Tests (COMPLET)** : Harmonisation de `docs/workflow/ops/testing-strategy.md` pour l'aligner avec l'état réel (380 tests, tests STEP5 et suite legacy). Correction de bugs de sérialisation JSON critiques (clés magiques non quotées) dans `json_reducer.py`. Résolution des dépendances et de l'isolation dans la suite de tests (`conftest.py`, `test_step5_json_formats`, `test_csv_monitor_no_retrigger`, `test_step2_fps_parsing`, `test_step4_lemonfox_toggle`).
- [2026-06-04 12:35:00] **Alignement Coding Standards et Environnements Virtuels (COMPLET)** : Alignement de `.agents/rules/codingstandards.md` avec l'état réel du repository (documentation de la STEP3, dépréciation de MySQL, et standardisation de `tracking_env_slim` pour MediaPipe CPU). Nomenclature des environnements virtuels standardisée dans tous les scripts système, de test et de validation.
- [2026-06-03 20:16:00] **Correction Tests Historiques MySQL (COMPLET)** : Résolution des erreurs de collection et d'exécution dans la suite de tests unitaires et d'intégration legacy (`tests/legacy/`). Redirection des imports vers `services.deprecated.mysql_service`, remplacement des mocks `config` obsolètes par des injections explicites, et skip documenté des tests dépendant d'anciennes méthodes de `CSVService`. Suite de tests validée avec succès via `tests-suite-guardian`.

## Questions Ouvertes
- Aucune

## Prochaines Étapes
- Aucune