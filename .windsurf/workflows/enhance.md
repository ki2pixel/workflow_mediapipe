---
description: Améliorer un Prompt avec le Contexte du Projet
---

---
description: Améliorer un Prompt avec le Contexte du Projet et des techniques avancées (CoT, Persona, Structure)
---

### `/enhance` — Optimisation Avancée de Prompt
1. **Analyse Contextuelle (Ingénierie)**
   - Lire la requête brute de l'utilisateur.
   - Charger le contexte global via `read_file` sur les fichiers de la Memory Bank (`activeContext.md`, `progress.md`, `systemPatterns.md`, etc.).
   - Déterminer la nature de la tâche (Codage, Architecture, Documentation, Debugging) pour sélectionner la stratégie d'optimisation (voir étape 3).

2. **Recherche Active de Documentation**
   - Identifier les règles spécifiques au projet via `code_search` dans `docs/workflow/` et `.windsurf/rules/codingstandards.md`.
   - Utiliser `read_file` sur les documents pertinents trouvés.
   - Si des ambiguïtés techniques subsistent, faire un `grep_search` rapide pour valider l'usage actuel dans le code existant.

3. **Synthèse et Rédaction Structurée (Prompt Engineering)**
   - Compiler les informations en un "Mega-Prompt" en appliquant les techniques suivantes :
     - **Persona** : Définir le rôle exact (ex: "Expert Senior React" ou "Architecte Système").
     - **Contexte Projet** : Injecter explicitement les règles trouvées en étape 2 (Standards, Tech Stack).
     - **Chain-of-Thought (CoT)** : Si la tâche est complexe, instruire l'IA de "penser étape par étape" avant de coder.
     - **Format de Sortie** : Imposer un format strict (ex: XML tags, JSON, ou Markdown structuré) comme suggéré dans les modèles "Claude/GPT Optimized".
     - **Constitutional AI** : Ajouter une contrainte de vérification (sécurité, pas de régression, respect des types).
   
   - **Action** : Proposer *uniquement* le prompt amélioré à l'utilisateur sous forme de bloc de code, suivi d'une courte explication des améliorations (ex: "+ Contexte DB", "+ Gestion d'erreur").

4. **Validation et Exécution**
   - Demander confirmation à l'utilisateur ("Voulez-vous exécuter ce prompt ?").
   - Une fois le "oui" reçu :
     - Exécuter le prompt amélioré.
     - Utiliser systématiquement les outils (`read_file`, `apply_patch`, `run_command`) pour réaliser la tâche.
     - Vérifier la qualité du résultat final par rapport aux critères définis dans le prompt amélioré.