#!/usr/bin/env python3
"""
Universal Domain Analyzer for Fine-Tuning

Adaptable script to analyze any technical domain for LLM fine-tuning.
Scans documentation, code, and configuration files to extract domain expertise.

Usage:
    python analyze_domain.py --project_path . --domain "[DOMAIN]" --output domain_analysis.json
"""

import os
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import logging

# Configuration adaptable par domaine
DOMAIN_CONFIGS = {
    "software_engineering": {
        "file_extensions": [".py", ".js", ".ts", ".java", ".cpp", ".go", ".rs"],
        "doc_extensions": [".md", ".rst", ".txt"],
        "config_extensions": [".yaml", ".yml", ".json", ".toml", ".ini"],
        "keywords": ["class", "interface", "api", "endpoint", "service", "pattern", "architecture"],
        "command_patterns": [r"npm\s+\w+", r"python\s+\w+", r"docker\s+\w+", r"git\s+\w+"],
        "error_patterns": [r"Error:", r"Exception:", r"Failed to", r"Cannot"]
    },
    "data_science": {
        "file_extensions": [".py", ".ipynb", ".r", ".sql"],
        "doc_extensions": [".md", ".rst", ".txt"],
        "config_extensions": [".yaml", ".yml", ".json"],
        "keywords": ["model", "training", "feature", "pipeline", "dataset", "algorithm", "ml"],
        "command_patterns": [r"pip\s+install", r"conda\s+\w+", r"jupyter\s+\w+", r"pandas\."],
        "error_patterns": [r"ValueError", r"KeyError", r"ImportError", r"MemoryError"]
    },
    "devops": {
        "file_extensions": [".sh", ".py", ".yaml", ".yml", ".json", ".tf", ".hcl"],
        "doc_extensions": [".md", ".rst", ".txt"],
        "config_extensions": [".yaml", ".yml", ".json", ".toml", ".conf"],
        "keywords": ["docker", "kubernetes", "terraform", "ansible", "ci/cd", "deploy", "monitor"],
        "command_patterns": [r"docker\s+\w+", r"kubectl\s+\w+", r"terraform\s+\w+", r"ansible\s+\w+"],
        "error_patterns": [r"deployment\s+failed", r"pod\s+error", r"timeout", r"permission\s+denied"]
    },
    "default": {
        "file_extensions": [".py", ".js", ".ts", ".java", ".cpp", ".go", ".rs", ".sh"],
        "doc_extensions": [".md", ".rst", ".txt", ".doc"],
        "config_extensions": [".yaml", ".yml", ".json", ".toml", ".ini", ".conf"],
        "keywords": ["service", "api", "config", "deploy", "test", "build"],
        "command_patterns": [r"\w+\s+\w+", r"\.\w+", r"make\s+\w+"],
        "error_patterns": [r"error", r"failed", r"exception", r"cannot"]
    }
}

@dataclass
class DomainAnalysis:
    """Structure pour l'analyse de domaine"""
    domain: str
    project_path: str
    total_files: int
    categories: Dict[str, Any]
    concepts: List[str]
    tools: List[str]
    patterns: List[str]
    commands: List[str]
    errors: List[str]
    integrations: List[str]
    file_stats: Dict[str, int]

