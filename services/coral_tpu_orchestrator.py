import asyncio
import logging
import threading
from typing import Callable, Any

logger = logging.getLogger(__name__)

class CoralTPUOrchestrator:
    """
    Gestionnaire de queue asynchrone dédié au TPU Coral.
    Objectif: Traitement par micro-lots (batch processing) et sérialisation 
    des requêtes d'inférence (STEP3, STEP4, STEP5) pour préserver la SRAM de 8Mo 
    et éviter les évictions de cache coûteuses sur le bus PCIe.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CoralTPUOrchestrator, cls).__new__(cls)
                cls._instance._init_orchestrator()
            return cls._instance

    def _init_orchestrator(self):
        self.loop = asyncio.new_event_loop()
        self.queue = asyncio.Queue()
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="CoralTPU_AsyncLoop")
        self.thread.start()
        logger.info("[Coral TPU] Orchestrateur asynchrone initialisé.")

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._worker())

    async def _worker(self):
        logger.info("[Coral TPU] Worker de queue asynchrone démarré (Micro-lots / Sérialisation).")
        while True:
            func, future = await self.queue.get()
            try:
                # Exécution de la fonction bloquante dans un thread pour ne pas bloquer l'event loop TPU
                result = await self.loop.run_in_executor(None, func)
                if not future.done():
                    future.set_result(result)
            except Exception as e:
                logger.error(f"[Coral TPU] Erreur lors du traitement asynchrone: {e}")
                if not future.done():
                    future.set_exception(e)
            finally:
                self.queue.task_done()

    def submit_task(self, func: Callable[..., Any]) -> Any:
        """
        Soumet une fonction synchrone à la queue asynchrone du TPU et attend le résultat.
        Cela garantit que l'accès au TPU (ex: lancement d'un subprocess STEP3/4/5) 
        est sérialisé et orchestré.
        """
        future = asyncio.run_coroutine_threadsafe(self._enqueue(func), self.loop)
        return future.result()

    async def _enqueue(self, func: Callable[..., Any]):
        future = self.loop.create_future()
        await self.queue.put((func, future))
        return await future

# Instance singleton
tpu_orchestrator = CoralTPUOrchestrator()
