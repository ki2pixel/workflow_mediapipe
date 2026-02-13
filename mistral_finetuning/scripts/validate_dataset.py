#!/usr/bin/env python3
"""
Script de validation du dataset pour fine-tuning Mistral
- Vérification format JSONL
- Validation structure messages
- Contrôle longueur tokens
- Détection de duplicatas
"""

import json
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Set
import sys

class DatasetValidator:
    def __init__(self, dataset_dir: str):
        self.dataset_dir = Path(dataset_dir)
        self.max_token_length = 32000  # Limite Mistral pour fine-tuning
        self.approx_chars_per_token = 4  # Approximation

    def validate_jsonl_files(self) -> Dict[str, Any]:
        """Valide tous les fichiers JSONL du dataset"""
        results = {
            "files_validated": [],
            "total_examples": 0,
            "valid_examples": 0,
            "invalid_examples": 0,
            "errors": [],
            "duplicates": [],
            "warnings": []
        }

        # Chercher tous les fichiers .jsonl
        jsonl_files = list(self.dataset_dir.glob("*.jsonl"))
        print(f"Trouvé {len(jsonl_files)} fichiers JSONL")

        all_examples = []
        seen_hashes = set()

        for jsonl_file in jsonl_files:
            print(f"\nValidation de {jsonl_file.name}...")
            file_results = self._validate_single_file(jsonl_file)

            results["files_validated"].append({
                "filename": jsonl_file.name,
                "examples": file_results["examples"],
                "valid": file_results["valid"],
                "invalid": file_results["invalid"]
            })

            results["total_examples"] += file_results["examples"]
            results["valid_examples"] += file_results["valid"]
            results["invalid_examples"] += file_results["invalid"]
            results["errors"].extend(file_results["errors"])
            results["warnings"].extend(file_results["warnings"])

            # Collecter pour détection de duplicatas
            for example in file_results["examples_list"]:
                example_hash = self._hash_example(example)
                if example_hash in seen_hashes:
                    results["duplicates"].append({
                        "file": jsonl_file.name,
                        "hash": example_hash,
                        "content_preview": example["messages"][1]["content"][:100] if len(example["messages"]) > 1 else "N/A"
                    })
                else:
                    seen_hashes.add(example_hash)
                all_examples.append(example)

        # Statistiques finales
        results["duplicate_count"] = len(results["duplicates"])
        results["validity_rate"] = results["valid_examples"] / results["total_examples"] if results["total_examples"] > 0 else 0

        return results

    def _validate_single_file(self, file_path: Path) -> Dict[str, Any]:
        """Valide un fichier JSONL individuel"""
        results = {
            "examples": 0,
            "valid": 0,
            "invalid": 0,
            "errors": [],
            "warnings": [],
            "examples_list": []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    results["examples"] += 1

                    try:
                        example = json.loads(line)
                        results["examples_list"].append(example)

                        if self._validate_example(example, line_num, file_path.name):
                            results["valid"] += 1
                        else:
                            results["invalid"] += 1

                    except json.JSONDecodeError as e:
                        error_msg = f"Ligne {line_num} dans {file_path.name}: Erreur JSON - {e}"
                        results["errors"].append(error_msg)
                        results["invalid"] += 1
                        print(f"❌ {error_msg}")

        except FileNotFoundError:
            results["errors"].append(f"Fichier non trouvé: {file_path}")
        except Exception as e:
            results["errors"].append(f"Erreur lors de la lecture de {file_path}: {e}")

        return results

    def _validate_example(self, example: Dict[str, Any], line_num: int, filename: str) -> bool:
        """Valide un exemple individuel"""
        is_valid = True

        # 1. Structure de base
        if "messages" not in example:
            self._add_error(f"Ligne {line_num} ({filename}): Clé 'messages' manquante", filename)
            return False

        messages = example["messages"]
        if not isinstance(messages, list) or len(messages) < 2:
            self._add_error(f"Ligne {line_num} ({filename}): 'messages' doit être une liste avec au moins 2 éléments", filename)
            return False

        # 2. Validation des messages
        expected_roles = ["system", "user", "assistant"]
        seen_roles = set()

        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                self._add_error(f"Ligne {line_num} ({filename}): Message {i} n'est pas un objet", filename)
                is_valid = False
                continue

            # Rôles
            if "role" not in msg:
                self._add_error(f"Ligne {line_num} ({filename}): Message {i} sans rôle", filename)
                is_valid = False
                continue

            role = msg["role"]
            if role not in expected_roles:
                self._add_error(f"Ligne {line_num} ({filename}): Rôle invalide '{role}' (attendu: {expected_roles})", filename)
                is_valid = False

            if role in seen_roles:
                self._add_warning(f"Ligne {line_num} ({filename}): Rôle '{role}' dupliqué", filename)
            seen_roles.add(role)

            # Contenu
            if "content" not in msg:
                self._add_error(f"Ligne {line_num} ({filename}): Message {i} sans contenu", filename)
                is_valid = False
                continue

            content = msg["content"]
            if not isinstance(content, str) or not content.strip():
                self._add_error(f"Ligne {line_num} ({filename}): Message {i} a un contenu vide", filename)
                is_valid = False

            # Longueur
            content_length = len(content)
            estimated_tokens = content_length / self.approx_chars_per_token
            if estimated_tokens > self.max_token_length:
                self._add_error(f"Ligne {line_num} ({filename}): Message {i} trop long ({estimated_tokens:.0f} tokens > {self.max_token_length})", filename)
                is_valid = False

        # 3. Structure conversation
        if "system" not in seen_roles:
            self._add_error(f"Ligne {line_num} ({filename}): Message système manquant", filename)
            is_valid = False

        if "user" not in seen_roles:
            self._add_error(f"Ligne {line_num} ({filename}): Message utilisateur manquant", filename)
            is_valid = False

        if "assistant" not in seen_roles:
            self._add_error(f"Ligne {line_num} ({filename}): Message assistant manquant", filename)
            is_valid = False

        return is_valid

    def _add_error(self, message: str, filename: str):
        """Ajoute une erreur"""
        self.errors.append(message)
        print(f"❌ {message}")

    def _add_warning(self, message: str, filename: str):
        """Ajoute un avertissement"""
        self.warnings.append(message)
        print(f"⚠️ {message}")

    def _hash_example(self, example: Dict[str, Any]) -> str:
        """Génère un hash pour détecter les duplicatas"""
        # Simplification: hash du contenu des messages utilisateur et assistant
        content_to_hash = ""
        for msg in example.get("messages", []):
            if msg.get("role") in ["user", "assistant"]:
                content_to_hash += msg.get("content", "")

        return hashlib.md5(content_to_hash.encode('utf-8')).hexdigest()

    def generate_report(self, results: Dict[str, Any], output_file: str):
        """Génère un rapport de validation"""
        report = {
            "validation_summary": {
                "timestamp": "2026-02-12",  # À remplacer par datetime.now()
                "files_processed": len(results["files_validated"]),
                "total_examples": results["total_examples"],
                "valid_examples": results["valid_examples"],
                "invalid_examples": results["invalid_examples"],
                "validity_rate": f"{results['validity_rate']*100:.1f}%",
                "duplicates_found": results["duplicate_count"]
            },
            "files_detail": results["files_validated"],
            "errors": results["errors"][:50],  # Limiter à 50 erreurs
            "warnings": results["warnings"][:50],  # Limiter à 50 avertissements
            "duplicates": results["duplicates"][:20]  # Limiter à 20 duplicatas
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📊 Rapport sauvegardé dans {output_file}")
        return report

    def run(self, output_file: str = "validation_report.json"):
        """Exécute la validation complète"""
        print("=== Validation du Dataset ===")

        # Validation
        results = self.validate_jsonl_files()

        # Rapport
        report = self.generate_report(results, output_file)

        # Résumé
        print("""
=== RÉSULTATS ===""")
        print(f"📁 Fichiers validés: {len(results['files_validated'])}")
        print(f"📝 Exemples totaux: {results['total_examples']}")
        print(f"✅ Exemples valides: {results['valid_examples']}")
        print(f"❌ Exemples invalides: {results['invalid_examples']}")
        print(f"📊 Taux de validité: {results['validity_rate']*100:.1f}%")
        print(f"🔄 Duplicatas détectés: {results['duplicate_count']}")

        # Évaluation
        if results["valid_examples"] == results["total_examples"] and results["duplicate_count"] == 0:
            print("🎉 Dataset valide et prêt pour l'entraînement!")
            return True
        else:
            print("⚠️ Problèmes détectés - correction requise avant entraînement")
            return False


def main():
    # Configuration
    dataset_dir = "dataset"
    output_file = "validation_report.json"

    # Créer le validateur
    validator = DatasetValidator(dataset_dir)

    # Exécuter
    success = validator.run(output_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
