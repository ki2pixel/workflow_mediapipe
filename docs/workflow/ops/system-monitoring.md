# Monitoring Système - CPU/RAM/GPU et Instrumentation API

**TL;DR** : Service de monitoring système avec instrumentation API et widget frontend optimisé. Support GPU conditionnel et mode minimisé.

## Le Problème : Monitoring Système Fragmenté

Tu as besoin de surveiller les ressources système (CPU, RAM, GPU) mais les métriques sont dispersées, non instrumentées et sans interface unifiée. Tu as besoin d'un système de monitoring complet avec performance tracking.

## Notre Solution : Service Centralisé avec Instrumentation

Nous utilisons `MonitoringService` pour agréger toutes les métriques système avec instrumentation API automatique. Le frontend dispose d'un widget optimisé avec mode minimisé et backoff adaptatif.

### ❌ Monitoring fragmenté (anti-pattern)
```python
# Approche inefficace - métriques dispersées
def get_cpu():
    return psutil.cpu_percent()  # Isolé

def get_memory():
    return psutil.virtual_memory()  # Isolé

def get_gpu():
    return nvidia_smi()  # Isolé, pas de fallback
# Résultat : pas d'agrégation, pas d'instrumentation, pas d'interface unifiée
```

### ✅ Service centralisé (pattern recommandé)
```python
# Approche optimisée - agrégation complète
class MonitoringService:
    def get_system_status(self):
        return {
            "cpu": self._get_cpu_info(),
            "memory": self._get_memory_info(),
            "gpu": self._get_gpu_info() if config.ENABLE_GPU_MONITORING else None,
            "disk": self._get_disk_info()
        }
# Résultat : agrégation, instrumentation, interface unifiée, fallback GPU
```

### Flux de Monitoring

1. **Collecte** : CPU, RAM, GPU, disque via `MonitoringService`
2. **Instrumentation** : Décorateur `@measure_api` sur tous les endpoints
3. **Agrégation** : Métriques temporelles via `PerformanceService`
4. **Affichage** : Widget frontend avec DOM batching et backoff adaptatif
5. **Cache** : Cache-busting CSS pour mises à jour immédiates

## Trade-offs par Mode de Monitoring

| Mode | Performance | Couverture | Complexité | Quand l'utiliser |
|------|-------------|-----------|------------|-----------------|
| **Centralisé** | Optimisée | Complète | Moyenne | Production standard |
| **Distribué** | Variable | Maximale | Élevée | Systèmes distribués |
| **Minimal** | Maximale | Critique | Simple | Systèmes légers |
| **Aucun** | Maximale | Aucune | Minimale | Développement rapide |

## Trade-offs par Stratégie de Frontend

| Stratégie | Performance | UX | Complexité | Quand l'utiliser |
|-----------|-------------|----|------------|-----------------|
| **Widget complet** | Moyenne | Maximale | Moyenne | Production, monitoring complet |
| **Mode minimisé** | Optimisée | Réduite | Simple | Production, espace limité |
| **Backoff adaptatif** | Variable | Bonne | Moyenne | Production, réseau instable |
| **Polling fixe** | Variable | Moyenne | Simple | Développement, debug |

## Analogie : Tableau de Bord vs Compteur de Vitesse

Pense au monitoring comme un **tableau de bord** vs un **compteur de vitesse**. Le **MonitoringService** est le tableau de bord : il affiche toutes les métriques importantes (CPU, RAM, GPU, disque) en un seul coup d'œil. Le **widget frontend** est le compteur de vitesse : il montre les informations essentielles en temps réel avec mode compact pour économiser de l'espace. L'**instrumentation API** est le système de télémétrie : chaque requête est enregistrée pour analyse post-mortem.

## Frontend - Widget de Monitoring

### Composant Principal

```javascript
// static/components/SystemMonitor.js
class SystemMonitor {
    constructor() {
        this.isMinimized = false;
        this.pollingManager = new PollingManager();
        this.domBatcher = new DOMBatcher();
    }
    
    async startMonitoring() {
        // Backoff adaptatif
        this.pollingManager.startPolling('/api/system_monitor', {
            interval: 2000,
            backoff: true,
            callback: (data) => this.updateDisplay(data)
        });
    }
    
    updateDisplay(data) {
        // DOM batching pour éviter les reflows
        this.domBatcher.scheduleUpdate(() => {
            this.updateCPU(data.cpu);
            this.updateMemory(data.memory);
            this.updateGPU(data.gpu);
        });
    }
    
    toggleMinimized() {
        this.isMinimized = !this.isMinimized;
        this.domBatcher.scheduleUpdate(() => {
            this.render();
        });
    }
}
```

