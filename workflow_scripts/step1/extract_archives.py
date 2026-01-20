#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'extraction d'archives pour le workflow de traitement vidéo
Version Ubuntu - Étape 1 (Logique métier de la version originale préservée)
"""

import os
import sys
import shutil
import zipfile
import rarfile
import tarfile
import logging
import argparse
import re
import unicodedata
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.filename_security import FilenameSanitizer, validate_extraction_path

# --- Configuration des chemins et du logger ---
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
LOG_DIR = BASE_DIR / "logs" / "step1"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"extract_archives_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- Configuration du traitement ---
PROCESSED_ARCHIVES_FILE = LOG_DIR / "processed_archives.txt"
PROCESSED_ARCHIVES_RESET_MARKER = LOG_DIR / "processed_archives.last_reset"
WORK_DIR = BASE_DIR / "projets_extraits"
DELETE_ARCHIVE_AFTER_SUCCESS = True


def get_processed_archives():
    """Récupère la liste des archives déjà traitées."""
    if not PROCESSED_ARCHIVES_FILE.exists():
        return set()
    try:
        with open(PROCESSED_ARCHIVES_FILE, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip()}
    except Exception as e:
        logging.error(f"Erreur lecture du fichier des archives traitées: {e}")
        return set()


def reset_processed_archives_if_needed(now: datetime | None = None) -> bool:
    """Réinitialise mensuellement le fichier des archives traitées.

    Cette fonction s'assure qu'au changement de mois, le fichier
    `processed_archives.txt` est vidé pour éviter qu'une archive ayant
    le même nom de fichier soit ignorée d'un mois sur l'autre. Un
    marqueur de mois (`processed_archives.last_reset`) est utilisé pour
    savoir si une réinitialisation a déjà eu lieu pour le mois courant.

    Args:
        now: Date/heure à utiliser (principalement pour les tests). Si None, utilise l'heure courante.

    Returns:
        bool: True si une réinitialisation a eu lieu, False sinon (erreur ou déjà à jour).
    """
    try:
        current_dt = now or datetime.now()
        current_month = current_dt.strftime("%Y-%m")

        last_month_value = None
        if PROCESSED_ARCHIVES_RESET_MARKER.exists():
            try:
                last_month_value = PROCESSED_ARCHIVES_RESET_MARKER.read_text(encoding='utf-8').strip()
            except Exception as e:
                logging.warning(f"Impossible de lire le marqueur de réinitialisation: {e}")

        if last_month_value == current_month:
            return False

        if PROCESSED_ARCHIVES_FILE.exists() and PROCESSED_ARCHIVES_FILE.stat().st_size > 0:
            backup_name = LOG_DIR / (
                f"processed_archives_{last_month_value or 'previous'}_backup_"
                f"{current_dt.strftime('%Y%m%d_%H%M%S')}.txt"
            )
            try:
                shutil.copy2(PROCESSED_ARCHIVES_FILE, backup_name)
                logging.info(f"Réinitialisation mensuelle: sauvegarde créée '{backup_name.name}'.")
            except Exception as e:
                logging.error(f"Échec de sauvegarde avant réinitialisation: {e}")

            try:
                with open(PROCESSED_ARCHIVES_FILE, 'w', encoding='utf-8'):
                    pass
                logging.info("Réinitialisation mensuelle: fichier 'processed_archives.txt' vidé.")
            except Exception as e:
                logging.error(f"Impossible de vider le fichier processed_archives.txt: {e}")
        else:
            logging.info("Réinitialisation mensuelle: aucun contenu existant à sauvegarder.")

        try:
            PROCESSED_ARCHIVES_RESET_MARKER.write_text(current_month, encoding='utf-8')
            logging.info(f"Marqueur de réinitialisation mis à jour pour le mois: {current_month}")
        except Exception as e:
            logging.error(f"Impossible d'écrire le marqueur de réinitialisation: {e}")

        return True

    except Exception as e:
        logging.error(f"Erreur inattendue lors de la réinitialisation mensuelle: {e}")
        return False


def mark_archive_as_processed(archive_path):
    """Marque une archive comme traitée."""
    try:
        with open(PROCESSED_ARCHIVES_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{archive_path}\n")
    except Exception as e:
        logging.error(f"Erreur d'écriture dans le fichier des archives traitées: {e}")


def get_project_folder_name(archive_filename_str):
    """Dérive un nom de dossier de projet propre à partir du nom de l'archive."""
    name_without_ext = Path(archive_filename_str).stem
    parts = name_without_ext.split('_')
    folder_name_candidate = ""

    if parts[0].isdigit() and len(parts) > 1 and "camille" in parts[1].lower():
        folder_name_candidate = f"{parts[0]} {parts[1]}"
    elif "camille" in parts[0].lower():
        if len(parts) > 1 and parts[1].isalpha() and not parts[1].lower() == "camille":
            folder_name_candidate = f"{parts[0]} {parts[1]}"
        else:
            folder_name_candidate = parts[0]
    elif parts[0].isdigit() and len(parts) > 1 and parts[1].isalpha():
        folder_name_candidate = f"{parts[0]} {parts[1]}"
    else:
        folder_name_candidate = name_without_ext.replace("_", " ")

    clean_name = folder_name_candidate.strip()
    clean_name = re.sub(r'[<>:"/\\|?*&]', '_', clean_name)
    clean_name = re.sub(r'\s\s+', ' ', clean_name)
    clean_name = clean_name.strip('_ .')

    if not clean_name:
        logging.warning(f"Le nom de dossier pour '{archive_filename_str}' est vide. Utilisation d'un fallback.")
        fallback_name = re.sub(r'[<>:"/\\|?*&\s]', '_', Path(archive_filename_str).stem).strip('_')
        clean_name = f"projet_{fallback_name}" if fallback_name else "projet_sans_nom"
    return clean_name


