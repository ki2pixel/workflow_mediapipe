#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de finalisation et copie des projets vers la destination finale.
Étape 7 (Ubuntu)
\- Archive d'abord les artefacts d'analyse (scènes/tracking/audio) avant suppression
\- Copie ensuite le dossier du projet vers la destination finale
"""

import os
import errno
import sys
import json
import shutil
import logging
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import config
from services.results_archiver import ResultsArchiver, SCENES_SUFFIX, AUDIO_SUFFIX, TRACKING_SUFFIX, VIDEO_METADATA_NAME

# --- Configuration ---
WORK_DIR = Path(os.getcwd())
# --- MODIFICATION: Changer la destination ---
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/mnt/cache"))
# --- FIN DE LA MODIFICATION ---
FINALIZE_MODE = os.environ.get("FINALIZE_MODE", "lenient").lower()
BASE_DIR = ROOT_DIR
LOG_DIR = BASE_DIR / "logs" / "step7"

# --- Configuration du Logger ---
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"finalize_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)


def find_projects_to_finalize():
    """Trouve tous les projets dans WORK_DIR qui sont prêts à être finalisés."""
    projects = []
    logging.info(f"Recherche de projets à finaliser dans: {WORK_DIR}")

    for project_dir in WORK_DIR.iterdir():
        if not project_dir.is_dir() or project_dir.name.startswith("_temp_"):
            continue

        is_ready = False
        found_reason = ""
        for video_file in project_dir.rglob("*.mp4"):
            stem = video_file.stem
            scenes_csv = next(project_dir.rglob(f"{stem}{SCENES_SUFFIX}"), None)
            tracking_json = next(project_dir.rglob(f"{stem}{TRACKING_SUFFIX}"), None)
            audio_json = next(project_dir.rglob(f"{stem}{AUDIO_SUFFIX}"), None)
            if FINALIZE_MODE == "strict":
                if scenes_csv and scenes_csv.exists() and tracking_json and tracking_json.exists():
                    found_reason = f"artefacts scènes+tracking pour '{video_file.name}'"
                    is_ready = True
                    break
            elif FINALIZE_MODE == "videos":
                found_reason = f"vidéo présente '{video_file.name}'"
                is_ready = True
                break
            else:
                if (scenes_csv and scenes_csv.exists()) or (tracking_json and tracking_json.exists()) or (audio_json and audio_json.exists()):
                    found_reason = f"au moins un artefact pour '{video_file.name}'"
                    is_ready = True
                    break

        if is_ready:
            logging.info(f"Projet '{project_dir.name}' est prêt ({found_reason}). Mode: {FINALIZE_MODE}")
            projects.append(project_dir)
        else:
            logging.info(f"Projet '{project_dir.name}' ignoré (mode={FINALIZE_MODE}). Aucune vidéo/artefact requis trouvés.")

    return projects


def _is_dir_writable(path: Path) -> bool:
    """Teste la capacité d'écriture/suppression dans un répertoire cible.

    Plus fiable que os.access() sur des montages FUSE/NTFS.
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=str(path), delete=True) as tmp:
            tmp.write(b"writable-check")
            tmp.flush()
        return True
    except Exception:
        return False


def _select_output_dir(preferred: Path, base_dir: Path) -> Path:
    """Sélectionne une destination inscriptible, avec repli si nécessaire.

    - Utilise `preferred` si inscriptible.
    - Sinon, utilise `FALLBACK_OUTPUT_DIR` si défini et inscriptible.
    - Sinon, utilise `base_dir / "_finalized_output"`.
    """
    if _is_dir_writable(preferred):
        logging.info(f"Destination vérifiée: '{preferred}' est inscriptible")
        return preferred

    logging.warning(
        f"La destination préférée '{preferred}' n'est pas inscriptible (montage RO ? permissions ?). "
        "Activation d'une destination de repli."
    )

    env_fallback = os.environ.get("FALLBACK_OUTPUT_DIR")
    if env_fallback:
        fb = Path(env_fallback)
        if _is_dir_writable(fb):
            logging.warning(f"Bascule vers FALLBACK_OUTPUT_DIR: '{fb}'")
            return fb
        else:
            logging.warning(f"FALLBACK_OUTPUT_DIR défini mais non inscriptible: '{fb}'")

    local_fb = base_dir / "_finalized_output"
    local_fb.mkdir(parents=True, exist_ok=True)
    logging.warning(f"Bascule vers le répertoire de repli local: '{local_fb}'")
    return local_fb


