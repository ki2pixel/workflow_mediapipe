# Universal Dataset Design Patterns

**TL;DR**: Concevez des datasets spécialisés avec la règle 40/35/15/10 (architecture/opérations/integration/best practices) et des exemples techniques qui transforment un LLM générique en expert de domaine.

Vous avez 1000 questions-réponses sur votre projet, mais le modèle fine-tuné ne sait toujours pas quelle commande utiliser pour votre environnement spécifique. C'est le "Generic Dataset Problem" - trop de données générales, pas assez d'expertise technique précise.

## 🎯 Pattern de Distribution Universelle

### La Règle 40/35/15/10

| Catégorie | Pourcentage | Focus | Exemples Types |
|-----------|-------------|-------|-----------------|
| **Architecture Knowledge** | 40% | Structure, patterns, concepts | Design patterns, architecture decisions, component relationships |
| **Operations** | 35% | Commandes, workflows, erreurs | CLI commands, API calls, troubleshooting steps |
| **Integration** | 15% | APIs, ponts, écosystèmes | Third-party integrations, bridges, workflows |
| **Best Practices** | 10% | Sécurité, qualité, standards | Coding standards, security practices, testing patterns |

**Pourquoi cette distribution ?**
- **40% Architecture** : Le modèle doit comprendre la "mentalité" du domaine
- **35% Operations** : L'usage quotidien repose sur des commandes précises
- **15% Integration** : Les projets vivent dans un écosystème
- **10% Best Practices** : Évite les mauvaises habitudes et les erreurs

## 📊 Pattern Structure d'Exemple

### Template JSONL Universel

```json
{
  "messages": [
    {
      "role": "system",
      "content": "Tu es un expert senior du domaine [DOMAIN] avec [EXPERIENCE] années d'expérience. Tu maîtrises [KEY_CONCEPTS], [SPECIFIC_TOOLS], et [PATTERNS]. Tes réponses sont toujours précises, incluent les commandes exactes avec les bons chemins/paramètres, et expliquent le 'pourquoi' derrière chaque décision technique."
    },
    {
      "role": "user",
      "content": "[QUESTION_TECHNIQUE_SPECIFIQUE]"
    },
    {
      "role": "assistant",
      "content": "[RÉPONSE_PRÉCISE_AVEC_COMMANDES_ET_PATTERNS]"
    }
  ]
}
```

### Pattern de Réponse Expert

Chaque réponse doit contenir :

1. **Commande exacte** : Avec chemins/paramètres spécifiques
2. **Pourquoi** : Explication de la décision technique  
3. **Alternatives** : Options avec trade-offs
4. **Vérification** : Comment valider que ça fonctionne
5. **Erreurs communes** : Problèmes et solutions

## 🏗️ Patterns par Catégorie

### Architecture Knowledge Patterns

#### Pattern 1 : Design Decisions
```json
{
  "user": "Pourquoi utiliser le pattern [PATTERN] dans ce projet ?",
  "assistant": "C'est un choix architectural délibéré pour [RAISON].\n\n❌ **L'approche alternative** :\n[code avec problème]\n\n✅ **L'approche [PATTERN]** :\n[code solution]\n\n**Pourquoi cette approche ?**\n1. [Bénéfice 1 avec exemple]\n2. [Bénéfice 2 avec exemple]\n3. [Bénéfice 3 avec exemple]\n\n**Quand l'utiliser** : [Conditions]\n**Quand l'éviter** : [Contre-indications]"
}
```

