# Deployment Guide

**TL;DR**: Déployez votre modèle Mistral fine-tuné en production avec monitoring, versioning et rollback automatique via les scripts du projet.

Votre modèle fonctionne parfaitement en local, mais le déployer en production sans monitoring ni rollback vous expose à des pannes critiques. C'est le "Production Nightmare" - un modèle qui génère des commandes erronées en production avec aucun moyen de revenir en arrière.

## 🚀 Stratégie de Déploiement

### 1. Architecture de Production

```
Production Architecture
├── Load Balancer (nginx)
├── API Gateway (FastAPI)
├── Model Service (Mistral Fine-tuned)
├── Monitoring Stack (Prometheus + Grafana)
├── Logging Stack (ELK)
└── Backup/Restore System
```

### 2. Configuration Production

```yaml
# config/production.yaml
production:
  model:
    name: "workflow_mediapipe_v1"
    path: "mistral_finetuning/production/workflow_mediapipe_v1"
    version: "1.0.0"
    
  api:
    host: "0.0.0.0"
    port: 8000
    workers: 4
    timeout: 300
    
  monitoring:
    prometheus_port: 9090
    grafana_port: 3000
    log_level: "INFO"
    
  scaling:
    min_replicas: 2
    max_replicas: 10
    target_cpu_utilization: 70
    
  backup:
    schedule: "0 2 * * *"  # 2 AM daily
    retention_days: 30
```

## 📦 Model Packaging

### Export pour Production

```bash
# Export modèle optimisé
python scripts/export_model.py \
  --model_path mistral_finetuning/models/best_model \
  --export_path mistral_finetuning/production/workflow_mediapipe_v1 \
  --format onnx \
  --optimize \
  --quantize
```

### Dockerisation

```dockerfile
# Dockerfile.production
FROM nvidia/cuda:11.8-runtime-ubuntu20.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY mistral_finetuning/ /app/mistral_finetuning/
COPY requirements.txt /app/
WORKDIR /app

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Copy production model
COPY mistral_finetuning/production/ /app/models/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python3 scripts/health_check.py

# Start service
CMD ["python3", "scripts/production_server.py"]
```

## 🔧 Service API Production

### FastAPI Production Server

```python
# scripts/production_server.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from prometheus_client import Counter, Histogram, generate_latest

app = FastAPI(title="Workflow MediaPipe Assistant", version="1.0.0")

# Metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('api_request_latency_seconds', 'API request latency')
MODEL_INFERENCE_TIME = Histogram('model_inference_time_seconds', 'Model inference time')

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://workflow.yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load production model
model = load_production_model("workflow_mediapipe_v1")

@app.post("/api/v1/ask")
@REQUEST_LATENCY.time()
async def ask_question(request: QuestionRequest):
    """Endpoint principal pour questions techniques"""
    
    REQUEST_COUNT.labels(method="POST", endpoint="/ask").inc()
    
    try:
        start_time = time.time()
        
        # Validation entrée
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question vide")
        
        # Génération réponse
        with MODEL_INFERENCE_TIME.time():
            response = model.generate(request.question)
        
        # Validation sortie
        if not validate_technical_response(response):
            logging.warning(f"Réponse suspecte: {response[:100]}...")
        
        # Logging
        logging.info(f"Question: {request.question[:100]}...")
        logging.info(f"Response length: {len(response)} chars")
        
        return AnswerResponse(
            answer=response,
            model_version="workflow_mediapipe_v1",
            inference_time=time.time() - start_time
        )
        
    except Exception as e:
        logging.error(f"Erreur traitement question: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne")

@app.get("/metrics")
async def metrics():
    """Endpoint Prometheus pour monitoring"""
    return Response(generate_latest(), media_type="text/plain")

@app.get("/health")
async def health_check():
    """Health check pour load balancer"""
    
    try:
        # Test modèle
        test_response = model.generate("Test question")
        
        return {
            "status": "healthy",
            "model_loaded": True,
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")
```

## 📊 Monitoring Production