### Mode Minimisé

```javascript
// Mode compact sur une seule ligne
renderMinimized() {
    const cpu = this.data.cpu.percent.toFixed(1);
    const memory = `${this.data.memory.used_mb}MB/${this.data.memory.total_mb}MB`;
    const gpu = this.data.gpu ? `${this.data.gpu.utilization.toFixed(1)}%` : 'N/A';
    const temp = this.data.gpu ? `${this.data.gpu.temperature}°C` : '';
    
    this.element.innerHTML = `
        <div class="system-monitor-compact">
            <span class="cpu">CPU: ${cpu}%</span>
            <span class="memory">RAM: ${memory}</span>
            <span class="gpu">GPU: ${gpu} ${temp}</span>
            <button class="toggle" onclick="systemMonitor.toggleMinimized()">×</button>
        </div>
    `;
}
```

## Configuration Essentielle

### Variables d'Environnement

```bash
# Monitoring
ENABLE_GPU_MONITORING=true
SYSTEM_MONITOR_POLLING_INTERVAL=2000
SYSTEM_MONITOR_BACKOFF_ENABLED=true

# Performance
API_PERFORMANCE_SAMPLE_RATE=1.0
PERFORMANCE_METRICS_RETENTION_HOURS=24

# Frontend
CACHE_BUSTER=20240120_143022
DOM_BATCHING_ENABLED=true
```

### Configuration Service

```python
# config/settings.py
class Config:
    ENABLE_GPU_MONITORING = os.getenv('ENABLE_GPU_MONITORING', 'false').lower() == 'true'
    SYSTEM_MONITOR_POLLING_INTERVAL = int(os.getenv('SYSTEM_MONITOR_POLLING_INTERVAL', '2000'))
    CACHE_BUSTER = os.getenv('CACHE_BUSTER', 'default')
```

## Performance et Optimisations

### Backoff Adaptatif

```javascript
// PollingManager avec backoff
class PollingManager {
    startPolling(url, options = {}) {
        const {
            interval = 2000,
            backoff = true,
            maxInterval = 30000,
            callback
        } = options;
        
        const poll = async () => {
            try {
                const response = await fetch(url);
                const data = await response.json();
                callback(data);
                
                // Reset backoff on success
                this.currentInterval = interval;
            } catch (error) {
                // Exponential backoff
                if (backoff) {
                    this.currentInterval = Math.min(
                        this.currentInterval * 1.5,
                        maxInterval
                    );
                }
            }
            
            setTimeout(poll, this.currentInterval);
        };
        
        poll();
    }
}
```

### DOM Batching

```javascript
// DOMBatcher pour éviter les reflows
class DOMBatcher {
    constructor() {
        this.updates = [];
        this.scheduled = false;
    }
    
    scheduleUpdate(updateFn) {
        this.updates.push(updateFn);
        
        if (!this.scheduled) {
            this.scheduled = true;
            requestAnimationFrame(() => {
                this.updates.forEach(fn => fn());
                this.updates = [];
                this.scheduled = false;
            });
        }
    }
}
```

### Cache-Busting CSS

```html
<!-- templates/index_new.html -->
<link rel="stylesheet" href="/static/css/components/system-monitor.css?v={{ cache_buster }}">
```

## Monitoring GPU

### Support Conditionnel

```python
def _get_gpu_info(self) -> Optional[dict]:
    """Informations GPU si disponible."""
    if not config.ENABLE_GPU_MONITORING:
        return None
    
    try:
        import pynvml
        pynvml.nvmlInit()
        
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        
        return {
            "utilization": util.gpu,
            "temperature": temp,
            "memory_used_mb": mem.used / 1024 / 1024,
            "memory_total_mb": mem.total / 1024 / 1024,
            "memory_percent": (mem.used / mem.total) * 100
        }
    except Exception as e:
        logger.warning(f"GPU monitoring failed: {e}")
        return None
```

## Tests et Validation

### Tests Backend

```python
# tests/unit/test_monitoring_service.py
def test_get_system_status():
    """Test agrégation métriques système."""
    status = monitoring_service.get_system_status()
    
    assert "timestamp" in status
    assert "cpu" in status
    assert "memory" in status
    assert "disk" in status
    
    # GPU optionnel
    if config.ENABLE_GPU_MONITORING:
        assert "gpu" in status
    else:
        assert status.get("gpu") is None

def test_get_process_info():
    """Test informations processus."""
    info = monitoring_service.get_process_info()
    
    assert "pid" in info
    assert "uptime_seconds" in info
    assert "memory_mb" in info
    assert info["uptime_seconds"] > 0
```

