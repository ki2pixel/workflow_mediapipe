#!/usr/bin/env python3
"""
Script de préparation du dataset pour fine-tuning Mistral
- Collecte et validation des exemples
- Division train/validation/test
- Génération de statistiques
"""

import json
import os
import random
from pathlib import Path
from typing import List, Dict, Any
import sys

class DatasetPreparer:
    def __init__(self, dataset_dir: str):
        self.dataset_dir = Path(dataset_dir)

    def load_dataset(self) -> List[Dict[str, Any]]:
        """Charge tous les exemples du dataset depuis tous les fichiers .jsonl"""
        examples = []

        # Trouver tous les fichiers .jsonl
        jsonl_files = list(self.dataset_dir.glob("*.jsonl"))
        print(f"Trouvé {len(jsonl_files)} fichiers JSONL: {[f.name for f in jsonl_files]}")

        for jsonl_file in jsonl_files:
            print(f"Chargement de {jsonl_file.name}...")
            examples.extend(self._load_jsonl_file(jsonl_file))

        return examples

    def _load_jsonl_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Charge un fichier JSONL"""
        examples = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    example = json.loads(line)
                    examples.append(example)
                except json.JSONDecodeError as e:
                    print(f"Erreur JSON ligne {line_num} dans {file_path}: {e}")
                    continue
        return examples

    def validate_examples(self, examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Valide le format des exemples"""
        valid_examples = []
        for i, example in enumerate(examples):
            if self._validate_example(example):
                valid_examples.append(example)
            else:
                print(f"Exemple {i} invalide, ignoré")
        return valid_examples

    def _validate_example(self, example: Dict[str, Any]) -> bool:
        """Valide un exemple individuel"""
        if "messages" not in example:
            return False

        messages = example["messages"]
        if not isinstance(messages, list) or len(messages) < 2:
            return False

        # Vérifier les rôles
        roles = [msg.get("role") for msg in messages]
        if roles[0] != "system":
            return False
        if "user" not in roles or "assistant" not in roles:
            return False

        # Vérifier que chaque message a du contenu
        for msg in messages:
            if "content" not in msg or not msg["content"].strip():
                return False

        return True

    def split_dataset(self, examples: List[Dict[str, Any]], train_ratio=0.8, val_ratio=0.1) -> Dict[str, List[Dict[str, Any]]]:
        """Divise le dataset en train/validation/test"""
        random.shuffle(examples)

        n_total = len(examples)
        n_train = int(n_total * train_ratio)
        n_val = int(n_total * val_ratio)
        n_test = n_total - n_train - n_val

        return {
            "train": examples[:n_train],
            "validation": examples[n_train:n_train + n_val],
            "test": examples[n_train + n_val:]
        }

    def save_splits(self, splits: Dict[str, List[Dict[str, Any]]], output_dir: str):
        """Sauvegarde les splits dans des fichiers JSONL"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        for split_name, examples in splits.items():
            split_file = output_path / f"{split_name}.jsonl"
            with open(split_file, 'w', encoding='utf-8') as f:
                for example in examples:
                    json.dump(example, f, ensure_ascii=False)
                    f.write('\n')
            print(f"Sauvegardé {len(examples)} exemples dans {split_file}")

    def generate_statistics(self, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Génère des statistiques sur le dataset"""
        stats = {
            "total_examples": len(examples),
            "categories": {},
            "avg_message_length": 0,
            "max_message_length": 0,
            "min_message_length": float('inf')
        }

        total_length = 0
        for example in examples:
            # Estimation de la catégorie basée sur le contenu
            content = example["messages"][1]["content"] if len(example["messages"]) > 1 else ""
            category = self._categorize_example(content)

            if category not in stats["categories"]:
                stats["categories"][category] = 0
            stats["categories"][category] += 1

            # Statistiques de longueur
            length = sum(len(msg["content"]) for msg in example["messages"])
            total_length += length
            stats["max_message_length"] = max(stats["max_message_length"], length)
            stats["min_message_length"] = min(stats["min_message_length"], length)

        if examples:
            stats["avg_message_length"] = total_length / len(examples)

        return stats

    def _categorize_example(self, content: str) -> str:
        """Catégorise un exemple basé sur son contenu"""
        content_lower = content.lower()

        if any(keyword in content_lower for keyword in ["architecture", "service", "pattern", "frontend", "backend"]):
            return "architecture"
        elif any(keyword in content_lower for keyword in ["step", "pipeline", "command", "erreur", "diagnostic"]):
            return "pipeline"
        elif any(keyword in content_lower for keyword in ["after effects", "extendscript", "jsx", "ae"]):
            return "after_effects"
        elif any(keyword in content_lower for keyword in ["sécurité", "security", "best practice", "test"]):
            return "best_practices"
        else:
            return "other"

    def run(self, output_dir: str = "prepared_dataset"):
        """Exécute la préparation complète"""
        print("=== Préparation du Dataset ===")

        # 1. Charger les données
        print("\n1. Chargement des données...")
        examples = self.load_dataset()
        print(f"Chargé {len(examples)} exemples")

        # 2. Validation
        print("\n2. Validation des exemples...")
        valid_examples = self.validate_examples(examples)
        print(f"Exemples valides: {len(valid_examples)}/{len(examples)}")

        if not valid_examples:
            print("Erreur: Aucun exemple valide trouvé!")
            return False

        # 3. Statistiques
        print("\n3. Génération des statistiques...")
        stats = self.generate_statistics(valid_examples)
        print("Statistiques:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))

        # Sauvegarder les stats
        stats_file = Path(output_dir) / "dataset_stats.json"
        stats_file.parent.mkdir(exist_ok=True)
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"Statistiques sauvegardées dans {stats_file}")

        # 4. Division
        print("\n4. Division train/validation/test...")
        splits = self.split_dataset(valid_examples)
        print(f"Train: {len(splits['train'])}, Validation: {len(splits['validation'])}, Test: {len(splits['test'])}")

        # 5. Sauvegarde
        print("\n5. Sauvegarde des splits...")
        self.save_splits(splits, output_dir)

        print(f"\n✅ Préparation terminée! Fichiers dans {output_dir}")
        return True


def main():
    # Configuration
    dataset_dir = "dataset"
    output_dir = "prepared_dataset"

    # Créer le préparateur
    preparer = DatasetPreparer(dataset_dir)

    # Exécuter
    success = preparer.run(output_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
