import numpy as np
from utils.one_euro_filter import OneEuroFilterND

def test_one_euro_initialization():
    """Vérifie l'initialisation du filtre 1 Euro."""
    filter_1e = OneEuroFilterND(dim=5)
    assert not filter_1e.is_initialized
    
    initial_val = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    res = filter_1e.update(initial_val)
    assert filter_1e.is_initialized
    np.testing.assert_array_equal(res, initial_val)

def test_one_euro_smoothing_at_rest():
    """Vérifie le fort lissage (faible cutoff) au repos (bruit)."""
    filter_1e = OneEuroFilterND(dim=1, rate=30.0, min_cutoff=0.1, beta=0.0) # beta=0 -> cutoff fixe à 0.1
    val = np.array([1.0])
    filter_1e.update(val)
    
    # Petit bruit autour de 1.0
    noisy_val = np.array([1.1])
    res = filter_1e.update(noisy_val)
    
    # Le résultat doit être fortement lissé (proche de 1.0, très loin de 1.1)
    assert res[0] < 1.05

def test_one_euro_reactivity_on_fast_movement():
    """Vérifie la faible latence (fort cutoff) en mouvement rapide."""
    filter_1e = OneEuroFilterND(dim=1, rate=30.0, min_cutoff=0.1, beta=10.0) # beta fort -> haute réactivité
    val = np.array([1.0])
    filter_1e.update(val)
    
    # Mouvement rapide
    fast_val = np.array([10.0])
    res = filter_1e.update(fast_val)
    
    # Le résultat doit être réactif (proche de 10.0)
    assert res[0] > 9.0

def test_one_euro_nd_dimensions():
    """Vérifie que les 52 dimensions sont traitées indépendamment."""
    filter_1e = OneEuroFilterND(dim=52, rate=30.0, min_cutoff=1.0, beta=1.0)
    
    val1 = np.zeros(52)
    val1[0] = 1.0 # Dim 0 bouge
    
    filter_1e.update(np.zeros(52)) # Init à 0
    res = filter_1e.update(val1)
    
    # Dim 0 a bougé, Dim 1 est restée à 0
    assert res[0] > 0.0
    assert res[1] == 0.0