### Tests d'Intégration

```python
# tests/integration/test_system_monitor.py
def test_system_monitor_endpoint():
    """Test endpoint monitoring avec instrumentation."""
    response = client.get('/api/system_monitor')
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert "timestamp" in data
    assert "cpu" in data
    assert "memory" in data
```

### Tests Frontend

```javascript
// tests/frontend/test_system_monitor.mjs
export function test_system_monitor_widget() {
    const monitor = new SystemMonitor();
    
    // Test mode minimisé
    monitor.toggleMinimized();
    assert monitor.isMinimized === true;
    
    // Test DOM batching
    const updateCount = monitor.domBatcher.updates.length;
    monitor.updateDisplay({cpu: {percent: 50}});
    assert updateCount > 0;
}
```

## Résolution de Problèmes

### GPU Non Disponible

```bash
# Diagnostic
nvidia-smi
python -c "import pynvml; pynvml.nvmlInit()"

# Solution
# Activer ENABLE_GPU_MONITORING=true
# Installer pynvml si nécessaire
# Le système fonctionne sans GPU (grâce au support conditionnel)
```

### Performance Widget

```bash
# Diagnostic
# Surveiller le temps de réponse du widget
# Vérifier le nombre de reflows dans DevTools

# Solution
# Activer DOM batching
# Utiliser backoff adaptatif
# Réduire la fréquence de polling
```

### Instrumentation API

```bash
# Diagnostic
curl http://localhost:5000/api/performance/metrics

# Solution
# Vérifier que @measure_api est appliqué
# Activer API_PERFORMANCE_SAMPLE_RATE=1.0
# Vérifier PerformanceService.record_api_response_time()
```

## Sécurité

### Aucun Secret dans le Code

```python
# ✅ Correct
def get_system_status():
    """Agrégation métriques système."""
    # Utilise config.settings.config
    return {
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory()._asdict()
    }

# ❌ Incorrect
def get_system_status():
    """Agrégation métriques système."""
    # Pas de secrets en dur
    return {"api_key": "secret-key-here"}
```

### Aucune Commande Dangereuse

```python
# ✅ Correct
def get_system_info():
    """Informations système sécurisées."""
    return psutil.cpu_percent()

# ❌ Incorrect
def get_system_info():
    """Commande dangereuse."""
    return os.system("cat /proc/cpuinfo")  # Non sécurisé
```

## Intégration Pipeline

### Position dans l'Architecture

```mermaid
graph TD
    A[MonitoringService] --> B[PerformanceService]
    C[GPU Monitoring] --> A
    D[System Monitor Widget] --> E[Frontend]
    
    subgraph "API"
        F[/api/system_monitor] --> A
        G[/api/performance/metrics] --> B
    end
    
    A --> F
    B --> G
    E --> D
```

### Flux de Données

```python
# Pipeline → Monitoring → Performance → Frontend
system_metrics → monitoring_service.get_system_status() → performance_service.record_api_response_time() → frontend_widget
```

## Pièges Courants et Solutions

### Piège #1 : GPU Non Disponible
**Solution** : Support conditionnel via `ENABLE_GPU_MONITORING` et fallback gracieux.

### Piège #2 : Widget Lent
**Solution** : DOM batching et backoff adaptatif pour réduire les reflows.

### Piège #3 : Métriques Non Instrumentées
**Solution** : Décorateur `@measure_api` sur tous les endpoints et `PerformanceService`.

### Piège #4 : Cache CSS Ancien
**Solution** : Cache-busting avec `?v={{ cache_buster }}` dans les liens CSS.

### Piège #5 : Polling Trop Fréquent
**Solution** : Backoff adaptatif et intervalles configurables.

L'architecture de monitoring transforme les métriques système dispersées en une solution unifiée et performante. Le service backend agrège toutes les données avec instrumentation automatique, et le frontend dispose d'un widget optimisé avec mode minimisé et backoff adaptatif. Le système offre maintenant une visibilité complète sur les ressources avec une interface fluide et réactive.

---

## Golden Rule

**Agrège avant d'afficher ; sinon tu obtiens des métriques fragmentées qui ne racontent pas la même histoire et qui induisent en erreur l'opérateur.**
