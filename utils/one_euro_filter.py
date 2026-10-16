"""
One-Euro Filter — Lissage temporel adaptatif pour Blendshapes ARKit.
Numba @njit pour compilation LLVM, fallback NumPy si indisponible.
"""
import numpy as np
import math

try:
    from numba import njit
except ImportError:
    # Fallback if numba is not installed
    def njit(*args, **kwargs):
        def wrapper(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return wrapper

@njit(cache=True)
def _smoothing_factor(t_e, cutoff):
    r = 2.0 * math.pi * cutoff * t_e
    return r / (r + 1.0)

@njit(cache=True)
def _smoothing_factors(t_e, cutoffs, out):
    """Version vectorisée : un seul appel JIT pour les N coefficients (au lieu de N appels)."""
    for i in range(cutoffs.shape[0]):
        r = 2.0 * math.pi * cutoffs[i] * t_e
        out[i] = r / (r + 1.0)

@njit(cache=True)
def _exponential_smoothing(a, x, x_prev):
    return a * x + (1.0 - a) * x_prev

class OneEuroFilterND:
    """
    Filtre 1 Euro pour signaux N-dimensionnels (ex: 52 blendshapes).
    Filtre passe-bas adaptatif :
    - Au repos (faible vélocité) : cutoff faible = fort lissage anti-jitter
    - En mouvement rapide : cutoff élevé = faible lissage pour réactivité sans lag
    """
    def __init__(self, dim=52, rate=30.0, min_cutoff=1.0, beta=0.007, d_cutoff=1.0):
        self.dim = dim
        self.rate = rate
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev = np.zeros(dim, dtype=np.float64)
        self.dx_prev = np.zeros(dim, dtype=np.float64)
        self._alpha = np.empty(dim, dtype=np.float64)
        self.is_initialized = False
    
    def update(self, x):
        """Met à jour le filtre avec le vecteur courant et retourne le vecteur lissé."""
        x = np.asarray(x, dtype=np.float64)
        if not self.is_initialized:
            self.x_prev = x.copy()
            self.is_initialized = True
            return x.copy()
        
        t_e = 1.0 / self.rate
        
        # 1. Estimation de la vélocité (dérivée temporelle)
        a_d = _smoothing_factor(t_e, self.d_cutoff)
        dx = (x - self.x_prev) / t_e
        dx_hat = _exponential_smoothing(a_d, dx, self.dx_prev)
        
        # 2. Adaptation du cutoff en fonction de la vélocité
        cutoff = self.min_cutoff + self.beta * np.abs(dx_hat)
        
        # 3. Lissage exponentiel avec le nouveau cutoff : un seul appel JIT pour
        #    les N coefficients, calculé dans un buffer préalloué.
        a = self._alpha[: x.shape[0]]
        _smoothing_factors(t_e, cutoff, a)
        x_hat = _exponential_smoothing(a, x, self.x_prev)
        
        # Mémorisation
        self.x_prev = x_hat.copy()
        self.dx_prev = dx_hat.copy()
        
        return x_hat
