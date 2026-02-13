#!/usr/bin/env python3
"""
Script de régénération du dataset pipeline_operations_batch.jsonl
à partir des titres documentés
"""

import json
import os
from pathlib import Path

def generate_pipeline_examples():
    """Génère les 35 exemples pipeline operations"""

    system_prompt = "Tu es un expert du pipeline workflow_mediapipe, un système de post-production vidéo en 8 étapes pour After Effects. Tu maîtrises l'architecture Flask + Python, les 5 environnements virtuels isolés, le tracking facial MediaPipe/InsightFace, l'analyse audio Pyannote/Lemonfox, et l'intégration After Effects ExtendScript."

    titles = [
        "STEP1 extraction : Commande exécution sécurisée",
        "STEP2 conversion : Conversion vidéo 25fps",
        "STEP3 scene detection : TransNetV2 analyse scènes",
        "STEP4 audio analysis : Lemonfox + Pyannote",
        "STEP5 MediaPipe CPU : Tracking CPU multiprocessing",
        "STEP5 InsightFace GPU : Tracking GPU ONNX Runtime",
        "STEP6 JSON reduction : Optimisation données JSON",
        "STEP7 AE preprocessing : Pré-traitement After Effects",
        "STEP1 source dir error : Diagnostic répertoire manquant",
        "STEP2 ffmpeg error : Diagnostic outil manquant",
        "STEP3 GPU memory error : Gestion OOM TransNet",
        "STEP4 model error : Téléchargement modèles audio",
        "STEP5 CPU workers error : Ajustement multiprocessing",
        "STEP5 GPU unavailable : Fallback CPU MediaPipe",
        "STEP6 JSON malformed : Validation données entrée",
        "STEP7 file not found : Gestion fichiers manquants",
        "STEP1 speed optimization : Amélioration extraction archives",
        "STEP2 quality optimization : Paramètres conversion haute qualité",
        "STEP3 accuracy optimization : Seuils détection scènes",
        "STEP4 audio processing opt : Profil GPU et smoothing",
        "STEP5 MediaPipe perf : Workers et chunking CPU",
        "STEP5 InsightFace perf : ONNX et modèles GPU",
        "STEP6 JSON reduction opt : Streaming et parallélisation",
        "STEP7 AE preprocessing opt : Structures pré-indexées",
        "Pipeline status check : Vérification état via API",
        "Pipeline performance monitoring : Métriques système",
        "Pipeline interruptions handling : Reprise thread-safe",
        "Pipeline settings configuration : Hiérarchie .env/settings",
        "Pipeline state debugging : Diagnostic WorkflowState",
        "Pipeline logs management : Structure et rotation logs",
        "Pipeline dry run mode : Exécution simulation",
        "Pipeline parallel execution : Multiprocessing interne",
        "Pipeline resource management : Verrous et FilesystemService",
        "Pipeline error recovery : Relance étapes échouées",
        "Pipeline completion validation : Vérification résultats finaux"
    ]

    examples = []

    for title in titles:
        # Générer question utilisateur
        user_question = f"Comment {title.lower()} ?"

        # Générer réponse assistant (générique technique)
        assistant_response = f"Pour {title.lower()}, voici la procédure recommandée :\n\n"

        if "commande" in title.lower():
            assistant_response += f"```bash\n# Exemple de commande pour {title.split(':')[0]}\n/mnt/venv_ext4/env/bin/python workflow_scripts/{title.split()[0].lower()}/run_*.py\n```\n\n"
        elif "error" in title.lower():
            assistant_response += f"**Diagnostic {title.split(':')[0]} :**\n- Vérifier les logs dans `logs/{title.split()[0].lower()}/`\n- Contrôler la configuration dans `.env`\n- Utiliser les outils de debugging appropriés\n\n"
        elif "optimization" in title.lower() or "perf" in title.lower():
            assistant_response += f"**Optimisations pour {title.split(':')[0]} :**\n- Ajuster les paramètres dans `.env`\n- Monitorer les métriques de performance\n- Utiliser les profilers intégrés\n\n"
        else:
            assistant_response += f"**Configuration {title.split(':')[0]} :**\n- Suivre les standards du projet\n- Utiliser les services appropriés\n- Valider avec les tests unitaires\n\n"

        assistant_response += "**Références :**\n- `docs/workflow/` pour la documentation complète\n- `services/workflow_service.py` pour l'implémentation\n- `.windsurf/rules/codingstandards.md` pour les standards"

        # Créer l'exemple JSON
        example = {
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_question
                },
                {
                    "role": "assistant",
                    "content": assistant_response
                }
            ]
        }

        examples.append(example)

    return examples

def save_examples(examples, output_file):
    """Sauvegarde les exemples dans un fichier JSONL"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in examples:
            json.dump(example, f, ensure_ascii=False)
            f.write('\n')

    print(f"✅ {len(examples)} exemples sauvegardés dans {output_file}")

def validate_examples(examples):
    """Valide que tous les exemples sont du JSON valide"""
    valid_count = 0
    for i, example in enumerate(examples):
        try:
            json_str = json.dumps(example, ensure_ascii=False)
            json.loads(json_str)  # Test round-trip
            valid_count += 1
        except Exception as e:
            print(f"❌ Exemple {i} invalide: {e}")
            return False

    print(f"✅ {valid_count}/{len(examples)} exemples valides")
    return True

def main():
    output_file = "dataset/pipeline_operations_batch.jsonl"

    print("=== Régénération Pipeline Operations Batch ===")

    # Générer les exemples
    examples = generate_pipeline_examples()
    print(f"Généré {len(examples)} exemples")

    # Valider
    if not validate_examples(examples):
        print("❌ Erreur de validation")
        return

    # Sauvegarder
    save_examples(examples, output_file)

    print("🎉 Régénération terminée!")

if __name__ == "__main__":
    main()
