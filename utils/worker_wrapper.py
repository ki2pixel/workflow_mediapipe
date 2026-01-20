#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script wrapper qui adapte les arguments de run_with_monitoring.py aux arguments attendus
par process_video_worker_blendshapes_good_backup3.py
"""

import os
import sys
import argparse
import subprocess

def main():
    """
    Prend tous les arguments reçus et les passe directement à process_video_worker.
    """
    # Chemin vers le script worker final
    worker_script_path = os.path.join(
        os.path.dirname(__file__),
        "process_video_worker_blendshapes_good_backup3.py"
    )

    # La commande est simplement l'exécutable python, le script worker, et tous les arguments reçus
    # sys.argv[1:] contient tous les arguments passés au wrapper, y compris video_path.
    command = [
        sys.executable,
        worker_script_path,
    ] + sys.argv[1:]

    print(f"Wrapper: Lancement du worker avec la commande : {' '.join(command)}", file=sys.stderr)
    
    # Exécute le worker et retourne son code de sortie
    # Cela assure que la sortie (stdout/stderr) du worker est directement visible par le processus parent (run_with_monitoring)
    process = subprocess.Popen(command, stdout=sys.stdout, stderr=sys.stderr)
    process.wait()
    return process.returncode

if __name__ == "__main__":
    sys.exit(main())