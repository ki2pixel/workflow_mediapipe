#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'analyse audio (diarisation) avec Pyannote.audio
Version Ubuntu - Étape 4

Optimisations clés:
- Extraction audio via ffmpeg (remplace MoviePy) vers tmpfs si disponible
- Suppression d'OpenCV/MoviePy pour les métadonnées (utilisation ffprobe + fallback FPS=25)
- Écriture JSON en streaming (évite le stockage complet en mémoire)
- Mapping segments->frames sans matérialiser toute la diarisation
- Journalisation unique (suppression des prints dupliqués)
- Inference PyTorch optimisée (CUDA prioritaire, CPU fallback; no_grad/inference_mode)
- Politique device/workers configurable via variables d'environnement
- Nettoyage robuste des répertoires temporaires
- Compression gzip optionnelle (désactivée par défaut pour compatibilité STEP5)
"""

import os
import sys
import json
import argparse
import logging
import subprocess
import tempfile
import gzip
import time
import gc
from contextlib import nullcontext
import torch
from pathlib import Path
from datetime import datetime

# --- Configuration ---
WORK_DIR = Path(os.getcwd())
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm')
OUTPUT_SUFFIX = "_audio.json"
DEFAULT_FPS = 25

LOG_DIR_PATH = None


def _load_optimal_tv_config() -> dict:
    try:
        repo_root = Path(__file__).resolve().parents[2]
        config_path = repo_root / "config" / "optimal_tv_config.json"
        if not config_path.exists():
            return {}
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logging.warning("optimal_tv_config.json ignoré (JSON racine non-objet).")
            return {}
        logging.info(f"optimal_tv_config.json chargé: {config_path}")
        return data
    except Exception as e:
        logging.warning(f"Impossible de charger optimal_tv_config.json: {e}")
        return {}

# Le dossier de log est AUDIO_ANALYSIS_LOG_DIR, passé par argument
# On configure un logger de base qui sera complété dans main()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)


def find_videos_for_audio_analysis():
    """Trouve toutes les vidéos à analyser qui n'ont pas encore de fichier _audio.json."""
    videos_to_process = []
    logging.info(f"Recherche de vidéos dans {WORK_DIR}...")

    all_videos = [p for ext in VIDEO_EXTENSIONS for p in WORK_DIR.rglob(f'*{ext}')]

    skipped_mov = 0
    filtered_videos = []
    for video_path in all_videos:
        if video_path.suffix.lower() == '.mov':
            skipped_mov += 1
            continue
        filtered_videos.append(video_path)

    for video_path in filtered_videos:
        output_json_path = video_path.with_name(f"{video_path.stem}{OUTPUT_SUFFIX}")
        if not output_json_path.exists():
            videos_to_process.append(video_path)
    
    return videos_to_process


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


def _extract_audio_ffmpeg(input_video: Path, output_wav: Path) -> bool:
    """Extrait l'audio en WAV mono 16kHz via ffmpeg. Retourne True si OK."""
    try:
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(input_video),
            "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", "-acodec", "pcm_s16le",
            str(output_wav)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"ffmpeg extraction audio a échoué pour {input_video.name}: {e}")
        return False


def _write_empty_audio_json_streaming(output_json_path: Path, video_name: str, total_frames: int, fps: float) -> None:
    """Écrit un JSON vide compatible STEP5 en streaming."""
    with open(output_json_path, 'w', encoding='utf-8') as f:
        f.write('{\n')
        f.write(f'  "video_filename": "{video_name}",\n')
        f.write(f'  "total_frames": {total_frames},\n')
        f.write(f'  "fps": {round(fps, 2)},\n')
        f.write('  "frames_analysis": [')
        if total_frames > 0:
            f.write('\n')
            for frame_num in range(1, total_frames + 1):
                timecode = round((frame_num - 1) / fps, 3)
                obj = {
                    "frame": frame_num,
                    "audio_info": {
                        "is_speech_present": False,
                        "num_distinct_speakers_audio": 0,
                        "active_speaker_labels": [],
                        "timecode_sec": timecode,
                    },
                }
                if frame_num > 1:
                    f.write(',\n')
                f.write(json.dumps(obj))
        f.write('\n  ]\n')
        f.write('}\n')


def _cleanup_cuda_memory() -> None:
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    try:
        gc.collect()
    except Exception:
        pass


