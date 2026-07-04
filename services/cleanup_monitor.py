#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup Background Monitor Service
Handles periodic continuous cleanup tasks in a background thread.
"""

import os
import time
import logging

from services.cleanup_service import CleanupService

logger = logging.getLogger(__name__)

def orphan_cleanup_service():
    """Service de nettoyage en arrière-plan (orphelins STEP8 & logs obsolètes). S'exécute toutes les 12 heures."""
    logger.info("CLEANUP MONITOR: Service de nettoyage continu démarré.")
    
    interval_seconds = 12 * 3600  # 12 heures
    threshold_hours = int(os.environ.get('CLEANUP_ORPHANS_THRESHOLD_HOURS', 48))
    
    # Premier nettoyage au bout de 5 minutes pour ne pas ralentir le démarrage
    time.sleep(300)
    
    while True:
        try:
            logger.info("CLEANUP MONITOR: Exécution périodique du nettoyage des projets orphelins et des logs obsolètes.")
            results = CleanupService.cleanup_orphan_projects(threshold_hours=threshold_hours, dry_run=False)
            if results.get("errors"):
                for err in results["errors"]:
                    logger.error(f"CLEANUP MONITOR Error: {err}")
            if results.get("cleaned_projects") or results.get("cleaned_logs"):
                logger.info(
                    f"CLEANUP MONITOR: {len(results['cleaned_projects'])} projet(s) et "
                    f"{len(results.get('cleaned_logs', []))} fichier(s) logs nettoyé(s). "
                    f"Espace libéré: {results['total_space_saved_human']}."
                )
        except Exception as e:
            logger.error(f"CLEANUP MONITOR: Erreur inattendue: {e}", exc_info=True)
            
        time.sleep(interval_seconds)