class UniversalDomainAnalyzer:
    """Analyseur de domaine universel et adaptable"""
    
    def __init__(self, project_path: str, domain: str):
        self.project_path = Path(project_path)
        self.domain = domain.lower()
        self.config = DOMAIN_CONFIGS.get(self.domain, DOMAIN_CONFIGS["default"])
        
        # Logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Analyse data
        self.concepts: Set[str] = set()
        self.tools: Set[str] = set()
        self.patterns: Set[str] = set()
        self.commands: Set[str] = set()
        self.errors: Set[str] = set()
        self.integrations: Set[str] = set()
        self.file_stats = defaultdict(int)
    
    def analyze(self) -> DomainAnalysis:
        """Lance l'analyse complète du domaine"""
        self.logger.info(f"🔍 Analyse du domaine '{self.domain}' dans {self.project_path}")
        
        # 1. Scanner les fichiers
        self._scan_files()
        
        # 2. Analyser la documentation
        self._analyze_documentation()
        
        # 3. Analyser le code source
        self._analyze_source_code()
        
        # 4. Analyser les configurations
        self._analyze_configurations()
        
        # 5. Détecter les intégrations
        self._detect_integrations()
        
        # 6. Générer les catégories 40/35/15/10
        categories = self._generate_categories()
        
        return DomainAnalysis(
            domain=self.domain,
            project_path=str(self.project_path),
            total_files=sum(self.file_stats.values()),
            categories=categories,
            concepts=list(self.concepts),
            tools=list(self.tools),
            patterns=list(self.patterns),
            commands=list(self.commands),
            errors=list(self.errors),
            integrations=list(self.integrations),
            file_stats=dict(self.file_stats)
        )
    
    def _scan_files(self):
        """Scan tous les fichiers du projet"""
        self.logger.info("📁 Scan des fichiers...")
        
        all_extensions = (self.config["file_extensions"] + 
                         self.config["doc_extensions"] + 
                         self.config["config_extensions"])
        
        for file_path in self.project_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in all_extensions:
                self.file_stats[file_path.suffix] += 1
        
        self.logger.info(f"📊 {sum(self.file_stats.values())} fichiers trouvés")
    
    def _analyze_documentation(self):
        """Analyse la documentation pour extraire les concepts"""
        self.logger.info("📖 Analyse documentation...")
        
        for ext in self.config["doc_extensions"]:
            for file_path in self.project_path.rglob(f"*{ext}"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    self._extract_concepts_from_text(content)
                    self._extract_commands_from_text(content)
                    
                except Exception as e:
                    self.logger.warning(f"Erreur lecture {file_path}: {e}")
    
    def _analyze_source_code(self):
        """Analyse le code source pour extraire patterns et outils"""
        self.logger.info("💻 Analyse code source...")
        
        for ext in self.config["file_extensions"]:
            for file_path in self.project_path.rglob(f"*{ext}"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    self._extract_patterns_from_code(content)
                    self._extract_tools_from_code(content)
                    self._extract_errors_from_code(content)
                    
                except Exception as e:
                    self.logger.warning(f"Erreur lecture {file_path}: {e}")
    
    def _analyze_configurations(self):
        """Analyse les fichiers de configuration"""
        self.logger.info("⚙️ Analyse configurations...")
        
        for ext in self.config["config_extensions"]:
            for file_path in self.project_path.rglob(f"*{ext}"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    self._extract_tools_from_config(content)
                    
                except Exception as e:
                    self.logger.warning(f"Erreur lecture {file_path}: {e}")
    
    def _detect_integrations(self):
        """Détecte les intégrations et services externes"""
        self.logger.info("🔗 Détection intégrations...")
        
        # Patterns d'intégration courants
        integration_patterns = [
            r"api\.\w+",
            r"import\s+\w+",
            r"from\s+\w+\s+import",
            r"https?://\w+",
            r"@\w+",  # Décorateurs
            r"docker\s+pull",
            r"npm\s+install",
            r"pip\s+install"
        ]
        
        all_files = list(self.project_path.rglob("*"))
        for file_path in all_files:
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.yaml', '.yml', '.json']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for pattern in integration_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        self.integrations.update(matches)
                        
                except Exception:
                    continue  # Ignorer les erreurs de lecture
    
    def _extract_concepts_from_text(self, text: str):
        """Extrait les concepts du texte"""
        # Keywords du domaine
        for keyword in self.config["keywords"]:
            if keyword.lower() in text.lower():
                self.concepts.add(keyword)
        
        # Patterns de concepts (architecture, design, etc.)
        concept_patterns = [
            r"\w+\s+pattern",
            r"\w+\s+architecture",
            r"\w+\s+design",
            r"\w+\s+framework",
            r"\w+\s+library"
        ]
        
        for pattern in concept_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            self.concepts.update(matches)
    
    def _extract_commands_from_text(self, text: str):
        """Extrait les commandes du texte"""
        for pattern in self.config["command_patterns"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            self.commands.update(matches)
    
    def _extract_patterns_from_code(self, code: str):
        """Extrait les patterns du code"""
        # Patterns de code courants
        code_patterns = [
            r"class\s+\w+",
            r"def\s+\w+",
            r"interface\s+\w+",
            r"function\s+\w+",
            r"async\s+def\s+\w+",
            r"@\w+",  # Décorateurs
        ]
        
        for pattern in code_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            self.patterns.update(matches)
    
    def _extract_tools_from_code(self, code: str):
        """Extrait les outils/librairies du code"""
        # Import statements
        import_patterns = [
            r"import\s+(\w+)",
            r"from\s+(\w+)",
            r"require\s*\(['\"](\w+)",
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            self.tools.update(matches)
    
    def _extract_errors_from_code(self, code: str):
        """Extrait les erreurs et exceptions du code"""
        for pattern in self.config["error_patterns"]:
            matches = re.findall(pattern, code, re.IGNORECASE)
            self.errors.update(matches)
    
    def _extract_tools_from_config(self, config: str):
        """Extrait les outils des configurations"""
        # Services et outils dans les configs
        config_patterns = [
            r"image:\s*\w+",
            r"service:\s*\w+",
            r"dependency:\s*\w+",
            r"package:\s*\w+"
        ]
        
        for pattern in config_patterns:
            matches = re.findall(pattern, config, re.IGNORECASE)
            self.tools.update(matches)
    
    def _generate_categories(self) -> Dict[str, Any]:
        """Génère les catégories 40/35/15/10 basées sur l'analyse"""
        
        # Distribution 40/35/15/10
        total_examples = 100
        
        categories = {
            "architecture": {
                "count": 40,
                "focus": "Concepts, patterns, design decisions",
                "sources": ["documentation", "architecture docs"],
                "examples": list(self.concepts)[:10] if self.concepts else ["concept1", "concept2"]
            },
            "operations": {
                "count": 35,
                "focus": "Commands, workflows, troubleshooting",
                "sources": ["scripts", "cli tools", "error logs"],
                "examples": list(self.commands)[:10] if self.commands else ["command1", "command2"]
            },
            "integration": {
                "count": 15,
                "focus": "APIs, external services, bridges",
                "sources": ["api docs", "integration guides"],
                "examples": list(self.integrations)[:5] if self.integrations else ["service1", "service2"]
            },
            "best_practices": {
                "count": 10,
                "focus": "Security, quality, standards",
                "sources": ["security docs", "coding standards"],
                "examples": list(self.errors)[:5] if self.errors else ["error1", "error2"]
            }
        }
        
        return categories
    
    def save_analysis(self, analysis: DomainAnalysis, output_path: str):
        """Sauvegarde l'analyse en JSON"""
        self.logger.info(f"💾 Sauvegarde analyse dans {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(analysis), f, indent=2, ensure_ascii=False)
        
        self.logger.info("✅ Analyse sauvegardée avec succès")

def main():
    parser = argparse.ArgumentParser(description="Analyze domain for fine-tuning")
    parser.add_argument("--project_path", required=True, help="Path to project directory")
    parser.add_argument("--domain", required=True, help="Domain name (software_engineering, data_science, devops, etc.)")
    parser.add_argument("--output", default="domain_analysis.json", help="Output JSON file")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validation
    if not Path(args.project_path).exists():
        print(f"❌ Erreur: Le chemin {args.project_path} n'existe pas")
        return 1
    
    # Analyse
    analyzer = UniversalDomainAnalyzer(args.project_path, args.domain)
    analysis = analyzer.analyze()
    
    # Affichage résumé
    print(f"\n🎯 Analyse du domaine '{analysis.domain}'")
    print(f"📁 Chemin: {analysis.project_path}")
    print(f"📊 Fichiers analysés: {analysis.total_files}")
    print(f"🧠 Concepts trouvés: {len(analysis.concepts)}")
    print(f"🔧 Outils identifiés: {len(analysis.tools)}")
    print(f"🔄 Patterns détectés: {len(analysis.patterns)}")
    print(f"⚡ Commandes trouvées: {len(analysis.commands)}")
    print(f"❌ Erreurs répertoriées: {len(analysis.errors)}")
    print(f"🔗 Intégrations: {len(analysis.integrations)}")
    
    # Sauvegarde
    analyzer.save_analysis(analysis, args.output)
    
    print(f"\n✅ Analyse terminée ! Utilisez '{args.output}' pour la génération du dataset.")
    return 0

if __name__ == "__main__":
    exit(main())