def _get_total_vram_gb() -> float:
    try:
        if not torch.cuda.is_available():
            return 0.0
        props = torch.cuda.get_device_properties(0)
        return float(props.total_memory) / (1024**3)
    except Exception:
        return 0.0


def _is_low_vram_gpu(threshold_gb: float = 6.0) -> bool:
    total_gb = _get_total_vram_gb()
    return total_gb > 0.0 and total_gb <= threshold_gb


def _should_enable_amp(device: str) -> bool:
    if device != "cuda":
        return False
    env_value = os.getenv("AUDIO_ENABLE_AMP")
    if env_value is not None:
        return env_value == "1"
    return _is_low_vram_gpu()


def _get_pyannote_batch_size(device: str) -> int | None:
    raw = os.getenv("AUDIO_PYANNOTE_BATCH_SIZE")
    if raw is not None:
        try:
            value = int(raw)
            return value if value > 0 else None
        except Exception:
            return None
    if device == "cuda" and _is_low_vram_gpu():
        return 1
    return None


def _import_pyannote_pipeline():
    from pyannote.audio import Pipeline
    return Pipeline


def _load_pyannote_pipeline(model_id: str, hf_token: str, pipeline_cls=None):
    """
    Load pyannote Pipeline while handling token/use_auth_token compatibility.
    """
    pipeline_cls = pipeline_cls or _import_pyannote_pipeline()
    try:
        return pipeline_cls.from_pretrained(model_id, token=hf_token)
    except TypeError as type_err:
        if "token" not in str(type_err):
            raise
        logging.info(
            "Pipeline.from_pretrained(%s) ne supporte pas 'token'. "
            "Tentative avec use_auth_token.",
            model_id,
        )
        return pipeline_cls.from_pretrained(model_id, use_auth_token=hf_token)


def _run_diarization_and_extract_segments(diarization_pipeline, wav_path: Path, device: str) -> list:
    use_amp = _should_enable_amp(device)
    if use_amp and hasattr(torch, "cuda") and hasattr(torch.cuda, "amp"):
        amp_ctx = torch.cuda.amp.autocast(dtype=torch.float16)
    else:
        amp_ctx = nullcontext()

    pyannote_batch_size = _get_pyannote_batch_size(device)
    diarization_kwargs = {"num_speakers": None}
    if pyannote_batch_size is not None:
        diarization_kwargs["batch_size"] = pyannote_batch_size
        logging.info(f"Diarisation paramètres: batch_size={pyannote_batch_size}")

    with torch.inference_mode():
        with amp_ctx:
            try:
                diarization = diarization_pipeline(str(wav_path), **diarization_kwargs)
            except TypeError as e:
                if "batch_size" in str(e):
                    diarization_kwargs.pop("batch_size", None)
                    diarization = diarization_pipeline(str(wav_path), **diarization_kwargs)
                else:
                    raise
    segments = [(t.start, t.end, spk) for t, _, spk in diarization.itertracks(yield_label=True)]
    del diarization
    return segments


def _apply_audio_profile_from_env() -> None:
    profile = (os.getenv("AUDIO_PROFILE") or "").strip().lower()
    if not profile:
        return

    if profile == "gpu_optimized":
        os.environ["AUDIO_DISABLE_GPU"] = "0"
        os.environ["AUDIO_ENABLE_AMP"] = "1"
        os.environ["AUDIO_PYANNOTE_BATCH_SIZE"] = "1"
        logging.info("AUDIO_PROFILE=gpu_optimized appliqué (AMP=1, batch_size=1)")
        logging.warning("ATTENTION: AMP peut réduire significativement la qualité de diarisation (faux négatifs).")
        return

    if profile == "gpu_fp32":
        os.environ["AUDIO_DISABLE_GPU"] = "0"
        os.environ["AUDIO_ENABLE_AMP"] = "0"
        os.environ["AUDIO_PYANNOTE_BATCH_SIZE"] = "1"
        logging.info("AUDIO_PROFILE=gpu_fp32 appliqué (AMP=0, batch_size=1, FP32 pur - cohérence CPU)")
        return

    if profile == "gpu_no_amp":
        os.environ["AUDIO_DISABLE_GPU"] = "0"
        os.environ["AUDIO_ENABLE_AMP"] = "0"
        os.environ["AUDIO_PYANNOTE_BATCH_SIZE"] = "1"
        logging.info("AUDIO_PROFILE=gpu_no_amp appliqué (AMP=0, batch_size=1)")
        return

    if profile == "cpu_only":
        os.environ["AUDIO_DISABLE_GPU"] = "1"
        os.environ["AUDIO_ENABLE_AMP"] = "0"
        os.environ.pop("AUDIO_PYANNOTE_BATCH_SIZE", None)
        logging.info("AUDIO_PROFILE=cpu_only appliqué (GPU désactivé)")
        return

    logging.warning(
        f"AUDIO_PROFILE inconnu: '{profile}'. Valeurs supportées: gpu_optimized, gpu_fp32, gpu_no_amp, cpu_only"
    )


