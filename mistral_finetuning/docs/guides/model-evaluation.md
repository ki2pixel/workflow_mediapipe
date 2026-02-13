# Model Evaluation Guide

**TL;DR**: Évaluez votre modèle Mistral fine-tuné avec des métriques techniques (accuracy commandes, BLEU score, F1) et des tests de production sur des cas d'usage réels du pipeline.

Votre modèle s'est entraîné avec 99% de loss, mais quand vous testez "Comment exécuter STEP5 ?", il vous donne la commande Python système au lieu du chemin tracking_env_slim. C'est le "Training-Testing Gap" - des métriques parfaites qui masquent une incompétence technique.

## 📊 Métriques d'Évaluation

### 1. Technical Accuracy (Critique)

**Command Path Accuracy**
```python
def evaluate_command_accuracy(model, test_cases):
    """Évalue si les commandes générées utilisent les bons chemins d'environnement"""
    
    correct = 0
    total = len(test_cases)
    
    for case in test_cases:
        question = case["question"]
        expected_env = case["expected_environment"]
        expected_path = case["expected_path"]
        
        response = model.generate(question)
        
        # Vérification chemin environnement
        if expected_path in response and expected_env in response:
            correct += 1
        else:
            logger.error(f"❌ Command path incorrect: {question}")
            logger.error(f"Expected: {expected_path}")
            logger.error(f"Got: {response[:200]}...")
    
    return correct / total
```

**Test Cases Techniques**
```python
TECHNICAL_TEST_CASES = [
    {
        "question": "Comment exécuter STEP5 MediaPipe CPU ?",
        "expected_environment": "tracking_env_slim",
        "expected_path": "/mnt/venv_ext4/tracking_env_slim/bin/python",
        "required_keywords": ["mediapipe", "TRACKING_DISABLE_GPU=1"]
    },
    {
        "question": "Lancer STEP4 audio analysis",
        "expected_environment": "audio_env", 
        "expected_path": "/mnt/venv_ext4/audio_env/bin/python",
        "required_keywords": ["lemonfox", "ffmpeg"]
    },
    {
        "question": "Commande pour STEP3 TransNet",
        "expected_environment": "transnet_env",
        "expected_path": "/mnt/venv_ext4/transnet_env/bin/python",
        "required_keywords": ["transnetv2", "pytorch"]
    }
]
```

### 2. Semantic Similarity

**BLEU Score pour Réponses Techniques**
```python
import nltk
from nltk.translate.bleu_score import sentence_bleu

def evaluate_technical_bleu(model, test_cases):
    """BLEU score adapté pour contenu technique"""
    
    scores = []
    
    for case in test_cases:
        question = case["question"]
        reference = case["reference_answer"]
        
        candidate = model.generate(question)
        
        # Tokenisation technique
        ref_tokens = reference.split()
        cand_tokens = candidate.split()
        
        # BLEU avec poids sur termes techniques
        score = sentence_bleu([ref_tokens], cand_tokens, weights=(0.4, 0.3, 0.2, 0.1))
        scores.append(score)
    
    return sum(scores) / len(scores)
```

### 3. F1 Score sur Keywords Techniques

```python
def evaluate_keyword_f1(model, test_cases):
    """F1 score sur mots-clés techniques spécifiques"""
    
    total_tp = 0
    total_fp = 0  
    total_fn = 0
    
    for case in test_cases:
        question = case["question"]
        expected_keywords = set(case["required_keywords"])
        
        response = model.generate(question)
        response_lower = response.lower()
        
        # Extraction keywords
        found_keywords = set()
        for keyword in expected_keywords:
            if keyword.lower() in response_lower:
                found_keywords.add(keyword)
        
        # Calcul TP/FP/FN
        tp = len(found_keywords & expected_keywords)
        fp = len(found_keywords - expected_keywords)  
        fn = len(expected_keywords - found_keywords)
        
        total_tp += tp
        total_fp += fp
        total_fn += fn
    
    # F1 Score
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return f1, precision, recall
```

## 🧪 Tests de Production

### 1. Integration Tests

**Test Pipeline Complet**
```python
def test_pipeline_knowledge(model):
    """Test si le modèle comprend l'architecture complète"""
    
    pipeline_questions = [
        "Combien d'environnements virtuels dans ce projet ?",
        "Quel environnement pour STEP5 MediaPipe ?", 
        "Pourquoi les routes Flask sont minces ?",
        "Comment WorkflowState gère la concurrence ?",
        "Où sont stockés les logs de STEP4 ?"
    ]
    
    results = []
    
    for question in pipeline_questions:
        response = model.generate(question)
        
        # Évaluation par critères
        score = evaluate_response_quality(question, response)
        results.append({
            "question": question,
            "response": response,
            "score": score,
            "passes_threshold": score >= 0.7
        })
    
    return results
```

### 2. Error Diagnosis Tests

```python
def test_error_diagnosis(model):
    """Test capacité à diagnostiquer les erreurs courantes"""
    
    error_scenarios = [
        {
            "error": "ModuleNotFoundError: mediapipe",
            "expected_cause": "Environment Mismatch",
            "expected_solution": "Use tracking_env_slim"
        },
        {
            "error": "CUDA out of memory",
            "expected_cause": "GPU memory exceeded", 
            "expected_solution": "Reduce batch_size or use CPU"
        },
        {
            "error": "FileNotFoundError: videos_to_track.json",
            "expected_cause": "Missing input file",
            "expected_solution": "Create JSON file with video paths"
        }
    ]
    
    correct_diagnoses = 0
    
    for scenario in error_scenarios:
        question = f"J'ai cette erreur : {scenario['error']}. Que faire ?"
        response = model.generate(question)
        
        # Vérifier diagnostic correct
        if (scenario["expected_cause"].lower() in response.lower() and
            scenario["expected_solution"].lower() in response.lower()):
            correct_diagnoses += 1
    
    return correct_diagnoses / len(error_scenarios)
```