def _format_timestamp(now: datetime | None = None) -> str:
    """Retourne un horodatage sans caractères interdits pour un nom de dossier.

    Format: YYYY-MM-DD_HH-MM-SS (ex: 2025-10-06_07-51-55)

    Args:
        now: Datetime à utiliser (principalement pour les tests). Si None, utilise datetime.now().

    Returns:
        str: Horodatage formaté.
    """
    dt = now or datetime.now()
    return dt.strftime("%Y-%m-%d_%H-%M-%S")


def compute_unique_project_dir(base_name: str, destination_base_dir: Path, now: datetime | None = None) -> Path:
    """Calcule un nom de dossier projet unique à créer sous destination_base_dir.

    - Ajoute un suffixe horodaté pour éviter les collisions entre projets portant le même nom logique (ex: "13 Camille").
    - En cas d'ultra-collision (même seconde), incrémente avec un compteur (-2, -3...).

    Exemple: base_name="13 Camille" => "13 Camille 2025-10-06_07-51-55"

    Args:
        base_name: Nom de base dérivé du fichier d'archive (déjà nettoyé).
        destination_base_dir: Dossier parent où créer le projet (ex: `projets_extraits/`).
        now: Datetime optionnelle pour tests.

    Returns:
        Path: Chemin complet du dossier unique (sans le sous-dossier "docs").
    """
    ts = _format_timestamp(now)
    candidate = destination_base_dir / f"{base_name} {ts}"

    if not candidate.exists():
        return candidate

        
    counter = 2
    while True:
        with_counter = destination_base_dir / f"{base_name} {ts}-{counter}"
        if not with_counter.exists():
            return with_counter
        counter += 1