def _run_cpu_diarization_subprocess(wav_path: Path, output_segments_json: Path, hf_token: str) -> None:
    """Fallback CPU avec mêmes paramètres que GPU (sauf AMP) pour cohérence."""
    env = os.environ.copy()
    env["AUDIO_DISABLE_GPU"] = "1"
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["HUGGINGFACE_HUB_TOKEN"] = hf_token
    # Forcer FP32 (pas d'AMP) pour cohérence avec mode GPU sans AMP
    env["AUDIO_ENABLE_AMP"] = "0"
    pyannote_batch_size = os.getenv("AUDIO_PYANNOTE_BATCH_SIZE")
    if pyannote_batch_size:
        env["AUDIO_PYANNOTE_BATCH_SIZE"] = pyannote_batch_size

    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--log_dir",
        str(LOG_DIR_PATH or Path(tempfile.gettempdir())),
        "--disable_gpu",
        "--cpu_diarize_wav",
        str(wav_path),
        "--cpu_diarize_out",
        str(output_segments_json),
    ]
    subprocess.run(
        cmd,
        check=True,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def _load_segments_from_json(segments_json: Path) -> list:
    with open(segments_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    segments = []
    for item in data:
        start = float(item["start"])
        end = float(item["end"])
        speaker = str(item["speaker"])
        segments.append((start, end, speaker))
    return segments


def analyze_audio_file(video_path, diarization_pipeline, hf_token, device: str):
    """Analyse une vidéo, extrait l'audio via ffmpeg, effectue la diarisation et sauvegarde le JSON (streaming)."""
    output_json_path = video_path.with_name(f"{video_path.stem}{OUTPUT_SUFFIX}")

    duration_sec = _run_ffprobe_duration(video_path)
    video_fps = DEFAULT_FPS
    if duration_sec > 0:
        total_frames = int(round(duration_sec * video_fps))
    else:
        logging.warning(f"Durée inconnue, fallback frames basé sur DEFAULT_FPS={DEFAULT_FPS} pour {video_path.name}")
        # On fixera total_frames après avoir déterminé le max de frame touché par la timeline.
        total_frames = -1

    tmp_dir_root = "/dev/shm" if os.path.isdir("/dev/shm") else None
    try:
        with tempfile.TemporaryDirectory(dir=tmp_dir_root) as tmp_dir:
            tmp_wav = Path(tmp_dir) / f"{video_path.stem}_temp.wav"

            logging.info(f"Extraction audio (ffmpeg) de {video_path.name} -> {tmp_wav.name}...")
            if not _extract_audio_ffmpeg(video_path, tmp_wav):
                if total_frames < 0:
                    total_frames = 0
                _write_empty_audio_json_streaming(output_json_path, video_path.name, total_frames, video_fps)
                return True

            logging.info(f"Diarisation en cours sur {tmp_wav.name}...")
            start_infer_t = time.time()
            segments = None
            try:
                if device == "cuda":
                    _cleanup_cuda_memory()
                segments = _run_diarization_and_extract_segments(diarization_pipeline, tmp_wav, device)
                logging.info(f"Diarisation: {len(segments)} segment(s) détecté(s)")
            except RuntimeError as e_oom:
                if "CUDA out of memory" in str(e_oom):
                    logging.warning("CUDA OOM durant la diarisation, tentative de fallback CPU pour ce fichier...")
                    _cleanup_cuda_memory()
                    try:
                        cpu_segments_json = Path(tmp_dir) / f"{video_path.stem}_cpu_segments.json"
                        logging.info("Fallback CPU: mêmes paramètres que GPU (batch_size) sauf AMP, pour cohérence")
                        _run_cpu_diarization_subprocess(tmp_wav, cpu_segments_json, hf_token)
                        segments = _load_segments_from_json(cpu_segments_json)
                        logging.info(f"Fallback CPU: {len(segments)} segment(s) détecté(s)")
                    except subprocess.CalledProcessError as cpu_e:
                        safe_stderr = (cpu_e.stderr or "")
                        logging.error(
                            "Echec du fallback CPU (subprocess). "
                            f"returncode={cpu_e.returncode}. stderr:\n{safe_stderr}"
                        )
                        raise
                    except Exception:
                        logging.error("Echec du fallback CPU (erreur inattendue).", exc_info=True)
                        raise
                else:
                    segments = _run_diarization_and_extract_segments(diarization_pipeline, tmp_wav, device)
            infer_ms = int((time.time() - start_infer_t) * 1000)
            logging.info(f"Diarisation terminée en ~{infer_ms} ms")

            audio_timeline = {}
            max_frame_seen = 0
            for start_sec, end_sec, speaker_label in (segments or []):
                start_frame = max(1, int(start_sec * video_fps))
                end_frame = int(end_sec * video_fps)
                if end_frame < start_frame:
                    continue
                max_frame_seen = max(max_frame_seen, end_frame)
                for frame_num in range(start_frame, end_frame + 1):
                    frame_entry = audio_timeline.get(frame_num)
                    if frame_entry is None:
                        frame_entry = set()
                        audio_timeline[frame_num] = frame_entry
                    frame_entry.add(speaker_label)
            
            num_speech_frames = len(audio_timeline)
            speech_pct = (num_speech_frames / total_frames * 100) if total_frames > 0 else 0
            logging.info(f"Timeline audio: {num_speech_frames}/{total_frames} frames avec parole ({speech_pct:.1f}%)")

            if total_frames < 0:
                total_frames = max_frame_seen

            # Écriture JSON streaming (préserve le schéma pour STEP5)
            use_gzip = os.getenv("AUDIO_JSON_GZIP", "0") == "1"
            if use_gzip:
                json_path = str(output_json_path) + ".gz"
                open_fn = lambda p: gzip.open(p, mode="wt", encoding="utf-8")
            else:
                json_path = str(output_json_path)
                open_fn = lambda p: open(p, mode="w", encoding="utf-8")

            with open_fn(json_path) as f:
                f.write("{\n")
                f.write(f"  \"video_filename\": \"{video_path.name}\",\n")
                f.write(f"  \"total_frames\": {total_frames},\n")
                f.write(f"  \"fps\": {round(video_fps, 2)},\n")
                f.write("  \"frames_analysis\": [\n")
    
                frames_processed = 0
                last_log_t = time.time()
                for frame_num in range(1, total_frames + 1):
                    speakers = sorted(audio_timeline.get(frame_num, []))
                    is_speech = len(speakers) > 0
                    timecode = round((frame_num - 1) / video_fps, 3)
                    obj = {
                        "frame": frame_num,
                        "audio_info": {
                            "is_speech_present": is_speech,
                            "num_distinct_speakers_audio": len(speakers),
                            "active_speaker_labels": speakers,
                            "timecode_sec": timecode,
                        },
                    }
                    # Écriture streaming avec virgules correctes
                    if frame_num > 1:
                        f.write(",\n")
                    f.write(json.dumps(obj))
    
                    frames_processed += 1
                    if time.time() - last_log_t >= 2 or frames_processed == total_frames:
                        progress_percent = int((frames_processed / total_frames) * 100) if total_frames else 100
                        logging.info(
                            f"INTERNAL_PROGRESS: {frames_processed}/{total_frames} frames ({progress_percent}%) - {video_path.name}")
                        last_log_t = time.time()
    
                f.write("\n  ]\n")
                f.write("}\n")
    
            logging.info(f"Succès: analyse audio terminée pour {video_path.name}")
            return True

    except Exception as e:
        logging.error(f"Erreur inattendue lors de l'analyse de {video_path.name}: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(description="Analyse audio (diarisation) des vidéos.")
    parser.add_argument("--log_dir", type=str, required=True, help="Répertoire de logs")
    parser.add_argument("--hf_auth_token", type=str, help="Token d'authentification HuggingFace")
    parser.add_argument("--disable_gpu", action="store_true", help="Forcer l'utilisation CPU")
    parser.add_argument("--cpu_diarize_wav", type=str, help="Mode interne: diarisation CPU-only d'un WAV")
    parser.add_argument("--cpu_diarize_out", type=str, help="Mode interne: sortie JSON segments")
    args = parser.parse_args()

    log_dir_path = Path(args.log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)
    global LOG_DIR_PATH
    LOG_DIR_PATH = log_dir_path
    log_file = log_dir_path / f"audio_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

    logging.info("--- Démarrage du script d'analyse audio (Diarisation) ---")

    _apply_audio_profile_from_env()

    try:
        os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "max_split_size_mb:32")

        env_disable_gpu = os.getenv("AUDIO_DISABLE_GPU", "0") == "1"
        use_cuda = torch.cuda.is_available() and not env_disable_gpu and not args.disable_gpu
        device = "cuda" if use_cuda else "cpu"
        if device == "cpu":
            cpu_workers_env = os.getenv("AUDIO_CPU_WORKERS")
            try:
                if cpu_workers_env:
                    n_threads = max(1, int(cpu_workers_env))
                    torch.set_num_threads(n_threads)
                    os.environ.setdefault("OMP_NUM_THREADS", str(n_threads))
                    os.environ.setdefault("MKL_NUM_THREADS", str(n_threads))
            except Exception:
                pass
        logging.info(f"Utilisation du device: {device}")

        hf_token = None
        if args.hf_auth_token:
            hf_token = args.hf_auth_token
            try:
                os.environ["HUGGINGFACE_HUB_TOKEN"] = args.hf_auth_token
            except Exception:
                pass
        else:
            hf_token = os.getenv("HUGGINGFACE_HUB_TOKEN") or os.getenv("HF_AUTH_TOKEN")

        if not hf_token:
            logging.critical(
                "Aucun token Hugging Face fourni. Passez --hf_auth_token ou définissez HUGGINGFACE_HUB_TOKEN/HF_AUTH_TOKEN."
            )
            sys.exit(1)
        try:
            from huggingface_hub import HfApi
            try:
                from huggingface_hub.hf_api import HfFolder
                HfFolder.save_token(hf_token)
            except Exception:
                pass
            _id = HfApi().whoami(token=hf_token)
            safe_tail = hf_token[-6:] if len(hf_token) >= 6 else "***"
            logging.info(
                "Authentifié sur Hugging Face (token tail=***%s) en tant que: %s",
                safe_tail,
                _id.get("name") or _id.get("email"),
            )
        except Exception as auth_e:
            logging.warning(
                "Impossible de valider le token Hugging Face: %s. On tente quand même le téléchargement.",
                auth_e,
            )

        pipeline = None
        try:
            pipeline = _load_pyannote_pipeline("pyannote/speaker-diarization-3.1", hf_token)
        except Exception as e_v3:
            logging.warning(f"Impossible de charger la pipeline v3.1: {e_v3}. Tentative avec v2...")
            try:
                pipeline = _load_pyannote_pipeline("pyannote/speaker-diarization", hf_token)
            except Exception as e_v2:
                logging.critical(
                    "Echec du chargement des pipelines pyannote (v3.1 et v2). "
                    "Le modèle peut être privé/gated. Assurez-vous que votre token HF a accès "
                    "(accepter les conditions sur la page du modèle) et réessayez."
                )
                logging.critical(f"Détails v3.1: {e_v3}")
                logging.critical(f"Détails v2: {e_v2}")
                sys.exit(1)
        optimal_tv_config = _load_optimal_tv_config()
        pyannote_batch_size = _get_pyannote_batch_size(device)
        if pyannote_batch_size is not None:
            for key in ("segmentation", "embedding"):
                section = optimal_tv_config.get(key)
                if not isinstance(section, dict):
                    optimal_tv_config[key] = {}
                optimal_tv_config[key]["batch_size"] = pyannote_batch_size

        if optimal_tv_config and hasattr(pipeline, "instantiate"):
            try:
                pipeline.instantiate(optimal_tv_config)
                if pyannote_batch_size is not None:
                    logging.info(
                        f"Pyannote configuration appliquée (optimal_tv_config + batch_size={pyannote_batch_size})"
                    )
                else:
                    logging.info("Pyannote configuration appliquée (optimal_tv_config)")
            except Exception as e:
                msg = str(e)
                if pyannote_batch_size is not None and "batch_size" in msg and "does not exist" in msg:
                    logging.info(
                        f"Pipeline.instantiate ne supporte pas batch_size (AUDIO_PYANNOTE_BATCH_SIZE={pyannote_batch_size}). "
                        "Le batch_size sera appliqué lors de l'appel diarization si possible."
                    )
                else:
                    logging.warning(f"Impossible d'appliquer optimal_tv_config.json via pipeline.instantiate: {e}")

                    if pyannote_batch_size is not None:
                        try:
                            pipeline.instantiate(
                                {
                                    "segmentation": {"batch_size": pyannote_batch_size},
                                    "embedding": {"batch_size": pyannote_batch_size},
                                }
                            )
                            logging.info(
                                "Fallback: configuration minimale appliquée (batch_size seulement) suite à un échec optimal_tv_config"
                            )
                        except Exception as fallback_e:
                            logging.warning(
                                "Fallback: impossible d'appliquer la configuration minimale (batch_size seulement): "
                                f"{fallback_e}"
                            )

        if _should_enable_amp(device):
            total_gb = _get_total_vram_gb()
            logging.info(f"AMP activé pour l'inférence (VRAM total ~{total_gb:.2f} GiB)")

        if args.cpu_diarize_wav:
            if not args.cpu_diarize_out:
                logging.critical("Mode cpu_diarize_wav: --cpu_diarize_out est requis")
                sys.exit(1)
            wav_path = Path(args.cpu_diarize_wav)
            out_path = Path(args.cpu_diarize_out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            diarization_kwargs = {"num_speakers": None}
            pyannote_batch_size = _get_pyannote_batch_size("cpu")
            if pyannote_batch_size is not None:
                diarization_kwargs["batch_size"] = pyannote_batch_size
                logging.info(f"CPU subprocess: batch_size={pyannote_batch_size}")
            
            with torch.inference_mode():
                try:
                    diarization = pipeline(str(wav_path), **diarization_kwargs)
                except TypeError as e:
                    if "batch_size" in str(e):
                        diarization_kwargs.pop("batch_size", None)
                        diarization = pipeline(str(wav_path), **diarization_kwargs)
                    else:
                        raise
            
            segments = [
                {"start": float(t.start), "end": float(t.end), "speaker": str(spk)}
                for t, _, spk in diarization.itertracks(yield_label=True)
            ]
            logging.info(f"CPU subprocess: {len(segments)} segment(s) extrait(s)")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(segments, f)
            return

        if pipeline is None:
            logging.critical(
                "Impossible de charger la pipeline pyannote (pipeline=None). Le modèle peut être privé/gated. "
                "Vérifiez votre token Hugging Face (HUGGINGFACE_HUB_TOKEN) et acceptez les conditions du modèle."
            )
            sys.exit(1)

        try:
            if hasattr(pipeline, "to"):
                pipeline.to(torch.device(device))
                logging.info(f"Pipeline de diarisation chargée avec succès sur {device}.")
            else:
                logging.info("Pipeline pyannote ne supporte pas .to(); continuation sans déplacement explicite de device.")
        except RuntimeError as e:
            if "NVIDIA driver" in str(e) or "CUDA" in str(e):
                logging.warning(f"GPU incompatible ({e}), fallback sur CPU.")
                device = "cpu"
                if hasattr(pipeline, "to"):
                    pipeline.to(torch.device("cpu"))
                logging.info("Pipeline de diarisation chargée avec succès sur CPU (fallback).")
            else:
                raise
    except ImportError as e:
        logging.critical(f"Erreur lors du chargement de la pipeline Pyannote: {e}")
        sys.exit(1)

    videos = find_videos_for_audio_analysis()
    total_videos = len(videos)
    logging.info(f"TOTAL_AUDIO_TO_ANALYZE: {total_videos}")

    if total_videos == 0:
        logging.info("Aucune nouvelle vidéo à analyser.")
        return

    successful_count = 0
    for i, video_path in enumerate(videos):
        logging.info(f"ANALYZING_AUDIO: {i + 1}/{total_videos}: {video_path.name}")

        success = analyze_audio_file(video_path, pipeline, hf_token, device)
        if success:
            successful_count += 1

        try:
            if device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    logging.info("--- Analyse audio terminée ---")
    logging.info(f"Résumé: {successful_count}/{total_videos} analyse(s) réussie(s).")

    if successful_count < total_videos:
        # Permettre un succès partiel si demandé (utile pour pipelines tolérantes)
        allow_partial = os.getenv("AUDIO_PARTIAL_SUCCESS_OK", "0") == "1"
        if allow_partial and successful_count > 0:
            logging.warning(
                f"Partial success autorisé: {successful_count}/{total_videos} analyses ont réussi. Code de sortie 0."
            )
            return
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Erreur critique non gérée: {e}", exc_info=True)
        sys.exit(1)