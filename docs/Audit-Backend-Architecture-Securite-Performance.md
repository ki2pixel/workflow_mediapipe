J'ai analysé en détail l'architecture, le code et la documentation de votre backend `workflow_mediapipe`. Votre application repose sur un pipeline en 8 étapes orchestré par Flask, avec une architecture orientée services (SOA) et une isolation très stricte des environnements Python.

Voici l'audit complet du backend, divisé en 5 axes majeurs : Architecture, Sécurité, Performance, Qualité du Code et Tests.

### 1. Architecture et Conception (Architecture & Design)

**Points forts :**

* **Isolation des environnements (Venvs) :** Le fait de séparer les dépendances par étape (`transnet_env`, `audio_env`, `tracking_env_slim`, etc.) est une excellente décision architecturale. Cela évite "l'enfer des dépendances" classique dans les projets d'IA où PyTorch, TensorFlow et ONNXRuntime entrent souvent en conflit.
* **Thin Controllers & Service Layer :** Les routes Flask (dans `api_routes.py` et `workflow_routes.py`) respectent parfaitement le pattern "Thin Controller". La logique est proprement déléguée aux services (`WorkflowService`, `CSVService`, `MonitoringService`), ce qui rend l'API facile à maintenir et à tester.
* **Gestion de l'état centralisée :** `WorkflowState` agit comme une source de vérité unique et thread-safe pour suivre l'avancement des 8 étapes. L'utilisation de verrous (`threading.Lock`/`RLock`) est correctement implémentée pour gérer la concurrence.

**Points d'attention (Axes d'amélioration) :**

* **Orchestration par `subprocess` :** Le système lance les étapes via `subprocess.run` en appelant les différents environnements virtuels. Bien que pragmatique et parfaitement adapté pour exploiter intensivement une station de travail multicœur performante (en tirant parti des threads disponibles sans subir le GIL de Python), cela limite la scalabilité horizontale. Si l'application devait évoluer vers du multi-serveurs, il faudrait migrer vers un broker de messages (comme Celery ou RabbitMQ).
* **Couplage au système de fichiers local :** Le passage de l'état et des données entre les étapes repose entièrement sur le système de fichiers (`projets_extraits/`). Une défaillance disque ou des problèmes de permissions NTFS/FUSE (bien que gérés de manière défensive dans STEP8) pourraient bloquer le pipeline.

### 2. Sécurité

**Points forts :**

* **Système de validation des tokens :** L'implémentation de `SecurityConfig` et des décorateurs `@require_internal_worker_token` est très propre. Les communications internes sont protégées.
* **Protection contre le Path Traversal :** La classe `FilenameSanitizer` et les validations dans l'extraction (STEP1) sont robustes. Le nettoyage des caractères dangereux, la normalisation Unicode (NFKC) et le blocage des chemins absolus (`../`) sécurisent bien la surface d'attaque face aux archives ZIP malveillantes.
* **Principe du Webhook-only :** Avoir retiré les connexions directes à MySQL/Airtable au profit d'un Webhook JSON unique réduit considérablement la surface d'attaque externe.

**Points d'attention :**

