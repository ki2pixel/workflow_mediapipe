import os
import sys
import json
import argparse
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def setup_logging(log_dir: str):
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(log_dir, f"json_reducer_{timestamp}.log")

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.propagate = False

    logger.info(f"Log file initialized: {log_path}")
    return log_path


def reduce_video_json(data):
    """
    Réduit un objet JSON de données vidéo pour ne conserver que les clés
    utiles au script After Effects.
    """
    if "frames" not in data:
        return {"frames_analysis": []}  # Retourne une structure vide si le format est inattendu

    new_frames_data = []
    for frame in data["frames"]:
        new_tracked_objects = []
        if "tracked_objects" in frame and frame["tracked_objects"] is not None:
            for obj in frame["tracked_objects"]:
                # Initialisation de l'objet simplifié
                new_obj = {
                    "id": obj.get("id"),
                    "centroid_x": obj.get("centroid_x"),
                    "source": obj.get("source"),
                    "label": obj.get("label"),
                    "active_speakers": []  # Valeur par défaut
                }

                # Inclure la taille du bbox si disponible (ajout depuis l'étape 5)
                bbox_w = obj.get("bbox_width")
                bbox_h = obj.get("bbox_height")
                if bbox_w is not None and bbox_h is not None:
                    new_obj["bbox_width"] = bbox_w
                    new_obj["bbox_height"] = bbox_h

                # Extraction sécurisée de active_speakers
                if (obj.get("speaking_sources") and
                        isinstance(obj["speaking_sources"], dict) and
                        obj["speaking_sources"].get("audio") and
                        isinstance(obj["speaking_sources"]["audio"], dict)):
                    new_obj["active_speakers"] = obj["speaking_sources"]["audio"].get("active_speakers", [])

                new_tracked_objects.append(new_obj)

        new_frames_data.append({
            "frame": frame.get("frame"),
            "tracked_objects": new_tracked_objects
        })

    # La structure finale utilise "frames_analysis" pour correspondre au script AE
    return {"frames_analysis": new_frames_data}


def reduce_audio_json(data):
    """
    Réduit un objet JSON de données audio pour ne conserver que les clés
    utiles au script After Effects.
    """
    if "frames_analysis" not in data:
        return {"frames_analysis": []}  # Retourne une structure vide si le format est inattendu

    new_frames_analysis = []
    for frame_data in data["frames_analysis"]:
        if "audio_info" in frame_data and frame_data["audio_info"] is not None:
            new_audio_info = {
                "is_speech_present": frame_data["audio_info"].get("is_speech_present", False),
                "active_speaker_labels": frame_data["audio_info"].get("active_speaker_labels", [])
            }
            new_frames_analysis.append({
                "frame": frame_data.get("frame"),
                "audio_info": new_audio_info
            })

    return {"frames_analysis": new_frames_analysis}


def process_directory(base_path, keyword="Camille"):
    """
    Analyse les dossiers dans le chemin de base, recherche le mot-clé,
    et traite les paires de fichiers JSON trouvées dans les sous-dossiers "docs".
    """
    logger.info(f"Démarrage du scan dans : {base_path}")
    if not os.path.isdir(base_path):
        logger.error(f"Erreur : Le répertoire de base '{base_path}' n'existe pas.")
        return

    # 1. Lister les dossiers de projet
    project_folders = [d for d in os.listdir(base_path)
                       if os.path.isdir(os.path.join(base_path, d)) and keyword in d]

    if not project_folders:
        print(f"Aucun dossier contenant le mot-clé '{keyword}' n'a été trouvé.")
        return

    logger.info(f"Dossiers de projet trouvés : {len(project_folders)}")

    for folder in project_folders:
        docs_path = os.path.join(base_path, folder, "docs")

        if not os.path.isdir(docs_path):
            logger.warning(f"-> Avertissement : Le dossier 'docs' est manquant dans '{folder}'.")
            continue

        logger.info(f"\n--- Traitement du dossier : {docs_path} ---")

        # 2. Identifier les paires de fichiers JSON
        all_files = os.listdir(docs_path)
        video_json_files = [f for f in all_files if f.endswith(".json") and not f.endswith("_audio.json")]

        if not video_json_files:
            logger.info("Aucun fichier JSON vidéo principal trouvé.")
            continue

        for video_file in video_json_files:
            base_name = video_file.rsplit('.', 1)[0]
            audio_file = f"{base_name}_audio.json"

            video_path = os.path.join(docs_path, video_file)
            audio_path = os.path.join(docs_path, audio_file)

            if audio_file not in all_files:
                logger.warning(f"  - Fichier audio '{audio_file}' manquant pour '{video_file}'. Ignoré.")
                continue

            logger.info(f"  - Paire trouvée : \n    - {video_file}\n    - {audio_file}")

            try:
                # 3. Traiter le JSON vidéo
                with open(video_path, 'r', encoding='utf-8') as f:
                    video_data = json.load(f)

                reduced_video_data = reduce_video_json(video_data)

                with open(video_path, 'w', encoding='utf-8') as f:
                    json.dump(reduced_video_data, f, indent=2)

                logger.info("    - Fichier vidéo réduit avec succès.")

                # 4. Traiter le JSON audio
                with open(audio_path, 'r', encoding='utf-8') as f:
                    audio_data = json.load(f)

                reduced_audio_data = reduce_audio_json(audio_data)

                with open(audio_path, 'w', encoding='utf-8') as f:
                    json.dump(reduced_audio_data, f, indent=2)

                logger.info("    - Fichier audio réduit avec succès.")

            except json.JSONDecodeError as e:
                logger.error(f"    - ERREUR : Impossible de lire un fichier JSON. Erreur : {e}")
            except Exception as e:
                logger.error(f"    - ERREUR : Une erreur inattendue est survenue. Erreur : {e}")

    logger.info("\n--- Traitement terminé ! ---")


def main():
    parser = argparse.ArgumentParser(description="Étape 6 - Réduction JSON (vidéo + audio)")
    parser.add_argument('--base_dir', type=str, default=os.environ.get('BASE_PATH_SCRIPTS', ''), help='Chemin base du projet (contenant projets_extraits)')
    parser.add_argument('--work_dir', type=str, default=None, help='Chemin explicite vers projets_extraits')
    parser.add_argument('--keyword', type=str, default=os.environ.get('FOLDER_KEYWORD', 'Camille'), help='Mot-clé pour filtrer les dossiers projet')
    parser.add_argument('--log_dir', type=str, default=str(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'logs', 'step6')),
                        help='Répertoire pour les logs (par défaut logs/step6)')

    args = parser.parse_args()

    # Resolve working directory
    if args.work_dir:
        work_dir = args.work_dir
    else:
        base_dir = args.base_dir if args.base_dir else os.getcwd()
        work_dir = os.path.join(base_dir, 'projets_extraits')

    # Setup logging
    setup_logging(args.log_dir)

    # Progress total: count candidate projects
    try:
        if not os.path.isdir(work_dir):
            logger.warning(f"Répertoire de travail introuvable: {work_dir}")
            print(f"TOTAL_JSON_TO_REDUCE: 0")
            sys.exit(0)
        projects = [d for d in os.listdir(work_dir) if os.path.isdir(os.path.join(work_dir, d)) and args.keyword in d]
        print(f"TOTAL_JSON_TO_REDUCE: {len(projects)}")
    except Exception:
        print("TOTAL_JSON_TO_REDUCE: 0")

    # Run processing
    process_directory(work_dir, keyword=args.keyword)


if __name__ == "__main__":
    main()
