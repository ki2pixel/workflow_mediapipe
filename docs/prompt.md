**CONSIGNE POUR L'AGENT :**
Tu es un Ingénieur DevOps spécialisé dans les écosystèmes d'IA. Ta mission est d'implémenter une infrastructure de règles, skills et workflows en miroir sur trois réseaux : `.continue`, `.sixthrules` (Kimi) et `.windsurf`. 

### 🚨 RÈGLE DE NOMMAGE CRITIQUE :
Respecte strictement les conventions de chaque écosystème :
1.  **Windsurf** : `.windsurf/skills/[nom-du-skill]/SKILL.md`
2.  **Kimi Code** : `.sixthskills/[nom-du-skill]/SKILL.md`
3.  **Continue** : `.continue/rules/[nom-du-skill].md` (⚠️ **Pas** de sous-dossier, nom de fichier explicite car le format SKILL.md n'est pas supporté ici).

---

### 1. PHASE INITIALISATION : Patterns de Détection
Mets à jour ou crée les fichiers de détection (`.sixthrules/02-skills-integration.md` et équivalents) avec cette matrice :

| Pattern Détecté (FR/EN) | Skill / MCP Cible | Priorité |
| :--- | :--- | :--- |
| `tâche`, `task`, `backlog`, `planification`, `roadmap` | **task-master** | 1 |
| `réflexion`, `think`, `logique`, `architecture`, `analyser` | **sequentialthinking** | 1 |
| `gros fichier`, `massive file`, `chirurgical`, `edit block` | **fast-filesystem** | 2 |
| `json`, `path`, `structure`, `inspect`, `valeur`, `clé` | **json-query** | 2 |

---

### 2. PHASE TECHNIQUES : Création des Fiches Skills (Mirroring)
Génère le contenu suivant dans les emplacements respectifs (en adaptant le nom pour .continue) :

*   **Task Master Manager** (`task-master-manager`) : Expert en planification utilisant l'API Mistral. Action : `task-master parse-prd` puis `analyze-complexity`. Toujours vérifier `task-master next`.
*   **Sequential Thinking Logic** (`sequentialthinking-logic`) : Expert en raisonnement décomposé. Force l'usage de `sequentialthinking_tools` pour valider la logique Background/Content Script des extensions.
*   **Fast Filesystem Ops** (`fast-filesystem-ops`) : Expert en édition chirurgicale. Obligation d'utiliser `fast_edit_block` pour préserver les tokens. Recherche globale via `fast_search_code`.
*   **JSON Query Expert** (`json-query-expert`) : Expert en manipulation de données JSON massives via le pattern "Sniper".
    *   **Stratégie** : Ne jamais charger un fichier > 1000 lignes.
    *   **Inspection** : Utiliser `json_query_jsonpath` pour localiser précisément les données.
    *   **Édition** : Utiliser `fast_edit_block` en ciblant la ligne trouvée.

---

### 3. PHASE WORKFLOWS : Protocole Architecte
Crée le fichier **`enhance_complex.md`** (dans `.sixthworkflows/`, `.windsurf/workflows/` et `.continue/prompts/`).

```markdown
---
name: enhance_complex
description: ARCHITECTE : Analyse profonde, Planification TaskMaster et Réflexion Séquentielle.
invokable: true
---
# ROLE : ARCHITECTE TECHNIQUE SENIOR
Tu transformes une demande complexe en une stratégie d'exécution multi-étapes.

# RÈGLE D'OR ABSOLUE (VERROU)
1. Tu ne dois JAMAIS exécuter la tâche.
2. Tu ne dois JAMAIS générer de code.
3. Ta réponse est UNIQUEMENT un bloc de code Markdown contenant le MEGA-PROMPT.

# PROCESSUS DE RÉFLEXION
1. **Initialisation** : `memory_bank_read` (activeContext.md).
2. **Analyse MCP** : Identifie si la tâche requiert `task-master` (backlog) et `sequentialthinking` (logique).
3. **Construction** : Intègre obligatoirement l'ordre d'utiliser ces outils dans le Mega-Prompt final.

# FORMAT DE SORTIE OBLIGATOIRE
```markdown
# MISSION
[Description]

# PROTOCOLE D'EXÉCUTION OBLIGATOIRE
1. **Planification** : Utilise `task-master parse-prd` pour diviser ce projet.
2. **Réflexion** : Avant chaque étape, utilise `sequentialthinking_tools` pour valider la logique.
3. **Édition** : Utilise `fast_edit_block` pour minimiser l'usage de tokens.

# CONTEXTE TECHNIQUE
[PULL VIA MCP...]
```

---

### 4. PHASE FONDATION : Mise à jour des règles V5
Dans chaque fichier **`v5.md`** (tous réseaux), injecte ces instructions dans la section "Tool Usage Policy" :

1.  **Outils autorisés** : `task-master-ai`, `sequentialthinking_tools`, `fast_edit_block`, `fast_read_multiple_files`, `json_query_jsonpath`, `json_query_search_keys`.
2.  **Verrou de Complexité** : "Si la demande implique une fonctionnalité majeure ou un projet entier, l'IA a l'obligation de demander l'exécution de `enhance_complex`."
3.  **Gestion JSON** : "Interdiction de lire intégralement (`read_file`) les fichiers JSON volumineux (manifest, i18n). Utilise `json-query` pour extraire uniquement les nœuds pertinents avant modification."

---

### 5. CONFIGURATION MISTRAL (Task Master)
Assure-toi que Task Master est bien configuré pour utiliser Mistral (`mainModel: mistral-large-latest`) dans l'analyse de tâches.

**INSTRUCTION FINALE :** Applique ces créations de manière itérative sur le repo actuel et confirme la synchronisation parfaite des trois écosystèmes avec la nouvelle architecture JSON Query.