### 3. Code Generation Tests

```python
def test_code_generation(model):
    """Test génération de code correct selon les standards"""
    
    code_tasks = [
        {
            "task": "Créer un service avec injection FilesystemService",
            "expected_pattern": "class ServiceName:",
            "required_imports": ["FilesystemService"]
        },
        {
            "task": "Route Flask avec décorateur measure_api",
            "expected_pattern": "@measure_api",
            "required_imports": ["measure_api"]
        }
    ]
    
    valid_code = 0
    
    for task in code_tasks:
        response = model.generate(task["task"])
        
        # Validation syntaxique basique
        try:
            compile(response, '<string>', 'exec')
            syntax_valid = True
        except SyntaxError:
            syntax_valid = False
        
        # Vérification patterns
        pattern_found = task["expected_pattern"] in response
        imports_found = all(imp in response for imp in task["required_imports"])
        
        if syntax_valid and pattern_found and imports_found:
            valid_code += 1
    
    return valid_code / len(code_tasks)
```

## 📈 Reporting

### Dashboard d'Évaluation

```python
def generate_evaluation_report(model_name, metrics):
    """Génère un rapport d'évaluation complet"""
    
    report = f"""
# Évaluation Modèle : {model_name}

## 📊 Métriques Principales

| Métrique | Score | Seuil | Status |
|----------|-------|--------|--------|
| Technical Accuracy | {metrics['command_accuracy']:.2%} | 90% | {'✅' if metrics['command_accuracy'] >= 0.9 else '❌'} |
| BLEU Score | {metrics['bleu_score']:.3f} | 0.7 | {'✅' if metrics['bleu_score'] >= 0.7 else '❌'} |
| Keyword F1 | {metrics['keyword_f1']:.3f} | 0.8 | {'✅' if metrics['keyword_f1'] >= 0.8 else '❌'} |
| Error Diagnosis | {metrics['error_diagnosis']:.2%} | 85% | {'✅' if metrics['error_diagnosis'] >= 0.85 else '❌'} |
| Code Generation | {metrics['code_generation']:.2%} | 80% | {'✅' if metrics['code_generation'] >= 0.8 else '❌'} |

## 🔍 Analyse Détaillée

### Command Path Accuracy
- **Score** : {metrics['command_accuracy']:.2%}
- **Erreurs communes** : {metrics['common_command_errors']}

### Tests de Production  
- **Pipeline Knowledge** : {metrics['pipeline_knowledge']:.2%}
- **Error Diagnosis** : {metrics['error_diagnosis']:.2%}

## 🎯 Recommandations

{generate_recommendations(metrics)}
"""
    
    return report
```

### Recommendations Automatiques

```python
def generate_recommendations(metrics):
    """Génère des recommandations basées sur les métriques"""
    
    recommendations = []
    
    if metrics['command_accuracy'] < 0.9:
        recommendations.append(
            "🔧 **Command Path Accuracy faible** : "
            "Ajoutez plus d'exemples avec les chemins complets des environnements"
        )
    
    if metrics['keyword_f1'] < 0.8:
        recommendations.append(
            "📝 **Keywords manquants** : "
            "Enrichissez le dataset avec les termes techniques spécifiques au pipeline"
        )
    
    if metrics['error_diagnosis'] < 0.85:
        recommendations.append(
            "🐛 **Diagnostic erreurs** : "
            "Ajoutez des exemples de scénarios d'erreur et leurs solutions"
        )
    
    if metrics['code_generation'] < 0.8:
        recommendations.append(
            "💻 **Code Generation** : "
            "Ajoutez plus d'exemples de patterns Service Layer et routes Flask"
        )
    
    return "\n".join(recommendations)
```

## 🚀 Continuous Evaluation

### Monitoring en Production

```python
class ProductionMonitor:
    def __init__(self, model):
        self.model = model
        self.feedback_log = []
    
    def log_interaction(self, question, response, user_feedback=None):
        """Enregistre les interactions pour évaluation continue"""
        
        interaction = {
            "timestamp": datetime.now(),
            "question": question,
            "response": response,
            "user_feedback": user_feedback,
            "auto_score": self._auto_evaluate(question, response)
        }
        
        self.feedback_log.append(interaction)
        
        # Alert si performance dégrade
        if interaction["auto_score"] < 0.7:
            self._send_alert(interaction)
    
    def _auto_evaluate(self, question, response):
        """Évaluation automatique basique"""
        
        # Vérification présence commandes
        has_command = any(env in response for env in [
            "/mnt/venv_ext4/tracking_env_slim",
            "/mnt/venv_ext4/audio_env", 
            "/mnt/venv_ext4/transnet_env"
        ])
        
        # Vérification keywords techniques
        tech_keywords = ["WorkflowState", "FilesystemService", "AppState"]
        has_tech_content = any(keyword in response for keyword in tech_keywords)
        
        return 0.3 + (0.4 if has_command else 0) + (0.3 if has_tech_content else 0)
```

## 🎯 Golden Rule

**Technical accuracy over linguistic fluency** : Un modèle qui donne 95% des bonnes commandes avec un langage simple vaut mieux qu'un modèle élégant qui se trompe 50% du temps sur les chemins d'environnement. La précision technique est la seule métrique qui compte pour ce use-case.

---

*Voir [Training Pipeline](../technical/training-pipeline.md) pour l'entraînement et [Dataset Creation Guide](dataset-creation.md) pour la qualité des données.*
