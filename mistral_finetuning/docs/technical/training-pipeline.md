# Training Pipeline for Mistral Fine-Tuning

**TL;DR**: Pipeline complet d'entraînement avec validation croisée, monitoring automatique et déploiement orchestré via les scripts Python du projet.

Vous avez un dataset de 100 exemples techniques, mais lancer l'entraînement Mistral sans monitoring ni validation vous fait risquer des heures de calcul pour un modèle qui overfit sur 3 exemples. C'est le "Training Black Hole" - des jobs qui tournent sans visibilité.

## 🔄 Pipeline Complet

### Étape 1 : Préparation Dataset

```bash
# Validation format JSONL
python scripts/validate_dataset.py \
  --input mistral_finetuning/dataset/workflow_mediapipe_train.jsonl \
  --output mistral_finetuning/prepared_dataset/validated.jsonl

# Split train/validation (90/10)
python scripts/split_dataset.py \
  --input mistral_finetuning/prepared_dataset/validated.jsonl \
  --train mistral_finetuning/prepared_dataset/train.jsonl \
  --val mistral_finetuning/prepared_dataset/val.jsonl \
  --ratio 0.9
```

### Étape 2 : Configuration Entraînement

```python
# config/training_config.py
TRAINING_CONFIG = {
    "model": "mistral-small-latest",
    "dataset": {
        "train_file": "mistral_finetuning/prepared_dataset/train.jsonl",
        "val_file": "mistral_finetuning/prepared_dataset/val.jsonl"
    },
    "training": {
        "learning_rate": 2e-5,
        "batch_size": 4,
        "epochs": 3,
        "warmup_steps": 100,
        "weight_decay": 0.01
    },
    "evaluation": {
        "eval_steps": 50,
        "save_steps": 100,
        "early_stopping_patience": 3
    }
}
```

### Étape 3 : Lancement Entraînement

```bash
# Entraînement avec monitoring
python scripts/train_model.py \
  --config config/training_config.py \
  --output_dir mistral_finetuning/models/ \
  --monitor \
  --checkpoint_every 100
```

## 📊 Monitoring et Validation

### Métriques Suivies

```python
# scripts/monitor_training.py
class TrainingMonitor:
    def __init__(self):
        self.metrics = {
            "train_loss": [],
            "val_loss": [],
            "accuracy": [],
            "f1_score": [],
            "bleu_score": []
        }
    
    def log_step(self, step, train_loss, val_loss, metrics):
        self.metrics["train_loss"].append(train_loss)
        self.metrics["val_loss"].append(val_loss)
        
        # Détection overfitting
        if len(self.metrics["val_loss"]) > 10:
            recent_val = self.metrics["val_loss"][-5:]
            if all(x > recent_val[0] for x in recent_val[1:]):
                logger.warning("⚠️  Overfitting détecté!")
```

### Validation Croisée

```python
# scripts/cross_validate.py
def cross_validate(dataset, k_folds=5):
    fold_size = len(dataset) // k_folds
    results = []
    
    for fold in range(k_folds):
        val_start = fold * fold_size
        val_end = (fold + 1) * fold_size
        
        train_data = dataset[:val_start] + dataset[val_end:]
        val_data = dataset[val_start:val_end]
        
        # Entraînement sur ce fold
        model = train_fold(train_data)
        metrics = evaluate_model(model, val_data)
        results.append(metrics)
    
    return aggregate_results(results)
```

## 🚀 Déploiement

### Export Modèle

```bash
# Export pour production
python scripts/export_model.py \
  --model_path mistral_finetuning/models/best_model \
  --export_path mistral_finetuning/production/workflow_mediapipe_v1 \
  --format onnx
```

### Test Production

```python
# scripts/test_production.py
def test_production_model():
    model = load_production_model("workflow_mediapipe_v1")
    
    test_cases = [
        {
            "question": "Comment exécuter STEP5 MediaPipe CPU?",
            "expected_keywords": ["tracking_env_slim", "mediapipe", "TRACKING_DISABLE_GPU=1"]
        },
        {
            "question": "Quelle commande pour STEP4 audio analysis?",
            "expected_keywords": ["audio_env", "lemonfox", "ffmpeg"]
        }
    ]
    
    for case in test_cases:
        response = model.generate(case["question"])
        assert all(keyword in response for keyword in case["expected_keywords"])
        logger.info(f"✅ Test passed: {case['question']}")
```

## 🛠️ Scripts du Projet

### Structure Scripts

```
mistral_finetuning/
├── scripts/
│   ├── train_model.py          # Script principal d'entraînement
│   ├── test_model.py           # Tests unitaires modèle
│   ├── validate_dataset.py     # Validation format JSONL
│   ├── split_dataset.py        # Split train/validation
│   ├── monitor_training.py     # Monitoring temps réel
│   ├── cross_validate.py       # Validation croisée
│   ├── export_model.py         # Export production
│   └── test_production.py      # Tests production
├── config/
│   ├── training_config.py      # Configuration entraînement
│   └── model_config.py         # Configuration modèle
└── data/
    ├── raw/                     # Données brutes
    ├── prepared/                # Données préparées
    └── models/                  # Modèles entraînés
```

### Script Principal : train_model.py

```python
#!/usr/bin/env python3
"""
Script principal d'entraînement pour Mistral fine-tuning
"""

import argparse
import json
import logging
from pathlib import Path

from mistralai.client import MistralClient
from scripts.monitor_training import TrainingMonitor
from scripts.validate_dataset import validate_jsonl

def main():
    parser = argparse.ArgumentParser(description="Entraînement Mistral workflow_mediapipe")
    parser.add_argument("--config", required=True, help="Configuration file")
    parser.add_argument("--output_dir", required=True, help="Output directory")
    parser.add_argument("--monitor", action="store_true", help="Enable monitoring")
    parser.add_argument("--checkpoint_every", type=int, default=100, help="Checkpoint frequency")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(f"{args.output_dir}/training.log"),
            logging.StreamHandler()
        ]
    )
    
    # Load configuration
    with open(args.config) as f:
        config = json.load(f)
    
    # Validate dataset
    validate_jsonl(config["dataset"]["train_file"])
    validate_jsonl(config["dataset"]["val_file"])
    
    # Initialize monitoring
    monitor = TrainingMonitor() if args.monitor else None
    
    # Start training
    logger.info(f"🚀 Démarrage entraînement avec {config['model']}")
    
    try:
        # Training loop here
        pass
    except Exception as e:
        logger.error(f"❌ Erreur entraînement: {e}")
        raise

if __name__ == "__main__":
    main()
```

## 📈 Performance et Optimisation

### GPU Requirements

| Taille Dataset | VRAM Requis | Temps Estimé |
|----------------|-------------|--------------|
| 100 exemples   | 8 GB        | 30-45 min    |
| 500 exemples   | 16 GB       | 2-3 heures   |
| 1000 exemples  | 24 GB       | 4-6 heures   |

### Optimisations

```python
# Optimisation mémoire
training_config = {
    "gradient_accumulation_steps": 4,  # Simuler batch plus grand
    "fp16": True,                      # Mixed precision
    "gradient_checkpointing": True,    # Économie mémoire
    "dataloader_num_workers": 4        # Parallélisme
}
```

## 🎯 Golden Rule

**Monitor before you train** : Toujours valider le dataset, configurer le monitoring et tester sur un petit sous-ensemble avant de lancer un entraînement complet. Une heure de préparation évite 10 heures de calcul inutile.

---

*Voir [Dataset Strategy](dataset-strategy.md) pour la préparation des données et [Model Evaluation](../guides/model-evaluation.md) pour les métriques de validation.*
