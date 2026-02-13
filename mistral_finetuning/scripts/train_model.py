#!/usr/bin/env python3
"""
Script de lancement du fine-tuning Mistral
- Upload des fichiers dataset
- Création du job de fine-tuning
- Configuration des hyperparamètres
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
import time

try:
    from mistralai import Mistral
except ImportError:
    print("Erreur: mistralai package non installé. Installez avec: pip install mistralai")
    sys.exit(1)

class MistralFineTuner:
    def __init__(self, api_key: str):
        self.client = Mistral(api_key=api_key)
        self.uploaded_files = {}

    def upload_file(self, file_path: str, purpose: str) -> str:
        """Upload un fichier vers Mistral et retourne l'ID"""
        print(f"Upload de {file_path} (purpose: {purpose})...")

        with open(file_path, 'rb') as f:
            file_obj = self.client.files.upload(
                file={
                    "file_name": os.path.basename(file_path),
                    "content": f
                },
                purpose=purpose
            )

        file_id = file_obj.id
        self.uploaded_files[purpose] = file_id
        print(f"✅ Fichier uploadé: {file_id}")
        return file_id

    def create_finetuning_job(self,
                            training_file_id: str,
                            validation_file_id: str = None,
                            model: str = "open-mistral-7b",
                            training_steps: int = 100,
                            learning_rate: float = 1e-4,
                            batch_size: int = 1) -> Dict[str, Any]:
        """Crée un job de fine-tuning"""
        print("Création du job de fine-tuning...")
        print(f"Modèle: {model}")
        print(f"Training file: {training_file_id}")
        print(f"Validation file: {validation_file_id}")

        # Préparation des fichiers
        training_files = [{"file_id": training_file_id, "weight": 1}]
        validation_files = [validation_file_id] if validation_file_id else None

        # Hyperparamètres
        hyperparameters = {
            "training_steps": training_steps,
            "learning_rate": learning_rate
        }
        print(f"Hyperparamètres: {hyperparameters}")

        # Création du job
        job = self.client.fine_tuning.jobs.create(
            model=model,
            training_files=training_files,
            validation_files=validation_files,
            hyperparameters=hyperparameters,
            auto_start=False
        )

        print(f"✅ Job créé: {job.id}")
        print(f"Status: {job.status}")

        return {
            "job_id": job.id,
            "status": job.status,
            "model": model,
            "training_file": training_file_id,
            "validation_file": validation_file_id,
            "hyperparameters": hyperparameters
        }

    def monitor_job(self, job_id: str, interval: int = 30) -> None:
        """Surveille le statut du job"""
        print(f"Monitoring du job {job_id} (intervalle: {interval}s)...")

        while True:
            job = self.client.fine_tuning.jobs.get(job_id)
            print(f"[{time.strftime('%H:%M:%S')}] Status: {job.status}")

            if hasattr(job, 'progress'):
                print(f"Progress: {job.progress}")

            if job.status in ['COMPLETED', 'FAILED', 'CANCELLED']:
                print(f"Job terminé avec status: {job.status}")
                if hasattr(job, 'fine_tuned_model'):
                    print(f"Modèle fine-tuné: {job.fine_tuned_model}")
                break

            time.sleep(interval)

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Récupère le statut d'un job"""
        job = self.client.fine_tuning.jobs.get(job_id)
        return {
            "job_id": job.id,
            "status": job.status,
            "created_at": getattr(job, 'created_at', None),
            "finished_at": getattr(job, 'finished_at', None),
            "fine_tuned_model": getattr(job, 'fine_tuned_model', None),
            "progress": getattr(job, 'progress', None)
        }


def main():
    # Configuration
    prepared_dataset_dir = "prepared_dataset"
    api_key = os.getenv("MISTRAL_API_KEY")

    if not api_key:
        print("Erreur: MISTRAL_API_KEY non défini dans les variables d'environnement")
        print("Définissez-le avec: export MISTRAL_API_KEY=votre_clé_api")
        sys.exit(1)

    # Fichiers à uploader
    train_file = os.path.join(prepared_dataset_dir, "train.jsonl")
    validation_file = os.path.join(prepared_dataset_dir, "validation.jsonl")

    if not os.path.exists(train_file):
        print(f"Erreur: Fichier d'entraînement non trouvé: {train_file}")
        sys.exit(1)

    # Initialisation
    tuner = MistralFineTuner(api_key)

    try:
        # Upload des fichiers
        print("=== UPLOAD DES FICHIERS ===")
        training_file_id = tuner.upload_file(train_file, "fine-tune")

        validation_file_id = None
        if os.path.exists(validation_file):
            validation_file_id = tuner.upload_file(validation_file, "fine-tune")

        # Création du job
        print("\n=== CRÉATION DU JOB ===")
        job_info = tuner.create_finetuning_job(
            training_file_id=training_file_id,
            validation_file_id=validation_file_id,
            model="mistral-small-latest",
            training_steps=25,  # ~0.25 epoch pour 103 exemples
            learning_rate=1e-4,
            batch_size=1
        )

        print("\n=== JOB INFO ===")
        for key, value in job_info.items():
            print(f"{key}: {value}")

        # Sauvegarde des infos du job
        with open("finetuning_job.json", "w") as f:
            import json
            json.dump(job_info, f, indent=2)

        print("Infos du job sauvegardées dans finetuning_job.json")

    except Exception as e:
        print(f"Erreur lors du fine-tuning: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
