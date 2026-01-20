---
description: Améliorer un Prompt avec le Contexte du Projet
---

### `/enhance` — Améliorer un prompt avec le contexte projet
1. **Analyse initiale**  
   - Lire la requête brute et la consigner dans la réponse courante.  
   - Charger le contexte via `read_file` sur les mêmes fichiers de la Memory Bank.
2. **Recherche ciblée de documentation**  
   - Utiliser `code_search` pour identifier les fichiers `docs/workflow/{core,technical,pipeline,features,admin}/` pertinents.  
   - Ouvrir ces fichiers avec `read_file`; si une section doit être localisée par mot-clé, employer `grep_search`.
3. **Synthèse et rédaction du prompt amélioré**  
   - Compiler les informations recueillies en un prompt unique rappelant les standards (ex: `codingstandards.md`).  
   - Ne produire que le prompt amélioré et demander confirmation, comme spécifié.
4. **Exécution après validation**  
   - Une fois le “oui” reçu, suivre les étapes du prompt amélioré en réutilisant systématiquement `read_file`, `code_search` et `apply_patch` (ou `edit`/`multi_edit` lorsque disponibles) pour toute analyse/édition.  
   - Mentionner dans la réponse finale quelles parties ont été consultées grâce à ces outils.