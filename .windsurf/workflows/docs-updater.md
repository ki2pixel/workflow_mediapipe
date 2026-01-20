---
description: Docs Updater (Context-Aware with Code Verification)
---

# Workflow: Docs Updater — Official Tooling Compliance

> Garantit que l'analyse Memory Bank → Code → Documentation se fait uniquement avec les outils autorisés (`code_search`, `grep_search`, `read_file`, `apply_patch` via `edit/multi_edit`, `find_by_name`).

## Étape 0 — Rappels obligatoires
1. Charger le contexte Memory Bank (productContext, activeContext, decisionLog, progress, systemPatterns) avec `read_file` **avant toute autre action**.
2. Adhérer aux standards décrits dans `.windsurf/rules/codingstandards.md` et aux politiques Memory Bank.
3. Démarrer toute investigation inconnue avec `code_search`; n'utiliser `grep_search` que pour des motifs précis.

## Étape 1 — Acquisition du Contexte (Le « Pourquoi »)
- **Action** : `read_file` sur `memory-bank/{progress, decisionLog, productContext, systemPatterns}.md`.
- **Analyse** : Résumer mentalement objectifs, décisions et travaux en cours.

## Étape 2 — Cartographie de la Documentation (L'« Existant »)
- **Action** : Utiliser `find_by_name` (ou `code_search` sur `docs/workflow/{core,technical,pipeline,features,admin}/`) pour recenser les fichiers pertinents. Proscrire `run_command`.
- **Validation** : Lorsque nécessaire, ouvrir les fichiers ciblés avec `read_file` pour vérifier leur actualité.

## Étape 3 — Inspection du Code Source (Le « Quoi »)
1. **Ciblage** : Lancer `code_search` basé sur les éléments identifiés aux étapes 1 et 2.
2. **Lecture** : Employer `read_file` pour examiner les modules, signatures et docstrings réellement implémentés.
3. **Vérification** : Confirmer la cohérence des signatures, flags, paramètres et flux métier.

## Étape 4 — Triangulation & Synthèse
- Sans outils : croiser Pourquoi (Memory Bank), Quoi (code) et Existant (docs) pour détecter écarts ou lacunes.

## Étape 5 — Rapport Structuré
Produire :
```
## 📚 Assistant de Documentation (Analyse Triangulée)
### 1. Diagnostic des Changements
...
### 2. Preuves du Code (Code Evidence)
- @filepath#Lx-Ly — Divergence …
### 3. Plan de Mise à Jour
#### 📄 Fichier : docs/workflow/{core|technical|pipeline|features|admin}/.../example.md
- Problème identifié : …
- Suggestion précise : ```markdown ... ```
```

## Étape 6 — Application (après validation)
1. Mettre à jour les fichiers docs via `apply_patch` (équivalent `edit/multi_edit`).
2. Effectuer des recherches ciblées additionnelles avec `grep_search` si besoin.
3. Si des tests sont requis, suivre les workflows `/commit-*` correspondants.

> **Note** : Aucun usage de `run_command` n'est nécessaire pour cette procédure hors exécution de tests explicitement demandés. Préférer systématiquement les outils de navigation/fichier dédiés.