#### Pattern 2 : Component Relationships
```json
{
  "user": "Comment [COMPONENT_A] communique avec [COMPONENT_B] ?",
  "assistant": "[COMPONENT_A] et [COMPONENT_B] suivent le pattern [COMMUNICATION_PATTERN].\n\n**Architecture** :\n```mermaid\ngraph LR\n    A[Component A] -->|API/Event| B[Component B]\n    B -->|Response| A\n```\n\n**Implémentation** :\n```python\n# Component A\nclass ComponentA:\n    def send_to_b(self, data):\n        return component_b.process(data)\n\n# Component B  \nclass ComponentB:\n    def process(self, data):\n        # Logique métier\n        return processed_data\n```\n\n**Pourquoi ce découplage ?**\n- **Testabilité** : Chaque composant testable isolément\n- **Réutilisabilité** : B peut être utilisé par d'autres composants\n- **Maintenabilité** : Évolution indépendante des composants"
}
```

### Operations Patterns

#### Pattern 3 : Exact Commands
```json
{
  "user": "Quelle commande exacte pour [ACTION_SPECIFIQUE] ?",
  "assistant": "Pour [ACTION_SPECIFIQUE], utilisez cette commande précise :\n\n```bash\n[COMMAND_EXACTE_AVEC_PATHS_ET_PARAMS]\n```\n\n**Paramètres importants** :\n- `[PARAM1]` : [Explication]\n- `[PARAM2]` : [Explication]\n\n**Prérequis** :\n```bash\n# Vérification [PREREQUIS]\n[VERIFICATION_COMMAND]\n```\n\n**Si erreur [ERREUR_COMMUNE]** :\n```bash\n# Solution\n[SOLUTION_COMMAND]\n```\n\n**Performance attendue** : [MÉTRIQUES]"
}
```

#### Pattern 4 : Troubleshooting
```json
{
  "user": "J'ai cette erreur : [ERROR_MESSAGE]. Que faire ?",
  "assistant": "C'est l'erreur classique [ERROR_NAME]. Voici le diagnostic et solution.\n\n**🔍 Diagnostic** :\nL'erreur [ERROR_MESSAGE] se produit quand [CAUSE_RACINE].\n\n**🛠️ Solutions (par ordre de probabilité)** :\n\n1. **Solution 1 (90% des cas)** :\n```bash\n[SOLUTION_1_COMMAND]\n```\nVérifiez avec : `[VERIFICATION_1]`\n\n2. **Solution 2 (8% des cas)** :\n```bash\n[SOLUTION_2_COMMAND]\n```\n\n3. **Solution 3 (2% des cas)** :\n```bash\n[SOLUTION_3_COMMAND]\n```\n\n**🎯 Prévention** :\nPour éviter cette erreur à l'avenir :\n- [PRÉVENTION_1]\n- [PRÉVENTION_2]\n\n**📊 Contexte** : Cette erreur est fréquente quand [CONTEXT_SPECIFIQUE]."
}
```

### Integration Patterns

#### Pattern 5 : API Bridges
```json
{
  "user": "Comment intégrer [EXTERNAL_SERVICE] avec mon projet ?",
  "assistant": "Utilisez le pont [BRIDGE_PATTERN] pour intégrer [EXTERNAL_SERVICE].\n\n**Architecture du pont** :\n```python\nclass [BRIDGE_NAME]:\n    def __init__(self, config):\n        self.client = [EXTERNAL_SERVICE].Client(config.api_key)\n    \n    def [ACTION](self, data):\n        # Transformation format interne → format externe\n        external_data = self._transform_to_external(data)\n        \n        # Appel service externe\n        response = self.client.[API_METHOD](external_data)\n        \n        # Transformation format externe → format interne\n        return self._transform_to_internal(response)\n```\n\n**Configuration requise** :\n```yaml\n# config.yaml\nexternal_service:\n  api_key: \"${EXTERNAL_API_KEY}\"\n  base_url: \"https://api.service.com\"\n  timeout: 30\n```\n\n**Cas d'usage** :\n```python\nbridge = [BRIDGE_NAME](config)\nresult = bridge.[ACTION](internal_data)\n```\n\n**Gestion erreurs** :\n```python\ntry:\n    result = bridge.[ACTION](data)\nexcept [SERVICE_ERROR] as e:\n    logger.error(f\"Erreur {SERVICE}: {e}\")\n    # Fallback ou retry\n```"
}
```

### Best Practices Patterns

#### Pattern 6 : Security
```json
{
  "user": "Quelle est la manière sécurisée de gérer [SENSIBLE_OPERATION] ?",
  "assistant": "Pour [SENSIBLE_OPERATION], suivez le pattern [SECURITY_PATTERN].\n\n❌ **Approche non sécurisée** :\n```python\n# DANGEREUX : Secrets en dur\nAPI_KEY = \"sk-1234567890abcdef\"\npassword = \"password123\"\n```\n\n✅ **Approche sécurisée** :\n```python\nimport os\nfrom cryptography.fernet import Fernet\n\nclass SecureManager:\n    def __init__(self):\n        self.key = os.getenv(\"MASTER_KEY\").encode()\n        self.cipher = Fernet(self.key)\n    \n    def encrypt_sensitive_data(self, data):\n        return self.cipher.encrypt(data.encode())\n    \n    def get_api_key(self, service):\n        encrypted_key = os.getenv(f\"{service.upper()}_API_KEY\")\n        return self.cipher.decrypt(encrypted_key.encode()).decode()\n```\n\n**Principes de sécurité** :\n1. **Zero Secrets in Code** : Jamais de secrets en dur\n2. **Principle of Least Privilege** : Permissions minimales\n3. **Encryption at Rest** : Données sensibles chiffrées\n4. **Audit Trail** : Journalisation des accès\n\n**Validation** :\n```bash\n# Vérifier aucune clé en dur\ngrep -r \"sk-\" --include=\"*.py\" src/\n# Vérifier variables d'vironnement\nenv | grep API_KEY\n```"
}
```

## 📋 Checklist Qualité Universelle

Pour chaque exemple du dataset :

### ✅ Contenu Technique
- [ ] Question spécifique au domaine
- [ ] Commandes exactes avec paths/paramètres
- [ ] Patterns de code respectant les standards
- [ ] Explication du "pourquoi" technique
- [ ] Alternatives avec trade-offs

### ✅ Structure Format
- [ ] JSONL valide syntaxiquement
- [ ] System prompt expert cohérent
- [ ] Pas de secrets/clés en dur
- [ ] Échappement caractères spéciaux

### ✅ Valeur Pédagogique
- [ ] Enseigne un pattern ou une commande
- [ ] Exemples multiples (2+ scénarios)
- [ ] Gestion erreurs intégrée
- [ ] Métriques de performance

### ✅ Domain Specificity
- [ ] Termes techniques du domaine
- [ ] Commandes spécifiques aux outils
- [ ] Patterns architecturaux propres
- [ ] Contexte d'usage réel

## 🔄 Processus de Création

### Étape 1 : Collecte Sources
1. **Documentation existante** : README, guides techniques
2. **Code source** : Patterns récurrents, commandes CLI
3. **Logs et erreurs** : Problèmes réels et solutions
4. **Questions utilisateurs** : FAQ, support tickets

### Étape 2 : Catégorisation
1. **Architecture** : Concepts, design decisions, patterns
2. **Operations** : Commandes, workflows, troubleshooting
3. **Integration** : APIs, ponts, écosystèmes
4. **Best Practices** : Sécurité, qualité, standards

### Étape 3 : Création Exemples
1. **Template system prompt** : Adapter au domaine
2. **Questions techniques** : Basées sur cas réels
3. **Réponses expertes** : Avec commandes exactes
4. **Validation qualité** : Checklist complète

### Étape 4 : Review et Itération
1. **Review par expert** : Validation technique
2. **Test dataset** : Vérification format/cohérence
3. **Balance catégories** : Respect 40/35/15/10
4. **Finalisation** : Export JSONL production

## 🎯 Golden Rule du Dataset Design

**Teach patterns, not just answers** : Chaque exemple doit enseigner un pattern ou une commande réutilisable. La capacité du modèle à généraliser dépend de la qualité pédagogique des exemples, pas de leur quantité.

---

*Voir [Prompt Engineering Patterns](prompt-engineering.md) pour les system prompts et [Evaluation Metrics](evaluation-metrics.md) pour mesurer la qualité.*
