# Workflow: Docs Updater — Standardized & Metric-Driven

> Ce workflow harmonise la documentation en utilisant l'analyse statique standard (`cloc`, `radon`, `tree`) pour la précision technique et les modèles de référence pour la qualité éditoriale.

## 🚨 Protocoles Critiques
1.  **Outils autorisés** : MCP filesystem (`read_text_file`, `read_multiple_files`, `list_directory`, `directory_tree`, `search_files`, `edit_file`, `write_file`, `move_file`, `create_directory`), MCP ripgrep (`search`, `advanced-search`, `count-matches`, `list-files`, `list-file-types`), et `run_command` limité aux audits (`tree`, `cloc`, `radon`, `ls`).
2.  **Contexte** : Charger la Memory Bank (`productContext.md`, `systemPatterns.md`, `activeContext.md`, `progress.md`) via `read_file` avant toute action.
3.  **Source de Vérité** : Le Code (analysé par outils) > La Documentation existante > La Mémoire.

## Étape 1 — Audit Structurel et Métrique
Lancer les commandes suivantes pour ignorer les dossiers de données (ex: "Camille...", "assets") et cibler le cœur applicatif.

1.  **Cartographie (Filtre Bruit)** :
    - `run_command "tree -L 2 -I '__pycache__|venv|node_modules|.git|logs|debug|assets|*_output|*Camille*|transnet*|test*'"`
    - *But* : Visualiser uniquement l'architecture logicielle (`services`, `routes`, `utils`, `workflow_scripts`).
2.  **Volumétrie (Code Source)** :
    - `run_command "cloc services routes utils config scripts workflow_scripts static templates --md"`
    - *But* : Quantifier le code réel (Python vs JS) sans scanner les backups ou CSV.
3.  **Complexité Cyclomatique (Python Core)** :
    - `run_command "radon cc services routes utils workflow_scripts -a -nc"`
    - *But* : Repérer les points chauds (Score C/D/F).
    - **Règle** : Si Score > 10 (C), la doc DOIT expliquer la logique interne, pas juste les entrées/sorties.

## Étape 2 — Diagnostic Triangulé
Comparer les sources pour détecter les incohérences :

| **Intention** | Le "Pourquoi" | `read_file` (Memory Bank) |
| :--- | :--- | :--- |
| **Réalité** | Le "Quoi" & "Comment" | `radon` (complexité), `cloc` (volume), `search_files` |
| **Existant** | L'état actuel | `find_by_name` (sur `docs/workflow`), `read_file` |

**Action** : Identifier les divergences. Ex: "Le service `transnetv2_library.py` est complexe (Radon C) mais absent de la doc technique."

## Étape 3 — Sélection du Standard de Rédaction
Choisir le modèle approprié (inspiré des best-practices `doc-generate`) :

- **Documentation API** (`routes/`, `services/`) :
  - Entrées/Sorties précises.
  - Gestion des erreurs et codes HTTP.
- **Documentation Pipeline** (`workflow_scripts/`) :
  - **Flux de données** : Quel fichier entre ? Quel fichier sort ? (ex: `step3` -> JSON).
  - **Dépendances** : GPU requis ? Modèles chargés ?
- **Architecture & Utils** (`utils/`, `config/`) :
  - Diagrammes textuels (Mermaid) si interactions complexes.
  - Raison d'être des classes utilitaires.

## Étape 4 — Proposition de Mise à Jour
Générer un plan de modification avant d'appliquer :

```markdown
## 📝 Plan de Mise à Jour Documentation
### Audit Métrique
- **Cible** : `services/workflow_service.py`
- **Métriques** : 450 LOC, Complexité max C (12).

### Modifications Proposées
#### 📄 docs/workflow/.../target.md
- **Type** : [API | Pipeline | Architecture]
- **Diagnostic** : [Obsolète | Incomplet | Manquant]
- **Correction** :
  ```markdown
  [Contenu proposé respectant le standard choisi]
  ```
```

## Étape 5 — Application et Finalisation
1.  **Exécution** : Après validation, utiliser `edit_file` ou `multi_edit`.
2.  **Mise à jour Memory Bank** :
    - Si une dette technique importante est découverte via `radon` (Score D/F), ajouter impérativement une entrée dans `decisionLog.md` ou `systemPatterns.md`.

### Sous-protocole Rédaction — Application de documentation/SKILL.md

#### 5.1 Point d'Entrée Explicite
- **Mode Rédaction** : Déclenché après validation du plan de mise à jour.
- **Lecture obligatoire** : `.sixthskills/documentation/SKILL.md`.
- **Modèle à appliquer** : Spécifié dans le plan (article deep-dive, README, fiche technique, etc.).

#### 5.2 Checkpoints Obligatoires
**Avant rédaction** :
- [ ] TL;DR présent (section 1 du skill)
- [ ] Problem-first opening (section 2 du skill)

**Pendant rédaction** :
- [ ] Comparaison ❌/✅ (section 4 du skill)
- [ ] Trade-offs table si applicable (section 7 du skill)
- [ ] Golden Rule (section 8 du skill)
- [ ] Éviter les artefacts AI (section 6 du skill)

**Après rédaction** :
- [ ] Validation checklist « Avoiding AI-Generated Feel »
- [ ] Vérification ponctuation (remplacer " - " par ;/:/—)

#### 5.3 Traçabilité
Dans la proposition de mise à jour (Étape 4), ajouter :
#### Application du skill
- **Modèle** : [Article deep-dive | README | Technique]
- **Éléments appliqués** : TL;DR ✔, Problem-First ✔, Comparaison ✔, Trade-offs ✔, Golden Rule ✔

#### 5.4 Hook d'Automation
- **Validation Git** : Commentaire de commit « Guidé par documentation/SKILL.md — sections: [liste] »
- **Blocking** : Le workflow ne peut pas se terminer si les checkpoints ne sont pas cochés
- **Audit trail** : Chaque fichier modifié contient une note de validation interne