def _safe_rmtree(path: Path) -> None:
    """Supprime un dossier en consignant proprement les erreurs de permissions."""
    def _onerror(func, p, exc_info):
        logging.error(f"Suppression échouée sur '{p}': {exc_info[1]}")
    shutil.rmtree(path, onerror=_onerror)


def _destination_supports_chmod(dest_dir: Path) -> bool:
    """Détecte si le FS destination supporte chmod (NTFS typiquement renvoie EPERM).
    
    Si on ne peut pas créer de fichier, la question du chmod est secondaire; laisser True.
    """
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=str(dest_dir), delete=True) as tmp:
            try:
                os.chmod(tmp.name, 0o664)
            except PermissionError:
                return False
            except OSError as e:
                err = getattr(e, 'errno', None)
                if err in (errno.EPERM, errno.EACCES, getattr(errno, 'EOPNOTSUPP', None)):
                    return False
                raise
    except Exception:
        return True


def _copy_project_tree(src: Path, dst: Path) -> None:
    """Copie le projet sans préserver les permissions sur FS type NTFS.

    Stratégie:
    - Si chmod supporté: utiliser shutil.copytree (comportement standard).
    - Sinon: tenter rsync --no-perms/owner/group; à défaut cp --no-preserve; à défaut copie Python manuelle.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    supports_chmod = _destination_supports_chmod(dst)
    if supports_chmod:
        shutil.copytree(src, dst, dirs_exist_ok=True)
        return

    logging.info("Destination ne supporte pas chmod — copie sans préservation des permissions.")
    # 1) rsync si disponible
    try:
        subprocess.run([
            "rsync", "-a", "--no-perms", "--no-owner", "--no-group", "--no-times",
            f"{str(src)}/", f"{str(dst)}/"
        ], check=True)
        return
    except FileNotFoundError:
        logging.info("rsync non disponible, tentative via cp --no-preserve")
    except subprocess.CalledProcessError as e:
        logging.warning(f"rsync a échoué: {e}")

    # 2) cp --no-preserve si disponible (fusionner le contenu dans dst)
    try:
        dst.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "bash", "-lc",
            f"cp -r --no-preserve=mode,ownership '{str(src)}/.' '{str(dst)}/'"
        ], check=True)
        return
    except subprocess.CalledProcessError as e:
        logging.warning(f"cp --no-preserve a échoué: {e}")

    # 3) Fallback Python: os.walk et shutil.copyfile sans copystat
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target_dir = dst / rel if rel != "." else dst
        target_dir.mkdir(parents=True, exist_ok=True)
        for d in dirs:
            (target_dir / d).mkdir(parents=True, exist_ok=True)
        for f in files:
            s = Path(root) / f
            t = target_dir / f
            shutil.copyfile(s, t)


def _compute_alternative_output_dir(existing_dst: Path) -> Path:
    """Calcule un répertoire de sortie alternatif si `existing_dst` ne peut pas être supprimé.

    Ex.: /mnt/cache/33 Camille -> /mnt/cache/33 Camille__finalized_YYYYmmdd_HHMMSS[_n]
    """
    base = existing_dst.parent
    name = existing_dst.name
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    candidate = base / f"{name}__finalized_{ts}"
    i = 1
    while candidate.exists():
        candidate = base / f"{name}__finalized_{ts}_{i}"
        i += 1
    return candidate


def _normalize_project_docs_structure(dst_project_dir: Path) -> None:
    """Ensure destination project has a docs/ subfolder containing media and related files.

    If files are currently at the project root (common when previous steps didn't use a docs/
    directory), move recognized media and analysis files into docs/.
    """
    docs_dir = dst_project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    media_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".png", ".jpg", ".jpeg"}
    analysis_suffixes = {SCENES_SUFFIX, AUDIO_SUFFIX, TRACKING_SUFFIX}

    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    video_stems: set[str] = set()
    try:
        for p in dst_project_dir.iterdir():
            if p.is_file() and p.suffix.lower() in video_exts:
                video_stems.add(p.stem)
        if docs_dir.exists():
            for p in docs_dir.rglob("*"):
                if p.is_file() and p.suffix.lower() in video_exts:
                    video_stems.add(p.stem)
    except Exception:
        pass

    for entry in dst_project_dir.iterdir():
        if entry.name == "docs":
            continue
        if entry.is_file():
            ext = entry.suffix.lower()
            stem = entry.stem
            move = False
            if ext in media_exts:
                move = True
            else:
                for suf in analysis_suffixes:
                    if entry.name.endswith(suf) or entry.name == f"{stem}.csv":
                        move = True
                        break
                if not move and ext == ".json" and stem in video_stems:
                    move = True
            if move:
                target = docs_dir / entry.name
                try:
                    if target.exists():
                        target.unlink()
                    shutil.move(str(entry), str(target))
                except Exception as e:
                    logging.warning(f"Impossible de déplacer '{entry}' vers '{target}': {e}")


def restore_archived_analysis(project_name: str, output_project_dir: Path) -> None:
    """Restore archived analysis artifacts into the destination project docs/ folder.

    For each detected video file in docs/, attempt to retrieve archived artifacts
    (scenes CSV, audio JSON, tracking JSON) using ResultsArchiver and copy them next to the video.
    """
    try:
        docs_dir = output_project_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        video_exts = (".mp4", ".mov", ".avi", ".mkv", ".webm")
        videos = []
        if docs_dir.exists():
            videos.extend([p for p in docs_dir.rglob("*") if p.is_file() and p.suffix.lower() in video_exts])
        videos.extend([p for p in output_project_dir.iterdir() if p.is_file() and p.suffix.lower() in video_exts])

        for v in videos:
            target_dir = docs_dir if v.parent != docs_dir else v.parent
            stem = v.stem

            scenes_path = ResultsArchiver.find_analysis_file(project_name, v, SCENES_SUFFIX)
            if scenes_path:
                dst = target_dir / f"{stem}{SCENES_SUFFIX}"
                try:
                    shutil.copy2(scenes_path, dst)
                except Exception as e:
                    logging.warning(f"Restauration scenes échouée {scenes_path} -> {dst}: {e}")

            audio_path = ResultsArchiver.find_analysis_file(project_name, v, AUDIO_SUFFIX)
            if audio_path:
                dst = target_dir / f"{stem}{AUDIO_SUFFIX}"
                try:
                    shutil.copy2(audio_path, dst)
                except Exception as e:
                    logging.warning(f"Restauration audio échouée {audio_path} -> {dst}: {e}")

            tracking_path = ResultsArchiver.find_analysis_file(project_name, v, TRACKING_SUFFIX)
            if tracking_path:
                dst = target_dir / f"{stem}{TRACKING_SUFFIX}"
                try:
                    shutil.copy2(tracking_path, dst)
                except Exception as e:
                    logging.warning(f"Restauration tracking échouée {tracking_path} -> {dst}: {e}")
    except Exception as e:
        logging.warning(f"Restauration des analyses archivées échouée (projet={project_name}): {e}")

def finalize_project(project_dir):
    """Copie un projet vers la destination finale et supprime la source."""
    try:
        project_name = project_dir.name
        logging.info(f"Finalisation du projet: {project_name}")
        print(f"Finalisation en cours pour '{project_name}'...")

        # 1) Archiver d'abord tous les artefacts d'analyse disponibles
        try:
            arch_summary = ResultsArchiver.archive_project_analysis(project_name)
            if arch_summary and not arch_summary.get("error"):
                logging.info(
                    "Archivage des analyses terminé: %s",
                    json.dumps({k: arch_summary.get(k) for k in ("processed", "copied")}, ensure_ascii=False)
                )
            else:
                logging.warning(f"Archivage des analyses non effectué ou en erreur: {arch_summary}")
        except Exception as e:
            logging.warning(f"Erreur lors de l'archivage des analyses du projet '{project_name}': {e}")

        output_project_dir = OUTPUT_DIR / project_name

        if output_project_dir.exists():
            logging.warning(
                f"Le dossier de destination '{output_project_dir}' existe déjà. Tentative de suppression avant copie."
            )
            _safe_rmtree(output_project_dir)
            if output_project_dir.exists():
                alt_dir = _compute_alternative_output_dir(output_project_dir)
                logging.warning(
                    f"Impossible de supprimer la destination existante. Bascule vers: '{alt_dir}'"
                )
                output_project_dir = alt_dir

        try:
            _copy_project_tree(project_dir, output_project_dir)
        except Exception as e:
            logging.error("Erreur lors de la copie du projet: %s", e, exc_info=True)
            raise
        logging.info(f"Projet '{project_name}' copié avec succès vers '{output_project_dir}'")

        _normalize_project_docs_structure(output_project_dir)

        if os.environ.get("RESTORE_ARCHIVES_TO_OUTPUT", "0") in ("1", "true", "True"):
            try:
                restore_archived_analysis(project_name, output_project_dir)
            except Exception as e:
                logging.warning(f"Restauration des analyses archivées échouée: {e}")

        # --- Suppression du dossier source (après archivage) ---
        try:
            project_dir.resolve().relative_to(config.ARCHIVES_DIR.resolve())
            logging.error(f"Refus de suppression: '{project_dir}' est sous ARCHIVES_DIR")
            return False
        except Exception:
            pass
        _safe_rmtree(project_dir)
        logging.info(f"Dossier source '{project_dir}' supprimé avec succès.")
        # --- FIN suppression ---

        # --- MODIFICATION: Suppression de la création du fichier metadata_final.json ---
        # --- FIN DE LA MODIFICATION ---

        logging.info(f"Finalisation terminée pour '{project_name}'")
        print(f"Finalisation terminée pour '{project_name}'")
        return True

    except Exception as e:
        logging.error(f"Erreur lors de la finalisation du projet {project_dir.name}: {e}", exc_info=True)
        return False


def main():
    """Fonction principale du script."""
    logging.info(f"--- Démarrage du script de Finalisation et Nettoyage ---")

    global OUTPUT_DIR
    try:
        OUTPUT_DIR = _select_output_dir(OUTPUT_DIR, BASE_DIR)
        logging.info(f"Le répertoire de destination est: {OUTPUT_DIR.resolve()}")
    except Exception as e:
        logging.critical(
            f"Impossible de préparer un répertoire de destination inscriptible. Erreur: {e}"
        )
        sys.exit(1)

    projects = find_projects_to_finalize()
    total_projects = len(projects)
    logging.info(f"{total_projects} projet(s) à finaliser")
    print(f"{total_projects} projet(s) à finaliser")

    if total_projects == 0:
        logging.info("Aucun projet à finaliser. Fin du script.")
        return

    successful_count = 0
    for project in projects:
        if finalize_project(project):
            successful_count += 1

    logging.info(f"--- Finalisation terminée ---")
    logging.info(f"Résumé: {successful_count}/{total_projects} projet(s) finalisé(s) et déplacé(s) avec succès.")

    if successful_count < total_projects:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Erreur critique non gérée dans le script de finalisation: {e}", exc_info=True)
        sys.exit(1)