### Configuration Prometheus

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'workflow-mediapipe-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
    
  - job_name: 'workflow-mediapipe-model'
    static_configs:
      - targets: ['model:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

### Dashboard Grafana

```json
{
  "dashboard": {
    "title": "Workflow MediaPipe Model Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(api_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Model Inference Time",
        "type": "graph", 
        "targets": [
          {
            "expr": "histogram_quantile(0.95, model_inference_time_seconds)",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(api_requests_total{status=~\"5..\"}[5m]) / rate(api_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      }
    ]
  }
}
```

## 🔄 Versioning et Rollback

### Model Version Management

```python
# scripts/model_manager.py
class ModelManager:
    def __init__(self):
        self.models_dir = "mistral_finetuning/production"
        self.current_version = None
        self.load_current_version()
    
    def load_current_version(self):
        """Charge la version actuelle depuis metadata"""
        metadata_file = f"{self.models_dir}/current_version.json"
        
        if os.path.exists(metadata_file):
            with open(metadata_file) as f:
                metadata = json.load(f)
                self.current_version = metadata["version"]
    
    def deploy_model(self, model_path: str, version: str):
        """Déploie une nouvelle version du modèle"""
        
        try:
            # Backup version actuelle
            if self.current_version:
                self.backup_current_version()
            
            # Déploiement nouvelle version
            model_dir = f"{self.models_dir}/workflow_mediapipe_{version}"
            os.makedirs(model_dir, exist_ok=True)
            
            # Copie fichiers modèle
            shutil.copytree(model_path, f"{model_dir}/model")
            
            # Validation nouvelle version
            if not self.validate_model(model_dir):
                raise Exception("Validation échouée")
            
            # Mise à jour version courante
            self.update_current_version(version)
            
            # Redémarrage service
            self.restart_service()
            
            logging.info(f"✅ Modèle {version} déployé avec succès")
            
        except Exception as e:
            logging.error(f"❌ Échec déploiement {version}: {e}")
            # Rollback automatique
            if self.current_version:
                self.rollback_to_version(self.current_version)
            raise
    
    def rollback_to_version(self, version: str):
        """Rollback vers une version spécifique"""
        
        try:
            logging.info(f"🔄 Rollback vers version {version}")
            
            # Mise à jour metadata
            self.update_current_version(version)
            
            # Redémarrage service
            self.restart_service()
            
            # Validation rollback
            if self.validate_current_model():
                logging.info(f"✅ Rollback {version} réussi")
            else:
                raise Exception("Rollback validation échouée")
                
        except Exception as e:
            logging.error(f"❌ Rollback échoué: {e}")
            raise
    
    def validate_model(self, model_dir: str) -> bool:
        """Validation complète du modèle"""
        
        try:
            # Test chargement
            model = load_model_from_dir(f"{model_dir}/model")
            
            # Test inference
            test_questions = [
                "Comment exécuter STEP5 ?",
                "Quel environnement pour STEP4 ?"
            ]
            
            for question in test_questions:
                response = model.generate(question)
                
                # Validation technique
                if not validate_technical_response(response):
                    logging.warning(f"Réponse invalide: {question}")
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"Validation modèle échouée: {e}")
            return False
```

## 🛡️ Sécurité Production

### API Keys et Authentification

```python
# scripts/security.py
import jwt
from datetime import datetime, timedelta

class SecurityManager:
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        self.api_keys = self._load_api_keys()
    
    def generate_token(self, user_id: str) -> str:
        """Génère JWT token"""
        
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def verify_token(self, token: str) -> dict:
        """Vérifie JWT token"""
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expiré")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Token invalide")
    
    def validate_api_key(self, api_key: str) -> bool:
        """Valide API key"""
        return api_key in self.api_keys
```

### Rate Limiting

```python
# scripts/rate_limiter.py
import redis
from collections import defaultdict

class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.limits = {
            "default": {"requests": 100, "window": 3600},  # 100 req/hour
            "premium": {"requests": 1000, "window": 3600}  # 1000 req/hour
        }
    
    def is_allowed(self, user_id: str, tier: str = "default") -> bool:
        """Vérifie si utilisateur peut faire une requête"""
        
        limit_config = self.limits[tier]
        key = f"rate_limit:{user_id}"
        
        current = self.redis.get(key)
        if current is None:
            self.redis.setex(key, limit_config["window"], 1)
            return True
        
        if int(current) >= limit_config["requests"]:
            return False
        
        self.redis.incr(key)
        return True
```

## 📋 Checklist Déploiement

### Pré-déploiement
- [ ] Modèle validé avec métriques > 90%
- [ ] Tests de production passés
- [ ] Documentation mise à jour
- [ ] Backup version actuelle
- [ ] Monitoring configuré

### Post-déploiement
- [ ] Health checks OK
- [ ] Métriques monitoring actives
- [ ] Logs configurés
- [ ] Alerts configurées
- [ ] Documentation utilisateur mise à jour

### Monitoring Continu
- [ ] Request rate normal
- [ ] Latency < 2s
- [ ] Error rate < 1%
- [ ] Model inference time < 1s
- [ ] CPU usage < 80%

## 🎯 Golden Rule

**Deploy with rollback ready** : Toujours déployer avec un plan de rollback automatique. Un modèle en production qui génère des commandes erronées peut causer des dommages irréparables. La capacité à revenir en arrière en 30 secondes est plus importante que la nouvelle feature.

---

*Voir [Model Evaluation](model-evaluation.md) pour les métriques et [Training Pipeline](../technical/training-pipeline.md) pour la préparation des modèles.*