def secure_extract_zip(zip_path, temp_extract_dir, sanitizer):
    """
    Securely extract ZIP archive with filename validation and path traversal protection.

    Args:
        zip_path: Path to ZIP file
        temp_extract_dir: Temporary extraction directory
        sanitizer: FilenameSanitizer instance

    Returns:
        tuple: (success: bool, security_issues_count: int)
    """
    security_issues_count = 0

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member_info in zip_ref.infolist():
                original_path = member_info.filename

                if original_path.endswith('/'):
                    continue

                sanitization_result = sanitizer.sanitize_archive_member_path(original_path)

                if sanitization_result.security_issues:
                    security_issues_count += len(sanitization_result.security_issues)
                    logging.warning(f"Security issues in ZIP member '{original_path}': {sanitization_result.security_issues}")

                if sanitization_result.was_modified:
                    logging.info(f"Sanitized ZIP member: '{original_path}' -> '{sanitization_result.sanitized_name}'")

                final_path = temp_extract_dir / sanitization_result.sanitized_name
                if not validate_extraction_path(sanitization_result.sanitized_name, temp_extract_dir):
                    logging.error(f"Unsafe extraction path detected, skipping: {original_path}")
                    security_issues_count += 1
                    continue

                final_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    with zip_ref.open(member_info) as source, open(final_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                except Exception as e:
                    logging.error(f"Failed to extract ZIP member '{original_path}': {e}")
                    continue

        return True, security_issues_count

    except Exception as e:
        logging.error(f"Error during secure ZIP extraction: {e}")
        return False, security_issues_count


def secure_extract_rar(rar_path, temp_extract_dir, sanitizer):
    """
    Securely extract RAR archive with filename validation and path traversal protection.

    Args:
        rar_path: Path to RAR file
        temp_extract_dir: Temporary extraction directory
        sanitizer: FilenameSanitizer instance

    Returns:
        tuple: (success: bool, security_issues_count: int)
    """
    security_issues_count = 0

    try:
        with rarfile.RarFile(rar_path, 'r') as rar_ref:
            for member_info in rar_ref.infolist():
                original_path = member_info.filename

                if member_info.is_dir():
                    continue

                sanitization_result = sanitizer.sanitize_archive_member_path(original_path)

                if sanitization_result.security_issues:
                    security_issues_count += len(sanitization_result.security_issues)
                    logging.warning(f"Security issues in RAR member '{original_path}': {sanitization_result.security_issues}")

                if sanitization_result.was_modified:
                    logging.info(f"Sanitized RAR member: '{original_path}' -> '{sanitization_result.sanitized_name}'")

                final_path = temp_extract_dir / sanitization_result.sanitized_name
                if not validate_extraction_path(sanitization_result.sanitized_name, temp_extract_dir):
                    logging.error(f"Unsafe extraction path detected, skipping: {original_path}")
                    security_issues_count += 1
                    continue

                final_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    with rar_ref.open(member_info) as source, open(final_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                except Exception as e:
                    logging.error(f"Failed to extract RAR member '{original_path}': {e}")
                    continue

        return True, security_issues_count

    except Exception as e:
        logging.error(f"Error during secure RAR extraction: {e}")
        return False, security_issues_count


def secure_extract_tar(tar_path, temp_extract_dir, sanitizer):
    """
    Securely extract TAR archive with filename validation and path traversal protection.

    Args:
        tar_path: Path to TAR file
        temp_extract_dir: Temporary extraction directory
        sanitizer: FilenameSanitizer instance

    Returns:
        tuple: (success: bool, security_issues_count: int)
    """
    security_issues_count = 0

    try:
        with tarfile.open(tar_path, 'r:*') as tar_ref:
            for member_info in tar_ref.getmembers():
                original_path = member_info.name

                if member_info.isdir():
                    continue

                if not member_info.isfile():
                    logging.warning(f"Skipping non-regular file in TAR: {original_path}")
                    security_issues_count += 1
                    continue

                sanitization_result = sanitizer.sanitize_archive_member_path(original_path)

                if sanitization_result.security_issues:
                    security_issues_count += len(sanitization_result.security_issues)
                    logging.warning(f"Security issues in TAR member '{original_path}': {sanitization_result.security_issues}")

                if sanitization_result.was_modified:
                    logging.info(f"Sanitized TAR member: '{original_path}' -> '{sanitization_result.sanitized_name}'")

                final_path = temp_extract_dir / sanitization_result.sanitized_name
                if not validate_extraction_path(sanitization_result.sanitized_name, temp_extract_dir):
                    logging.error(f"Unsafe extraction path detected, skipping: {original_path}")
                    security_issues_count += 1
                    continue

                final_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    with tar_ref.extractfile(member_info) as source, open(final_path, 'wb') as target:
                        if source:  # extractfile can return None for some members
                            shutil.copyfileobj(source, target)
                except Exception as e:
                    logging.error(f"Failed to extract TAR member '{original_path}': {e}")
                    continue

        return True, security_issues_count

    except Exception as e:
        logging.error(f"Error during secure TAR extraction: {e}")
        return False, security_issues_count


def extract_archive(archive_path, destination_base_dir):
    """Extrait une archive de manière sécurisée, gère les sous-dossiers et nettoie."""
    project_folder_name = get_project_folder_name(archive_path.name)
    # Le dossier final contiendra un sous-dossier "docs" pour la cohérence avec les étapes suivantes
    final_destination = destination_base_dir / project_folder_name / "docs"
    temp_extract_dir = destination_base_dir / f"_temp_{project_folder_name}_{int(time.time())}"

    # Initialize security sanitizer
    sanitizer = FilenameSanitizer()
    total_security_issues = 0

    try:
        logging.info(f"Extraction sécurisée de {archive_path.name} vers {final_destination}")

        # 1. Extraire dans un dossier temporaire avec validation de sécurité
        temp_extract_dir.mkdir(parents=True, exist_ok=True)

        suffix = archive_path.suffix.lower()
        extraction_success = False

        if suffix in ('.zip', '.zipx'):
            logging.info(f"Extraction ZIP sécurisée de {archive_path.name}")
            extraction_success, security_issues = secure_extract_zip(archive_path, temp_extract_dir, sanitizer)
            total_security_issues += security_issues
        elif suffix == '.rar':
            logging.info(f"Extraction RAR sécurisée de {archive_path.name}")
            extraction_success, security_issues = secure_extract_rar(archive_path, temp_extract_dir, sanitizer)
            total_security_issues += security_issues
        elif suffix in ('.tar', '.gz', '.bz2', '.xz', '.tgz'):
            logging.info(f"Extraction TAR sécurisée de {archive_path.name}")
            extraction_success, security_issues = secure_extract_tar(archive_path, temp_extract_dir, sanitizer)
            total_security_issues += security_issues
        else:
            logging.warning(f"Format non supporté: {archive_path}")
            return False

        if not extraction_success:
            logging.error(f"Échec de l'extraction sécurisée pour {archive_path.name}")
            return False

        # Log security statistics
        stats = sanitizer.get_stats()
        logging.info(f"Statistiques de sécurité pour {archive_path.name}: "
                    f"{stats['total_processed']} fichiers traités, "
                    f"{stats['modified_count']} modifiés, "
                    f"{total_security_issues} problèmes de sécurité détectés")

        if total_security_issues > 0:
            logging.warning(f"ATTENTION: {total_security_issues} problèmes de sécurité détectés dans {archive_path.name}")

        # Vérifier qu'il y a des fichiers extraits
        extracted_items = list(temp_extract_dir.rglob('*'))
        if not extracted_items:
            logging.warning(f"Aucun fichier extrait de {archive_path.name}")
            return False

        # 2. Nettoyer les fichiers inutiles de l'extraction (ex: __MACOSX)
        macosx_junk = temp_extract_dir / "__MACOSX"
        if macosx_junk.exists() and macosx_junk.is_dir():
            logging.info("Suppression du dossier __MACOSX.")
            shutil.rmtree(macosx_junk)

        # 3. Gérer les cas où le ZIP contient un seul dossier racine
        items_in_temp = list(temp_extract_dir.iterdir())
        source_content_root = temp_extract_dir
        if len(items_in_temp) == 1 and items_in_temp[0].is_dir():
            logging.info(f"Le ZIP contient un seul dossier racine '{items_in_temp[0].name}'. Utilisation comme source.")
            source_content_root = items_in_temp[0]

        # 4. Déplacer le contenu vers la destination finale
        final_destination.mkdir(parents=True, exist_ok=True)
        for item_to_move in source_content_root.iterdir():
            target_path = final_destination / item_to_move.name
            if target_path.exists():
                logging.warning(f"'{target_path.name}' existe déjà dans la destination. Il sera écrasé.")
                if target_path.is_dir():
                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()
            shutil.move(str(item_to_move), str(target_path))

        logging.info(f"Extraction terminée pour {archive_path.name}")
        return True

    except (zipfile.BadZipFile, rarfile.BadRarFile, tarfile.ReadError) as e:
        logging.error(f"Erreur: Fichier archive corrompu ou invalide - {archive_path.name}: {e}")
        return False
    except Exception as e:
        logging.error(f"Erreur inattendue lors de l'extraction de {archive_path.name}: {e}")
        return False
    finally:
        # 5. Nettoyer le dossier temporaire
        if temp_extract_dir.exists():
            shutil.rmtree(temp_extract_dir)


def find_archives_to_process(source_dir):
    """Trouve les archives non encore traitées et contenant le mot-clé 'Camille'."""
    processed = get_processed_archives()
    archives = []
    keyword = "Camille"

    if not source_dir.exists():
        logging.warning(f"Le dossier d'archives '{source_dir}' n'existe pas.")
        return []

    logging.info(f"Recherche des archives dans '{source_dir}' avec le mot-clé '{keyword}'...")

    archive_extensions = ('.zip', '.zipx', '.rar', '.tar.gz', '.tgz', '.tar.bz2', '.tar.xz', '.7z', '.tar')
    for archive in source_dir.iterdir():
        if archive.is_file() and archive.suffix.lower() in archive_extensions:
            if keyword.lower() in archive.name.lower() and str(archive.resolve()) not in processed:
                archives.append(archive)
                logging.info(f"Archive correspondante trouvée: {archive.name}")

    return archives


def main():
    parser = argparse.ArgumentParser(description="Script d'extraction d'archives intelligent.")
    parser.add_argument('--source-dir', type=str, required=True,
                        help="Spécifie le répertoire où chercher les archives.")
    args = parser.parse_args()

    source_archives_dir = Path(args.source_dir)
    logging.info(f"--- Démarrage du script d'extraction d'archives ---")
    logging.info(f"Dossier source: {source_archives_dir.resolve()}")
    logging.info(f"Dossier de destination des projets: {WORK_DIR.resolve()}")

    WORK_DIR.mkdir(parents=True, exist_ok=True)

    # Réinitialisation mensuelle du fichier des archives traitées (si nécessaire)
    try:
        did_reset = reset_processed_archives_if_needed()
        if did_reset:
            logging.info("Réinitialisation mensuelle exécutée (ou marqueur mis à jour).")
        else:
            logging.info("Aucune réinitialisation mensuelle nécessaire.")
    except Exception as e:
        logging.error(f"Échec de la vérification de réinitialisation mensuelle: {e}")

    archives = find_archives_to_process(source_archives_dir)
    total_to_process = len(archives)
    logging.info(f"Trouvé {total_to_process} nouvelle(s) archive(s) à traiter.")
    print(f"Trouvé {total_to_process} archive(s) à traiter")  # Pour l'UI

    if total_to_process == 0:
        logging.info("Aucune nouvelle archive à traiter. Fin du script.")
        return

    successful_count = 0
    for i, archive in enumerate(archives):
        logging.info(f"--- Traitement {i + 1}/{total_to_process}: {archive.name} ---")

        success = extract_archive(archive, WORK_DIR)

        if success:
            successful_count += 1
            mark_archive_as_processed(str(archive.resolve()))
            if DELETE_ARCHIVE_AFTER_SUCCESS:
                try:
                    archive.unlink()
                    logging.info(f"Archive source '{archive.name}' supprimée avec succès.")
                except Exception as e:
                    logging.error(f"Impossible de supprimer l'archive source '{archive.name}': {e}")
        else:
            logging.error(f"L'extraction de '{archive.name}' a échoué. Voir les logs précédents.")

    logging.info(f"--- Traitement terminé ---")
    logging.info(f"Résumé: {successful_count}/{total_to_process} archive(s) extraite(s) avec succès.")

    if successful_count < total_to_process:
        sys.exit(1)  # Quitter avec un code d'erreur s'il y a eu des échecs


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Erreur critique non gérée dans le script: {e}")
        sys.exit(1)