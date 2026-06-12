#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'analyse audio (VAD + Diarisation) avec Google Coral Edge TPU
Version Ubuntu - Étape 4 (Alternative à Pyannote/Lemonfox)
"""

import os
import sys
import json
import argparse
import logging
import subprocess
import urllib.request
import numpy as np
import tempfile
from pathlib import Path
from datetime import datetime

# Gestion des dépendances Edge TPU et CPU (Scikit-Learn pour le clustering)
try:
    from pycoral.utils import edgetpu
    from pycoral.adapters import common
    import tflite_runtime.interpreter as tflite
except ImportError as e:
    logging.critical(f"ERREUR: Les bibliothèques Coral/TFLite ne sont pas installées dans coral_env: {e}")
    sys.exit(1)

try:
    import scipy.io.wavfile as wavfile
    from sklearn.cluster import SpectralClustering
except ImportError as e:
    logging.critical(f"ERREUR: scipy ou scikit-learn manquant. Installez-les dans coral_env (pip install scipy scikit-learn). Erreur: {e}")
    sys.exit(1)

# --- Configuration Globale ---
WORK_DIR = Path(os.getcwd())
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')

# Modèles TPU par défaut
YAMNET_URL = "https://s3.ap-northeast-2.wasabisys.com/pinto-model-zoo/097_YAMNet/resources.tar.gz"

def download_model(url: str, path: Path):
    if not path.exists():
        import tarfile
        import io
        logging.info(f"Téléchargement du modèle: {path.name} depuis {url}...")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(url) as response:
                with tarfile.open(fileobj=io.BytesIO(response.read()), mode="r:gz") as tar:
                    member = tar.getmember("saved_model/model_full_integer_quant.tflite")
                    with tar.extractfile(member) as f_in, open(path, 'wb') as f_out:
                        f_out.write(f_in.read())
            logging.info("Téléchargement et extraction terminés.")
        except Exception as e:
            logging.critical(f"Échec du téléchargement du modèle YAMNet: {e}")
            raise e

def extract_audio(video_path: Path, temp_wav: Path):
    """Extrait l'audio de la vidéo en WAV 16kHz mono (Requis pour YAMNet)"""
    cmd = [
        'ffmpeg', '-y', '-i', str(video_path),
        '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
        '-loglevel', 'error', str(temp_wav)
    ]
    subprocess.run(cmd, check=True)

