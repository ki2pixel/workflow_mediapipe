#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de compilation du modèle MobileNetV2 tronqué à la couche GAP (1280D)
pour Google Coral Edge TPU.

Usage:
    python scripts/compile_mobilenet_gap.py [--output_dir assets/]

Prérequis:
    - tensorflow >= 2.x
    - edgetpu_compiler (installé via: apt install edgetpu-compiler)

Ce script :
1. Charge MobileNetV2 pré-entraîné sur ImageNet via Keras
2. Tronque le modèle à la couche global_average_pooling2d (sortie 1280D)
3. Exporte en TFLite INT8 avec un dataset représentatif
4. Compile avec edgetpu_compiler pour Google Coral
5. Copie le résultat dans le dossier assets/

Note: Ce script est à exécuter manuellement et ne fait pas partie du pipeline automatique.
"""

import os
import sys
import argparse
import shutil
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def compile_mobilenet_gap(output_dir: Path):
    """Compile le modèle MobileNetV2 tronqué à la couche GAP."""

    try:
        import tensorflow as tf
        import numpy as np
    except ImportError:
        logging.critical(
            "TensorFlow n'est pas installé. Installez-le avec: "
            "pip install tensorflow"
        )
        sys.exit(1)

    logging.info("Chargement de MobileNetV2 pré-entraîné (ImageNet)...")
    base_model = tf.keras.applications.MobileNetV2(
        weights='imagenet',
        include_top=True,
        input_shape=(224, 224, 3)
    )

    # Trouver la couche GAP
    gap_layer = None
    for layer in base_model.layers:
        if 'global_average_pooling' in layer.name:
            gap_layer = layer
            break

    if gap_layer is None:
        logging.critical("Couche global_average_pooling2d non trouvée dans MobileNetV2")
        sys.exit(1)

    logging.info(f"Couche GAP trouvée: {gap_layer.name}, output shape: {gap_layer.output.shape}")

    # Créer le modèle tronqué
    truncated_model = tf.keras.Model(
        inputs=base_model.input,
        outputs=gap_layer.output
    )
    truncated_model.summary()

    # Générateur de dataset représentatif pour la quantification INT8
    def representative_dataset():
        """Génère des images aléatoires pour la calibration INT8.

        En production, remplacer par des frames réelles des vidéos du projet.
        """
        for _ in range(100):
            # Images aléatoires 224x224 RGB normalisées [0, 255] → uint8
            data = np.random.randint(0, 256, (1, 224, 224, 3)).astype(np.float32)
            # Normalisation MobileNetV2 : [-1, 1]
            data = (data / 127.5) - 1.0
            yield [data]

    # Conversion TFLite INT8
    logging.info("Conversion en TFLite INT8 (quantification post-entraînement)...")
    converter = tf.lite.TFLiteConverter.from_keras_model(truncated_model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.uint8
    converter.inference_output_type = tf.uint8

    tflite_model = converter.convert()

    # Sauvegarde du modèle TFLite
    output_dir.mkdir(parents=True, exist_ok=True)
    tflite_path = output_dir / "mobilenet_v2_gap_1280_quant.tflite"
    with open(tflite_path, 'wb') as f:
        f.write(tflite_model)
    logging.info(f"Modèle TFLite INT8 sauvegardé: {tflite_path}")

    # Compilation Edge TPU
    logging.info("Compilation pour Edge TPU...")
    edgetpu_path = tflite_path.with_name("mobilenet_v2_gap_1280_quant_edgetpu.tflite")

    try:
        result = subprocess.run(
            ['edgetpu_compiler', str(tflite_path), '-o', str(output_dir)],
            capture_output=True, text=True, check=True
        )
        logging.info(f"Compilation Edge TPU réussie:\n{result.stdout}")

        # Le compilateur génère le fichier avec _edgetpu dans le nom
        expected_compiled = output_dir / "mobilenet_v2_gap_1280_quant_edgetpu.tflite"
        if expected_compiled.exists():
            logging.info(f"Modèle Edge TPU disponible: {expected_compiled}")
        else:
            logging.warning(
                f"Fichier compilé attendu non trouvé: {expected_compiled}. "
                f"Vérifiez le contenu de {output_dir}"
            )

    except FileNotFoundError:
        logging.error(
            "edgetpu_compiler non trouvé. Installez-le avec:\n"
            "  curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -\n"
            "  echo 'deb https://packages.cloud.google.com/apt coral-edgetpu-stable main' | "
            "sudo tee /etc/apt/sources.list.d/coral-edgetpu.list\n"
            "  sudo apt update && sudo apt install edgetpu-compiler"
        )
        logging.info(
            f"Le modèle TFLite INT8 non-compilé est disponible: {tflite_path}. "
            f"Compilez-le manuellement avec: edgetpu_compiler {tflite_path}"
        )
    except subprocess.CalledProcessError as e:
        logging.error(f"Erreur de compilation Edge TPU: {e.stderr}")
        logging.info(
            f"Le modèle TFLite INT8 non-compilé est disponible: {tflite_path}. "
            f"Vérifiez la compatibilité des opérations avec le compilateur."
        )


def main():
    parser = argparse.ArgumentParser(
        description="Compile MobileNetV2 tronqué (GAP 1280D) pour Edge TPU"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=str(Path(__file__).parent.parent / "assets"),
        help="Dossier de sortie pour le modèle compilé (défaut: assets/)"
    )
    args = parser.parse_args()

    compile_mobilenet_gap(Path(args.output_dir))


if __name__ == "__main__":
    main()
