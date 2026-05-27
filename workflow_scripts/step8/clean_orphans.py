#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de nettoyage autonome pour les dossiers projets temporaires orphelins (Étape 8).

Ce script peut être exécuté manuellement ou via un cron job système.
Il parcourt le dossier configuré pour les projets (`projets_extraits/`) et supprime 
les dossiers qui n'ont reçu aucune modification depuis un seuil d'heures (défaut: 48h).
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import config
from services.cleanup_service import CleanupService

# Configuration du Logger
LOG_DIR = config.LOGS_DIR / "step8"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"cleanup_orphans_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("CleanOrphansCLI")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Nettoyage des projets temporaires abandonnés/orphelins."
    )
    parser.add_argument(
        "--threshold-hours", 
        type=int, 
        default=48,
        help="Âge minimum d'inactivité en heures pour considérer un dossier comme orphelin (défaut: 48)."
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Simule le nettoyage sans rien supprimer."
    )
    return parser.parse_args()

def main():
    args = parse_args()
    
    logger.info("======================================================")
    logger.info("Démarrage du nettoyage des projets orphelins (STEP8)")
    logger.info("======================================================")
    
    try:
        results = CleanupService.cleanup_orphan_projects(
            threshold_hours=args.threshold_hours,
            dry_run=args.dry_run
        )
        
        if results.get("errors"):
            logger.warning(f"Le nettoyage s'est terminé avec {len(results['errors'])} erreur(s).")
            for err in results["errors"]:
                logger.error(err)
            sys.exit(1)
            
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Erreur critique lors du nettoyage: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
