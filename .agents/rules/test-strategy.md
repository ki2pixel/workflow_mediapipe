---
trigger: model_decision
description: Applied when implementing or modifying test code. Rules for creating test perspective tables (equivalence partitioning/boundary values), Given/When/Then format, and coverage targets
globs: 
---

# Stratégie de Test & Assurance Qualité

Directives obligatoires pour la conception, l'implémentation et la validation des tests automatisés du projet.

## 1. Tableau des Perspectives de Test (Conception Amont)
Avant d'implémenter un composant ou un correctif significatif, concevoir un tableau des perspectives couvrant les classes d'équivalence et les valeurs limites :
- **Colonnes Obligatoires** : `ID Cas`, `Entrée / Précondition`, `Perspective (Nominal / Limite / Erreur)`, `Résultat Attendu`, `Remarques`.
- **Valeurs Limites Systématiques** : Vérifier a minima `0 / minimum / maximum / ±1 / vide / NULL`.
- **Flux Non-Bloquant** : **Ne pas marquer de pause** après l'affichage du tableau ; enchaîner directement sur l'implémentation des tests dans la même réponse, sauf ambiguïté bloquante.

### Modèle Synthétique
| ID Cas | Entrée / Précondition | Perspective | Résultat Attendu |
| :--- | :--- | :--- | :--- |
| TC-N-01 | Entrée nominale valide | Équivalence nominale | Traitement OK et retour contractuel |
| TC-E-01 | Entrée invalide ou vide | Valeur limite (vide/NULL) | Erreur de validation levée proprement |
| TC-F-01 | Défaillance dépendance | Cas d'erreur simulé (mock) | Exception interceptée et repli sécurisé |

## 2. Principes d'Implémentation du Code de Test
- **Parité des Cas d'Erreur** : Toujours inclure un nombre de cas d'erreur/limite **supérieur ou égal** aux cas nominaux (validation, exceptions, pannes réseau/BDD).
- **Structure Given / When / Then** : Structurer chaque test avec les marqueurs explicites :
  ```python
  # Given: Préconditions et jeu de données simulé
  # When:  Exécution de la méthode ou du service
  # Then:  Vérification des assertions et de l'état
  ```
- **Vérification d'Exceptions** : Toujours vérifier explicitement le **type exact** et le **message** de l'exception levée (`pytest.raises(..., match=...)`).

## 3. Commandes d'Exécution & Couverture
- **Objectif de Couverture** : Viser 100% de couverture de branches sur les chemins critiques du workflow (`process_video_worker`, `CSVService._normalize_url`, `WorkflowService`).
- **Commandes Dédiées par Environnement** :
  - Tests unitaires et intégration standards : `pytest tests/unit tests/integration`
  - Tests par étape dédiée : `./scripts/run_step2_tests.sh`, `./scripts/run_step3_tests.sh`, etc.
  - Frontend : `npm run test:frontend`