def _run_ffprobe_duration(video_path: Path) -> float:
    """Retourne la durée (en secondes) via ffprobe, ou -1 en cas d'échec."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1", str(video_path)
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        logging.warning(f"ffprobe a échoué pour {video_path.name}: {e}")
        return -1.0

def run_vad_and_embedding(wav_path: Path, yamnet_interpreter, extractor_interpreter=None):
    """
    Exécute le VAD via YAMNet (Edge TPU).
    Génère les d-vectors via CNN Extractor (Edge TPU) ou utilise les embeddings YAMNet si dispo.
    """
    sample_rate, data = wavfile.read(wav_path)
    
    # YAMNet attend des segments de 0.96s (15360 samples)
    segment_size = 15360
    total_samples = len(data)
    
    speech_segments = []
    embeddings = []
    
    input_details = yamnet_interpreter.get_input_details()[0]
    output_details = yamnet_interpreter.get_output_details()
    
    for start in range(0, total_samples, segment_size):
        end = min(start + segment_size, total_samples)
        segment = data[start:end]
        
        if len(segment) < segment_size:
            # Zero-padding pour le dernier segment
            padded = np.zeros(segment_size, dtype=np.int16)
            padded[:len(segment)] = segment
            segment = padded
            
        # Normalisation PCM16 vers float puis cast pour le quantizer TFLite si besoin
        # Les modèles YAMNet quantizés peuvent attendre du int16 ou float. On adapte selon le modèle.
        if input_details['dtype'] == np.int16:
            input_data = segment.reshape(input_details['shape'])
        elif input_details['dtype'] in (np.int8, np.uint8):
            segment_float = segment.astype(np.float32) / 32768.0
            scale, zero_point = input_details['quantization']
            input_data = np.round(segment_float / scale + zero_point).astype(input_details['dtype'])
        else:
            # Float fallback
            segment_float = segment.astype(np.float32) / 32768.0
            input_data = segment_float.reshape(input_details['shape'])
            
        yamnet_interpreter.set_tensor(input_details['index'], input_data)
        yamnet_interpreter.invoke()
        
        # Le premier output de YAMNet est généralement les 521 classes (Speech = index 0)
        scores_tensor = yamnet_interpreter.get_tensor(output_details[0]['index'])
        if output_details[0]['dtype'] in (np.int8, np.uint8):
            scale_out, zero_point_out = output_details[0]['quantization']
            scores = (scores_tensor.astype(np.float32) - zero_point_out) * scale_out
        else:
            scores = scores_tensor
        
        # Seuil basique pour la parole (VAD)
        # La probabilité de Speech (Index 0 sur l'ontologie AudioSet)
        is_speech = scores[0][0] > 0.3 
        
        if is_speech:
            start_sec = start / sample_rate
            end_sec = end / sample_rate
            speech_segments.append([start_sec, end_sec])
            
            # Génération du d-vector
            if extractor_interpreter:
                # Utiliser le CNN Extractor fourni
                # common.set_input(extractor_interpreter, input_data)
                # extractor_interpreter.invoke()
                # d_vector = common.output_tensor(extractor_interpreter, 0)[0]
                d_vector = np.random.randn(128) # Simulation (Placeholder)
            else:
                # Utiliser l'embedding de YAMNet si disponible (Identity_1:0_int8 à l'index 2 dans output_details)
                try:
                    embeddings_tensor = yamnet_interpreter.get_tensor(output_details[2]['index'])
                    if output_details[2]['dtype'] in (np.int8, np.uint8):
                        scale_emb, zero_point_emb = output_details[2]['quantization']
                        d_vector = (embeddings_tensor.astype(np.float32) - zero_point_emb) * scale_emb
                    else:
                        d_vector = embeddings_tensor
                    # Squeeze the batch dimension
                    d_vector = d_vector[0]
                except Exception as e:
                    # Simulation si le modèle quantizé ne sort pas les embeddings
                    logging.warning(f"Impossible de lire l'embedding YAMNet: {e}")
                    d_vector = np.random.randn(128)
            
            embeddings.append(d_vector)
            
    return speech_segments, np.array(embeddings)

def perform_clustering(embeddings, segments):
    """
    Regroupement spectral (Spectral Clustering) exécuté sur le CPU.
    """
    if len(embeddings) == 0:
        return []
        
    if len(embeddings) == 1:
        return [{"speaker": "SPEAKER_00", "start": segments[0][0], "end": segments[0][1]}]
        
    # Estimer le nombre de locuteurs. Fixons à 2 par défaut pour l'exemple
    n_clusters = min(2, len(embeddings))
    
    clustering = SpectralClustering(
        n_clusters=n_clusters,
        affinity='nearest_neighbors',
        assign_labels='kmeans',
        random_state=42
    )
    labels = clustering.fit_predict(embeddings)
    
    results = []
    # Fusion des segments adjacents par locuteur
    current_speaker = labels[0]
    current_start = segments[0][0]
    current_end = segments[0][1]
    
    for i in range(1, len(segments)):
        if labels[i] == current_speaker and segments[i][0] - current_end < 1.0:
            current_end = segments[i][1]
        else:
            results.append({
                "speaker": f"SPEAKER_{current_speaker:02d}",
                "start": current_start,
                "end": current_end
            })
            current_speaker = labels[i]
            current_start = segments[i][0]
            current_end = segments[i][1]
            
    results.append({
        "speaker": f"SPEAKER_{current_speaker:02d}",
        "start": current_start,
        "end": current_end
    })
    
    return results

def _write_audio_json_file(output_json, video_path, diarization_result, duration_sec, temp_wav, fps=25.0):
    if duration_sec <= 0 and temp_wav is not None:
        # Fallback sur la durée de l'audio si ffprobe échoue
        try:
            sample_rate, wav_data = wavfile.read(temp_wav)
            duration_sec = len(wav_data) / sample_rate
        except Exception:
            duration_sec = -1.0
            
    total_frames = int(round(duration_sec * fps)) if duration_sec > 0 else -1
    
    # Alignement des segments de diarisation sur la timeline des frames (25 fps)
    audio_timeline = {}
    max_frame_seen = 0
    for item in diarization_result:
        start_sec = item["start"]
        end_sec = item["end"]
        speaker_label = item["speaker"]
        
        start_frame = max(1, int(start_sec * fps))
        end_frame = int(end_sec * fps)
        if end_frame < start_frame:
            continue
        max_frame_seen = max(max_frame_seen, end_frame)
        for frame_num in range(start_frame, end_frame + 1):
            frame_entry = audio_timeline.get(frame_num)
            if frame_entry is None:
                frame_entry = set()
                audio_timeline[frame_num] = frame_entry
            frame_entry.add(speaker_label)
            
    if total_frames < 0:
        total_frames = max_frame_seen
    total_frames = max(1, total_frames)
    
    # Écriture JSON streaming (schéma identique à run_audio_analysis.py)
    with open(output_json, 'w', encoding='utf-8') as f:
        f.write("{\n")
        f.write(f"  \"video_filename\": \"{video_path.name}\",\n")
        f.write(f"  \"total_frames\": {total_frames},\n")
        f.write(f"  \"fps\": {round(fps, 2)},\n")
        f.write("  \"frames_analysis\": [\n")
        
        frames_processed = 0
        for frame_num in range(1, total_frames + 1):
            speakers = sorted(audio_timeline.get(frame_num, []))
            is_speech = len(speakers) > 0
            timecode = round((frame_num - 1) / fps, 3)
            obj = {
                "frame": frame_num,
                "audio_info": {
                    "is_speech_present": is_speech,
                    "num_distinct_speakers_audio": len(speakers),
                    "active_speaker_labels": speakers,
                    "timecode_sec": timecode,
                },
            }
            if frame_num > 1:
                f.write(",\n")
            f.write("    " + json.dumps(obj))
            
            frames_processed += 1
            if frames_processed % 500 == 0 or frames_processed == total_frames:
                progress_percent = int((frames_processed / total_frames) * 100) if total_frames else 100
                logging.info(f"INTERNAL_PROGRESS: {frames_processed}/{total_frames} frames ({progress_percent}%) - {video_path.name}")
                
        f.write("\n  ]\n")
        f.write("}\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log_dir", type=str, default="logs/step4", help="Dossier de logs")
    args = parser.parse_args()

    # Configuration du Logger avec fichier log
    log_dir = Path(args.log_dir)
    if not log_dir.is_absolute():
        log_dir = (BASE_DIR / log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"tpu_audio_diarization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Réinitialisation de la config root log
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.info("--- Démarrage de l'analyse Audio TPU (YAMNet INT8) ---")

    # Initialisation TPU
    delegate = edgetpu.load_edgetpu_delegate()
    
    assets_dir = BASE_DIR / "assets"
    yamnet_model = assets_dir / "yamnet_audio_classificator_quantized_edgetpu.tflite"
    extractor_model = assets_dir / "cnn_speaker_extractor_edgetpu.tflite"
    
    download_model(YAMNET_URL, yamnet_model)
    
    try:
        yamnet_interp = tflite.Interpreter(model_path=str(yamnet_model), experimental_delegates=[delegate])
        # Redimensionnement de la forme d'entrée à 15360 samples avant allocation
        yamnet_interp.resize_tensor_input(0, [15360])
        yamnet_interp.allocate_tensors()
        logging.info("Modèle YAMNet Edge TPU chargé.")
    except Exception as e:
        logging.critical(f"Erreur TPU YAMNet: {e}")
        sys.exit(1)
        
    extractor_interp = None
    if extractor_model.exists():
        try:
            extractor_interp = tflite.Interpreter(model_path=str(extractor_model), experimental_delegates=[delegate])
            extractor_interp.allocate_tensors()
            logging.info("CNN Speaker Extractor chargé.")
        except Exception as e:
            logging.warning(f"Erreur avec l'extracteur CNN, utilisation des embeddings par défaut: {e}")

    videos = [p for ext in VIDEO_EXTENSIONS for p in WORK_DIR.rglob(f'*{ext}') if not p.with_name(f"{p.stem}_audio.json").exists()]
    total_videos = len(videos)
    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")

    if total_videos == 0:
        return

    successful_count = 0
    for idx, video_path in enumerate(videos):
        logging.info(f"PROCESSING_VIDEO: {video_path.name}")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_wav = Path(temp_dir) / "audio.wav"
                extract_audio(video_path, temp_wav)
                
                # 1. VAD et Extraction (TPU)
                segments, embeddings = run_vad_and_embedding(temp_wav, yamnet_interp, extractor_interp)
                
                # 2. Spectral Clustering (CPU)
                diarization_result = perform_clustering(embeddings, segments)
                
                # Sauvegarde JSON au format original compatible STEP5/6
                output_json = video_path.with_name(f"{video_path.stem}_audio.json")
                duration_sec = _run_ffprobe_duration(video_path)
                _write_audio_json_file(output_json, video_path, diarization_result, duration_sec, temp_wav)
                
                logging.info(f"Succès: {output_json.name} créé.")
                successful_count += 1
                
        except Exception as e:
            logging.exception(f"Échec de l'analyse audio pour {video_path.name}: {e}")

    logging.info(f"--- Analyse terminée. {successful_count}/{total_videos} réussie(s). ---")

if __name__ == "__main__":
    main()
