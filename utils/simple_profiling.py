import time
from collections import defaultdict
from contextlib import contextmanager

# Dictionnaire global pour stocker les statistiques de profilage
PROFILING_STATS = defaultdict(lambda: {"total_time": 0, "calls": 0})


@contextmanager
def profile_section(section_name):
    """Un context manager pour profiler une section de code."""
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed_time = (time.perf_counter() - start_time) * 1000  # en ms
        PROFILING_STATS[section_name]["total_time"] += elapsed_time
        PROFILING_STATS[section_name]["calls"] += 1


def reset_profiling_stats():
    """Réinitialise les statistiques de profilage."""
    global PROFILING_STATS
    PROFILING_STATS = defaultdict(lambda: {"total_time": 0, "calls": 0})


# Créer un alias pour maintenir la compatibilité avec le worker
reset_profiling = reset_profiling_stats


def get_profiling_stats_dict():
    """Retourne une copie des statistiques actuelles."""
    return {k: dict(v) for k, v in PROFILING_STATS.items()}


def print_profiling_stats(logger_fn=print):
    """Affiche un résumé formaté des statistiques de profilage."""
    if not PROFILING_STATS:
        logger_fn("Aucune donnée de profilage collectée.")
        return

    logger_fn("\n--- PROFILING RESULTS (Detailed) ---")

    # Calcul du temps total pour le pourcentage
    total_time_all_sections = sum(
        stats["total_time"] for stats in PROFILING_STATS.values()
    )
    if total_time_all_sections == 0:
        logger_fn(
            "Temps total de profilage est zéro. Impossible de calculer les pourcentages."
        )
        total_time_all_sections = 1  # Pour éviter la division par zéro

    # Tri par temps total décroissant
    sorted_stats = sorted(
        PROFILING_STATS.items(), key=lambda item: item[1]["total_time"], reverse=True
    )

    logger_fn(
        f"{'Section':<30} | {'Total Time (ms)':>15} | {'Calls':>10} | {'Avg Time (ms)':>15} | {'% of Total':>10}"
    )
    logger_fn("-" * 85)

    for name, stats in sorted_stats:
        total_ms = stats["total_time"]
        calls = stats["calls"]
        avg_ms = total_ms / calls if calls > 0 else 0
        percentage = (total_ms / total_time_all_sections) * 100

        logger_fn(
            f"{name:<30} | {total_ms:>15.2f} | {calls:>10} | {avg_ms:>15.4f} | {percentage:>9.2f}%"
        )
    logger_fn("-" * 85)
