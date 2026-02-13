#!/usr/bin/env python3
"""
Universal Dataset Generator for Fine-Tuning

Génère des datasets JSONL pour fine-tuning LLM basés sur l'analyse de domaine.
Utilise les patterns universels et les templates adaptables.

Usage:
    python generate_dataset.py --domain_analysis domain_analysis.json --output dataset.jsonl --count 100
"""

import json
import random
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import re

@dataclass
class DatasetConfig:
    """Configuration pour la génération de dataset"""
    domain: str
    experience_years: str
    key_tools: List[str]
    patterns: List[str]
    concepts: List[str]
    integrations: List[str]
    categories: Dict[str, Any]

class UniversalDatasetGenerator:
    """Générateur de dataset universel et adaptable"""
    
    def __init__(self, domain_analysis_path: str):
        self.domain_analysis = self._load_domain_analysis(domain_analysis_path)
        self.config = self._create_config()
        
        # Templates adaptables
        self.system_prompt_template = self._get_system_prompt_template()
        self.example_templates = self._get_example_templates()
        
        # Logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _load_domain_analysis(self, path: str) -> Dict:
        """Charge l'analyse de domaine"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _create_config(self) -> DatasetConfig:
        """Crée la configuration depuis l'analyse"""
        return DatasetConfig(
            domain=self.domain_analysis["domain"],
            experience_years="5",  # Par défaut, adaptable
            key_tools=self.domain_analysis["tools"][:10],  # Top 10 outils
            patterns=self.domain_analysis["patterns"][:10],  # Top 10 patterns
            concepts=self.domain_analysis["concepts"][:10],  # Top 10 concepts
            integrations=self.domain_analysis["integrations"][:5],  # Top 5 intégrations
            categories=self.domain_analysis["categories"]
        )
    
    def _get_system_prompt_template(self) -> str:
        """Template du system prompt adaptable"""
        return f"""Tu es un expert senior du domaine {self.config.domain} avec {self.config.experience_years} années d'expérience. Tu maîtrises {', '.join(self.config.key_tools[:5])}, {', '.join(self.config.patterns[:3])}, et les standards {self.config.domain}. Tes réponses sont toujours précises, incluent les commandes exactes avec les bons paramètres, et expliquent le 'pourquoi' derrière chaque décision technique."""
    
    def _get_example_templates(self) -> Dict[str, List[Dict]]:
        """Templates d'exemples par catégorie"""
        return {
            "architecture": [
                {
                    "user_template": "Quel pattern utiliser pour {pattern_problem} dans {domain} ?",
                    "response_template": self._get_architecture_pattern_template()
                },
                {
                    "user_template": "Comment {component_a} communique avec {component_b} dans {domain} ?",
                    "response_template": self._get_component_relationship_template()
                }
            ],
            "operations": [
                {
                    "user_template": "Quelle commande exacte pour {action} dans {domain} ?",
                    "response_template": self._get_command_template()
                },
                {
                    "user_template": "J'ai cette erreur : {error_message}. Que faire dans {domain} ?",
                    "response_template": self._get_troubleshooting_template()
                }
            ],
            "integration": [
                {
                    "user_template": "Comment intégrer {external_service} avec mon projet {domain} ?",
                    "response_template": self._get_integration_template()
                }
            ],
            "best_practices": [
                {
                    "user_template": "Quelles sont les best practices pour {security_topic} dans {domain} ?",
                    "response_template": self._get_best_practices_template()
                }
            ]
        }
    
    def _get_architecture_pattern_template(self) -> str:
        """Template pour les patterns d'architecture"""
        return """Pour {pattern_problem} dans {domain}, le pattern {pattern_name} est la meilleure approche.

❌ **L'approche naïve** :
```python
# Code problématique
{problematic_code}
```
*Problèmes* : {problems}

✅ **Le pattern {pattern_name}** :
```python
# Implémentation correcte
class {PatternName}Class:
    def __init__(self, {params}):
        self.{attribute1} = {value1}
        self.{attribute2} = {value2}
    
    def {method_name}({method_params}):
        # Logique du pattern
        {pattern_logic}
        return {result}
```

**Pourquoi ce pattern ?**
1. **{advantage1}** : {explanation1}
2. **{advantage2}** : {explanation2}
3. **{advantage3}** : {explanation3}

**Cas d'usage typique dans {domain}** :
```python
# Exemple réel
pattern = {PatternName}Class({config_example})
result = pattern.{method_name}({input_example})
```

**Performance et scalabilité** :
- Complexité : {complexity}
- Memory usage : {memory_usage}
- Scalability : {scalability_info}

**Quand éviter ce pattern** :
- {contra_indication1}
- {contra_indication2}"""
    
    def _get_command_template(self) -> str:
        """Template pour les commandes techniques"""
        return """Pour {action} dans {domain}, utilisez cette commande précise :

```bash
{exact_command_with_paths_and_params}
```

**Paramètres importants** :
- `{param1}` : {explanation_param1}
- `{param2}` : {explanation_param2}

**Pourquoi cette approche ?**
1. **{reason1}** : {detailed_explanation1}
2. **{reason2}** : {detailed_explanation2}
3. **{reason3}** : {detailed_explanation3}

**Alternatives avec trade-offs** :

❌ **Alternative 1 (Non recommandée)** :
```bash
{alternative_command_1}
```
*Inconvénients* : {disadvantages1}

✅ **Alternative 2 (Cas spécifique)** :
```bash
{alternative_command_2}
```
*Quand l'utiliser* : {usage_condition2}

**Vérification post-exécution** :
```bash
# Vérifier que {action} a réussi
{verification_command}

# Confirmer l'état
{confirmation_command}
```

**Erreurs communes et solutions** :

Si vous rencontrez `{common_error1}` :
```bash
# Solution 1 (90% des cas)
{solution_error1}
```

Si vous rencontrez `{common_error2}` :
```bash
# Solution 2 (8% des cas)
{solution_error2}
```

**Performance attendue** :
- Temps d'exécution : {execution_time}
- Ressources utilisées : {resources}
- Scalabilité : {scalability}"""
    
    def _get_troubleshooting_template(self) -> str:
        """Template pour le diagnostic d'erreurs"""
        return """C'est l'erreur classique {error_name} dans {domain}. Voici le diagnostic complet et les solutions.

**🔍 Diagnostic immédiat** :
L'erreur `{error_message}` se produit quand {root_cause}. C'est fréquent quand {specific_context}.

**🛠️ Solutions par ordre de probabilité** :

### 1. Solution Principale (90% des cas)
```bash
# Solution immédiate
{main_solution}

# Vérifier la résolution
{verification_1}
```
**Pourquoi ça marche** : {solution_explanation1}

### 2. Solution Alternative (8% des cas)
```bash
# Si la solution 1 échoue
{alternative_solution}

# Valider le résultat
{verification_2}
```
**Quand l'utiliser** : {usage_condition2}

### 3. Solution Avancée (2% des cas)
```bash
# Pour les cas complexes
{advanced_solution}
```
**Prérequis** : {prerequisites3}

**🎯 Prévention à long terme** :
Pour éviter cette erreur à l'avenir dans {domain} :
1. **Preventive config** : {preventive_config}
2. **Monitoring** : {monitoring_setup}
3. **Best practice** : {best_practice}

**📊 Contexte technique** :
Cette erreur est documentée dans {documentation_reference} et affecte principalement {affected_components}."""
    
    def _get_integration_template(self) -> str:
        """Template pour les intégrations"""
        return """Pour intégrer {external_service} avec {domain}, utilisez le pattern {integration_pattern}.

**Architecture d'intégration** :
```mermaid
graph LR
    A[Votre App {domain}] --> B[Bridge {integration_pattern}]
    B --> C[External Service API]
    C --> B
    B --> A
```

**Implémentation du bridge** :
```python
class {BridgeName}:
    def __init__(self, config):
        self.client = {external_service}.Client(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout
        )
        self.transformer = {domain}DataTransformer()
    
    def {main_action}({domain}_data):
        # 1. Transformer données {domain} → format externe
        external_data = self.transformer.to_external({domain}_data)
        
        # 2. Appeler l'API externe
        try:
            response = self.client.{api_method}(external_data)
        except {external_service}Error as e:
            logger.error(f"Erreur {external_service}: {{e}}")
            raise {domain}IntegrationError(f"Échec intégration {external_service}")
        
        # 3. Transformer réponse externe → format {domain}
        return self.transformer.from_external(response)
```

**Configuration requise** :
```yaml
# config/integration.yaml
external_service:
  api_key: "${{EXTERNAL_API_KEY}}"
  base_url: "https://api.{external_service}.com/v1"
  timeout: 30
  retry_attempts: 3
```

**Sécurité - Gestion des clés API** :
```python
# 🔐 Jamais de clés en dur
class SecureConfig:
    def __init__(self):
        self.api_key = os.getenv("EXTERNAL_API_KEY")
        if not self.api_key:
            raise ValueError("EXTERNAL_API_KEY requis")
```

**Cas d'usage pratique** :
```python
# Utilisation dans votre application {domain}
config = SecureConfig()
bridge = {BridgeName}(config)
result = bridge.{main_action}({domain}_data)
```

**Monitoring et logging** :
```python
@metrics.counter("external_service_requests_total")
def monitored_bridge_call(self, data):
    start_time = time.time()
    try:
        result = self.{main_action}(data)
        metrics.counter("external_service_success_total").inc()
        return result
    except Exception as e:
        metrics.counter("external_service_error_total").inc()
        raise
    finally:
        metrics.histogram("request_duration").observe(time.time() - start_time)
```"""
    
    def _get_best_practices_template(self) -> str:
        """Template pour les best practices"""
        return """Pour {security_topic} dans {domain}, suivez ces best practices éprouvées.

❌ **Approches dangereuses à éviter** :
```python
# 🚨 JAMAIS FAIRE ÇA
API_KEY = "sk-1234567890abcdef"  # Secret en dur
password = "password123"  # Mot de passe en clair
```

✅ **Approche sécurisée recommandée** :
```python
import os
from cryptography.fernet import Fernet

class {domain}SecurityManager:
    def __init__(self):
        self.master_key = self._load_master_key()
        self.cipher = Fernet(self.master_key)
    
    def _load_master_key(self) -> bytes:
        key = os.getenv("{domain.upper()}_MASTER_KEY")
        if not key:
            raise ValueError("{domain.upper()}_MASTER_KEY requis")
        return key.encode()
    
    def encrypt_sensitive_data(self, data: str) -> str:
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted.decode()
    
    def get_api_key(self, service: str) -> str:
        encrypted_key = os.getenv(f"{{service.upper()}}_API_KEY")
        if not encrypted_key:
            raise ValueError(f"{{service.upper()}}_API_KEY non configuré")
        
        return self.decrypt_sensitive_data(encrypted_key)
```

**🔐 Configuration sécurisée** :
```yaml
# config/security.yaml
security:
  encryption:
    algorithm: "AES-256-GCM"
    key_rotation_days: 90
  api_keys:
    storage: "encrypted_env_vars"
    rotation_days: 30
    audit_log: true
```

**Variables d'environnement sécurisées** :
```bash
# .env.template (jamais commiter les vraies valeurs)
{domain.upper()}_MASTER_KEY=votre_clé_maître_ici
EXTERNAL_SERVICE_API_KEY=clé_chiffrée_ici
```

**🛡️ Validation d'entrée** :
```python
import re
from pydantic import BaseModel, validator

class SecureInput(BaseModel):
    data: str
    user_id: str
    
    @validator('data')
    def validate_data(cls, v):
        if any(pattern in v.lower() for pattern in ['<script', 'javascript:', 'sql:']):
            raise ValueError('Contenu potentiellement dangereux détecté')
        return v
```

**🔍 Audit et monitoring** :
```python
class SecurityAuditor:
    def __init__(self):
        self.logger = logging.getLogger('{domain}_security')
    
    def log_access(self, user_id: str, resource: str, action: str, success: bool):
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"ACCESS: {{user_id}} -> {{resource}} [{{action}}] = {{status}}")
    
    def log_security_event(self, event_type: str, details: dict):
        self.logger.warning(f"SECURITY: {{event_type}} - {{details}}")
```

**🎯 Golden Rule {domain}** :
**Zero Trust, Verify Always** : Ne faites confiance à aucune entrée, aucune connexion. Vérifiez toujours tout, chiffrez tout, et supposez que le système est déjà compromis."""
    
    def generate_dataset(self, output_path: str, count: int = 100) -> None:
        """Génère le dataset complet"""
        self.logger.info(f"🚀 Génération dataset de {count} exemples pour {self.config.domain}")
        
        dataset = []
        
        # Générer exemples par catégorie selon distribution 40/35/15/10
        for category, config in self.config.categories.items():
            category_count = config["count"]
            self.logger.info(f"📝 Génération {category_count} exemples pour {category}")
            
            for i in range(category_count):
                example = self._generate_example(category, i)
                dataset.append(example)
        
        # Mélanger le dataset
        random.shuffle(dataset)
        
        # Sauvegarder
        self._save_dataset(dataset, output_path)
        
        self.logger.info(f"✅ Dataset généré : {len(dataset)} exemples dans {output_path}")
    
    def _generate_example(self, category: str, index: int) -> Dict[str, Any]:
        """Génère un exemple spécifique"""
        templates = self.example_templates[category]
        template = random.choice(templates)
        
        # Adapter le template au domaine
        user_question = self._adapt_user_template(template["user_template"])
        assistant_response = self._adapt_response_template(template["response_template"])
        
        return {
            "messages": [
                {"role": "system", "content": self.system_prompt_template},
                {"role": "user", "content": user_question},
                {"role": "assistant", "content": assistant_response}
            ]
        }
    
    def _adapt_user_template(self, template: str) -> str:
        """Adapte le template utilisateur au domaine"""
        replacements = {
            "{domain}": self.config.domain,
            "{pattern_problem}": random.choice(self.config.patterns) if self.config.patterns else "pattern problem",
            "{component_a}": random.choice(self.config.concepts) if self.config.concepts else "component A",
            "{component_b}": random.choice(self.config.concepts) if self.config.concepts else "component B",
            "{action}": random.choice(self.config.commands) if self.config.commands else "specific action",
            "{error_message}": random.choice(self.config.errors) if self.config.errors else "Error: Something went wrong",
            "{external_service}": random.choice(self.config.integrations) if self.config.integrations else "External Service",
            "{security_topic}": "sécurité des données"
        }
        
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        
        return result
    
    def _adapt_response_template(self, template: str) -> str:
        """Adapte le template de réponse au domaine"""
        # Remplacements génériques
        replacements = {
            "{domain}": self.config.domain,
            "{PatternName}": "SpecificPattern",
            "{pattern_name}": "specific_pattern",
            "{pattern_problem}": "pattern problem",
            "{BridgeName}": f"{self.config.domain.title()}Bridge",
            "{integration_pattern}": "BridgePattern",
            "{external_service}": random.choice(self.config.integrations) if self.config.integrations else "ExternalService",
            "{main_action}": "process_data",
            "{api_method}": "api_call"
        }
        
        # Remplacements spécifiques au domaine
        if self.config.key_tools:
            replacements["{tool1}"] = self.config.key_tools[0]
            replacements["{tool2}"] = self.config.key_tools[1] if len(self.config.key_tools) > 1 else "tool2"
        
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        
        return result
    
    def _save_dataset(self, dataset: List[Dict], output_path: str) -> None:
        """Sauvegarde le dataset en JSONL"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in dataset:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')

def main():
    parser = argparse.ArgumentParser(description="Generate dataset for fine-tuning")
    parser.add_argument("--domain_analysis", required=True, help="Domain analysis JSON file")
    parser.add_argument("--output", default="dataset.jsonl", help="Output dataset file")
    parser.add_argument("--count", type=int, default=100, help="Number of examples to generate")
    
    args = parser.parse_args()
    
    # Validation
    if not Path(args.domain_analysis).exists():
        print(f"❌ Erreur: Le fichier {args.domain_analysis} n'existe pas")
        return 1
    
    # Génération
    generator = UniversalDatasetGenerator(args.domain_analysis)
    generator.generate_dataset(args.output, args.count)
    
    return 0

if __name__ == "__main__":
    exit(main())