* **Valeurs de fallback en développement :** Dans `config/security.py` et `config/settings.py`, si `strict=False`, le système fallback sur des clés comme `dev-internal-worker-token` ou `dev-key-change-in-production`. Il faut s'assurer impérativement que l'application en production force `strict=True` pour empêcher un démarrage avec des secrets par défaut.
* **Commandes Shell :** Bien que les arguments passés aux sous-processus soient gérés via des listes en Python (ce qui évite l'injection shell directe), il faut rester vigilant sur les variables d'environnement injectées dynamiquement.

### 3. Performance et Optimisation des Ressources

**Points forts :**

* **Instrumentation intégrée :** Le décorateur `@measure_api` couplé au `PerformanceService` et au `MonitoringService` offre une excellente observabilité en temps réel (CPU, RAM, usage GPU).
* **Gestion des ressources adaptative :** Le pipeline gère très bien les limites matérielles. Le fallback automatique du GPU vers le CPU et la gestion du paramètre `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32` dans l'étape 4 sont vitaux pour éviter les erreurs "Out Of Memory" (OOM), particulièrement critiques avec des GPU disposant d'une VRAM modeste (4 Go par exemple).
* **Chunking Adaptatif (STEP5) :** Le découpage du traitement vidéo en petits blocs pour le multiprocessing MediaPipe optimise fortement l'usage mémoire tout en parallélisant efficacement le travail.

**Points d'attention :**

* **Goulets d'étranglement I/O :** L'étape 6 (Réduction JSON) et l'étape 7 (Pré-traitement AE) génèrent et lisent de très volumineux fichiers JSON. Sur des disques lents, cela va bloquer le CPU. L'implémentation actuelle d'écriture atomique avec des fichiers temporaires est sûre, mais génère une double écriture disque.

### 4. Qualité du Code et Maintenabilité

**Points forts :**

* **Configuration centralisée :** `config/settings.py` utilise les `dataclasses` intelligemment avec un `__post_init__` pour normaliser les chemins (`Path`). C'est robuste et typé.
* **Documentation "As Code" :** Les fichiers Markdown dans `docs/workflow/` sont remarquables. La documentation explique non seulement le *comment*, mais surtout le *pourquoi* (trade-offs, anti-patterns vs patterns recommandés).

**Points d'attention :**

* **Complexité Cyclomatique (Radon F) :** Comme documenté dans votre stratégie de tests, des fichiers comme `process_video_worker.py` (STEP5) et certaines méthodes du `CSVService` ont une très forte complexité logique. Le parsing des blendshapes, le merging des sources audio et la gestion des processus concurrents sont entremêlés. Un découpage en classes spécialisées plus petites dans ces workers faciliterait la maintenance future.

### 5. Tests et Fiabilité

**Points forts :**

* **Couverture stratégique :** Avec 173 tests et 89% de couverture mentionnés, l'effort de test est très mature. L'utilisation de `pytest`, des mocks pour les appels externes (Lemonfox, DeepInfra), et des fixtures sécurise bien les refactorisations.
* **Tests de Non-Régression :** La présence de tests spécifiques comme le warmup OpenCV (`test_step5_mp_seek_warmup.py`) ou le nettoyage des URLs à double-encodage démontre un excellent apprentissage post-mortem des bugs rencontrés.

**Points d'attention :**

* **Sensibilité de l'environnement de test :** L'exécution des tests dépend fortement de l'existence des sous-dossiers d'environnements (comme vérifié dans `diagnose_tests.sh`). Cela rend la CI/CD (si vous en mettez une en place) plus complexe à configurer, car il faudra provisionner tous les Venvs avant de lancer les tests complets.

---

### Recommandations Prioritaires (Plan d'Action)

1. **Refactorisation du Worker STEP5 :** Divisez `FrameProcessor.process_frame()` dans `process_video_worker.py`. Séparez l'extraction pure (MediaPipe), la logique métier de filtrage, et la construction du dictionnaire de sortie. Cela réduira la complexité de ce point névralgique.
2. **Sécurité en Production :** Ajoutez un contrôle bloquant au démarrage (par exemple dans `validate_startup.py`) qui fait crasher l'application si `DEBUG=False` et qu'un token par défaut est détecté. Actuellement, la classe `SecurityConfig` soulève un warning si `strict=False`.
3. **Optimisation I/O pour STEP6/STEP7 :** Si les fichiers JSON de tracking deviennent trop massifs, envisagez de streamer la lecture/écriture (par exemple via la librairie `ijson` en Python) au lieu de charger tout l'arbre DOM JSON en mémoire avec `json.load()`.
4. **Nettoyage continu :** Pour l'étape 8, assurez-vous qu'un mécanisme cron ou un worker asynchrone gère le nettoyage des dossiers temporaires abandonnés en cas de crash brutal du processus parent (qui échapperait au `finally` du script).

L'architecture est globalement d'excellente qualité, pragmatique et parfaitement dimensionnée pour un environnement de post-production exigeant. Le niveau d'isolation technique et de documentation est digne d'un standard d'entreprise.
