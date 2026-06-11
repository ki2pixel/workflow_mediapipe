#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le routeur asynchrone Coral TPU (CoralTPUOrchestrator).
"""

import sys
import time
import threading
import pytest
from pathlib import Path

# Ajouter le chemin du projet pour résoudre les modules
BASE_PATH = Path(__file__).parent.parent.parent
if str(BASE_PATH) not in sys.path:
    sys.path.insert(0, str(BASE_PATH))

from services.coral_tpu_orchestrator import CoralTPUOrchestrator, tpu_orchestrator

class TestCoralTPUOrchestrator:
    """
    Validation du comportement du CoralTPUOrchestrator (Singleton et file asynchrone).
    """

    def test_singleton_pattern(self):
        # Given: Le CoralTPUOrchestrator est instancié une première fois
        instance_1 = CoralTPUOrchestrator()
        
        # When:  Une seconde instanciation est demandée
        instance_2 = CoralTPUOrchestrator()
        
        # Then:  Les deux instances sont strictement identiques (Singleton)
        assert instance_1 is instance_2
        assert instance_1 is tpu_orchestrator

    def test_submit_task_success(self):
        # Given: Une fonction synchrone simple
        def simple_task():
            return 42
            
        # When:  La tâche est soumise à l'orchestrateur
        result = tpu_orchestrator.submit_task(simple_task)
        
        # Then:  Le résultat est correctement retourné via la file asynchrone
        assert result == 42

    def test_submit_task_error_propagation(self):
        # Given: Une fonction qui lève une exception
        def error_task():
            raise ValueError("Test error propagation")
            
        # When:  La tâche est soumise
        # Then:  L'erreur est propagée et levée dans le thread appelant
        with pytest.raises(ValueError, match="Test error propagation"):
            tpu_orchestrator.submit_task(error_task)

    def test_sequential_execution(self):
        # Given: Deux tâches soumises, la première étant longue
        execution_order = []
        
        def task_1():
            time.sleep(0.1)
            execution_order.append(1)
            return True
            
        def task_2():
            execution_order.append(2)
            return True

        # When:  Les tâches sont soumises depuis des threads distincts
        def run_task(task_func):
            tpu_orchestrator.submit_task(task_func)

        t1 = threading.Thread(target=run_task, args=(task_1,))
        t2 = threading.Thread(target=run_task, args=(task_2,))

        # Lancer t1 puis t2 avec un petit délai pour garantir l'ordre d'entrée dans la queue
        t1.start()
        time.sleep(0.02)
        t2.start()

        t1.join()
        t2.join()
        
        # Then:  L'ordre d'exécution respecte la soumission séquentielle (FIFO)
        assert execution_order == [1, 2]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
