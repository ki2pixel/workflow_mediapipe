## 1. Analyse des possibilités Lightning.ai

### Reformulation du besoin fonctionnel exact
Le besoin n’est **pas** de “mettre STEP5 dans le cloud”, mais de **déporter uniquement la branche InsightFace GPU** de STEP5 vers Lightning.ai, tout en conservant **strictement MediaPipe comme moteur par défaut, CPU-only local** via `tracking_env_slim`. L’architecture actuelle est déjà compatible avec cette séparation : `run_tracking_manager.py` force déjà **InsightFace = GPU-only** et **MediaPipe = CPU-only**, pilotés par `STEP5_ENABLE_GPU`, `STEP5_TRACKING_ENGINE` et `STEP5_GPU_ENGINES`; `WorkflowCommandsConfig` pointe STEP5 vers `tracking_env_slim`; `app_new.py` prépare les vidéos STEP5 via `WorkflowService.prepare_tracking_step()` puis injecte `--videos_json_path` au manager.

### Option A — Studio Lightning.ai GPU persistant piloté comme machine distante
**Principe** : un Studio GPU sert de “machine distante STEP5 InsightFace”, pilotable via SSH/CLI/SDK, avec environnement persistant et stockage durable. C’est l’option la plus proche d’un **remote worker** sans refonte. La doc Lightning confirme qu’un Studio est un environnement persistant avec SSH, IDE, stockage et environnement durable, plus automatisable via SDK/CLI.

**Avantages**
- Très bon alignement avec l’architecture actuelle : on garde le pipeline local et on remplace seulement l’exécution de la branche InsightFace.
- Environnement persistant : une fois `insightface`, `onnxruntime-gpu`, CUDA providers et modèles validés, on évite la dérive de setup à chaque run.
- Très simple pour le debug initial : accès SSH, VSCode, logs, tests manuels.
- Facile à piloter avec `lightning studio start/stop/ssh/cp` ou SDK `Studio.start()/run()`.
- Permet une intégration incrémentale via un nouveau mode local de type `remote_lightning` sans casser `WorkflowCommandsConfig`.

**Limites**
- Lancement distant moins “industrialisé” qu’un vrai job batch.
- Nécessite de gérer le transfert des entrées/sorties et éventuellement le nettoyage de workspace.
- Coût potentiellement moins optimisé si le Studio reste réveillé trop longtemps.
- Reprise/idempotence à encadrer côté projet local.

**Complexité** : faible à moyenne.
**Pertinence MVP** : excellente.

### Option B — Studio de préparation + Batch Job Lightning à la demande
**Principe** : on prépare et valide l’environnement dans un Studio, puis on soumet l’exécution réelle de STEP5 InsightFace via `Job.run(...)` ou `lightning run job`, en réutilisant l’environnement Studio “forké” à la soumission. La doc Lightning confirme que le Job peut réutiliser un environnement de Studio incluant code, dépendances, data et variables, ou un Docker image si on veut plus d’isolation.

**Avantages**
- Plus robuste pour l’exploitation récurrente : exécution non interactive, mieux adaptée aux traitements ponctuels ou par lots.
- Réduction de la dérive d’environnement si on soumet depuis un Studio de référence validé.
- Meilleure base pour l’industrialisation et la parallélisation ultérieure.
- Job files / Drive / artifacts adaptés à la récupération d’outputs JSON, logs et métriques.

**Limites**
- Un peu plus de complexité d’orchestration locale : soumission, suivi du job, polling du statut, récupération finale.
- Cold start probable plus visible qu’un Studio déjà prêt.
- Besoin de formaliser un dossier d’entrée/sortie plus propre qu’en Option A.

**Complexité** : moyenne.
**Pertinence MVP** : bonne, mais plutôt en phase 2.

### Option C — Service/API distante hébergée sur Lightning
**Principe** : encapsuler InsightFace dans une API distante déployée depuis Studio snapshot ou via un service/déploiement Lightning. La doc “Deploy a Studio” montre qu’un Studio snapshot peut être converti en déploiement monitoré/autoscalé; les docs déploiement/API montrent aussi une voie serveur/LitServe.

**Avantages**
- Contrat d’appel clair à terme : upload, job submit, polling/callback, download résultat.
- Bonne base si plusieurs clients/pipelines doivent mutualiser le moteur InsightFace.
- Potentiel d’autoscaling et de versioning plus propre qu’un pilotage SSH brut.

**Limites**
- C’est l’option qui ajoute le plus de surface d’architecture : contrat d’API, auth, upload, latence réseau, stockage temporaire, lifecycle des jobs.
- Le pipeline local devrait gérer davantage de logique protocolaire qu’avec A/B.
- Risque de sur-ingénierie pour un besoin initial centré sur STEP5.

**Complexité** : élevée.
**Pertinence MVP** : faible.

### Option D — BYOC / multi-cloud / reserved GPUs
**Principe** : activer BYOC, VPC privé, GPUs réservés, preprovisioning ou multi-cloud seulement si la contrainte réelle le justifie. La doc Lightning indique que BYOC sert à garder les données dans le cloud du client, utiliser les crédits cloud, renforcer conformité/sécurité/régionalisation; reserved garantit la capacité; preprovisioning réduit les cold starts au prix d’un coût continu.

**Avantages**
- Justifié si sécurité/réglementation/quotas/engagements cloud imposent que les données vidéo ne sortent pas du périmètre.
- Reserved/preprovisioning utile si disponibilité GPU ou délai de démarrage deviennent bloquants.
- Multi-cloud utile si certaines familles GPU sont fréquemment indisponibles.

**Limites**
- Forte hausse de complexité ops, gouvernance et coût de mise en place.
- Pas nécessaire pour un MVP technique.
- Nécessite souvent arbitrages org, quotas, régions, tagging, sécurité, IAM.

**Complexité** : élevée à très élevée.
**Pertinence MVP** : faible, sauf contrainte entreprise explicite.

### Comparatif structuré
| Option | Intégration archi existante | Refactor local | Latence/coût | Sync I/O | Tolérance aux pannes / reprise | Mode d’usage idéal | Compatibilité InsightFace/CUDA | Simplicité opérateur |
|---|---|---:|---|---|---|---|---|---|
| A Studio persistant | Très bonne | Faible | Coût bon si arrêt auto; faible latence si studio chaud | Simple via Drive/CLI/SSH | Moyenne, à compléter côté projet | interactif, semi-automatisé | Très bonne | Très bonne |
| B Studio + Batch Job | Bonne | Faible à moyenne | Meilleur pour usage ponctuel/batch, mais cold start | Très bonne via job files/Drive | Bonne | batch, automatisé, ponctuel | Très bonne | Bonne |
| C API distante | Moyenne | Moyenne à forte | Latence réseau + coût service permanent possible | Complexe (upload/download/API) | Bonne si bien conçue | multi-clients, industrialisation avancée | Bonne | Moyenne |
| D BYOC / reserved | Bonne mais lourde | Moyenne à forte | Pertinent si quota/stockage/sécu; sinon surcoût | Bonne | Très bonne si correctement opéré | prod contrainte, conformité | Très bonne | Faible à moyenne |

### Lecture pragmatique
- **MVP le plus simple** : **Option A**.
- **Trajectoire d’industrialisation naturelle** : **Option B**.
- **Option C** seulement si le moteur devient un service partagé.
- **Option D** uniquement si conformité, quotas, disponibilité ou coûts cloud engagés le rendent nécessaire.

## 2. Recommandation principale + alternatives

### Recommandation priorisée
1. **MVP recommandé : Option A — Studio GPU persistant piloté comme machine distante**
2. **Alternative d’industrialisation : Option B — Studio de référence + Batch Job à la demande**
3. **Alternative long terme si mutualisation inter-clients : Option C — API distante**
4. **Option contexte entreprise : Option D — BYOC / reserved / multi-cloud**

### Justification technique et opérationnelle
L’architecture actuelle de Workflow MediaPipe est déjà favorable à cette stratégie, car STEP5 sépare explicitement les moteurs. Le code existant impose déjà les invariants essentiels :
- `config/workflow_commands.py` lance STEP5 via `tracking_env_slim` (donc MediaPipe local CPU par défaut) ;
- `workflow_scripts/step5/run_tracking_manager.py` refuse InsightFace sans GPU et force MediaPipe hors GPU ;
- `workflow_scripts/step5/face_engines.py` confirme qu’InsightFace est **GPU-only** ;
- `services/workflow_service.py` prépare déjà la liste de vidéos et le fichier temporaire d’entrée.

Autrement dit, le bon axe n’est pas de refondre STEP5, mais d’ajouter une **branche d’orchestration distante pour le moteur `insightface` uniquement**, en gardant la branche MediaPipe intacte. Option A est la meilleure pour cela parce qu’elle remplace surtout **le lieu d’exécution** du worker InsightFace, pas la structure du pipeline.

### Meilleure option MVP
**Studio GPU persistant + exécution distante commandée depuis le pipeline local**.

Concrètement :
- si `STEP5_TRACKING_ENGINE` est vide ou `mediapipe*` → exécution actuelle locale CPU inchangée ;
- si `STEP5_TRACKING_ENGINE=insightface` **et** `STEP5_EXECUTION_MODE=remote_lightning` → le pipeline local prépare l’input STEP5, l’envoie au Studio Lightning, déclenche la commande distante, attend/poll, puis rapatrie `*_tracking.json`, logs, métriques.

### Alternative pour industrialisation / montée en charge
Passer ensuite à **Option B** : conserver un Studio “golden environment” pour figer les dépendances, puis soumettre des **Batch Jobs** pour chaque lot STEP5. Cela réduit les dérives manuelles, facilite la répétabilité, et prépare une exécution par lot plus robuste.

## 3. Plan d’action local (code / config / scripts)

### Principes à conserver impérativement
- **MediaPipe reste CPU-only local**.
- **Aucune migration GPU de MediaPipe**.
- **Routes Flask restent minces**.
- **Logique d’orchestration ajoutée dans `services/`**.
- **Extension incrémentale de config**, pas refonte.
- **WorkflowState** reste la source de vérité pour l’état et l’expérience opérateur.

### Adaptations locales minimales recommandées

#### 3.1 Étendre la configuration sans casser l’existant
Cibles probables :
- `config/settings.py`
- `config/workflow_commands.py`

Ajouter des variables **optionnelles** du type :
- `STEP5_EXECUTION_MODE=local|remote_lightning`
- `STEP5_REMOTE_PROVIDER=lightning`
- `STEP5_LIGHTNING_STUDIO_NAME`
- `STEP5_LIGHTNING_TEAMSPACE`
- `STEP5_LIGHTNING_MACHINE`
- `STEP5_LIGHTNING_REMOTE_ROOT`
- `STEP5_LIGHTNING_INPUTS_DIR`
- `STEP5_LIGHTNING_OUTPUTS_DIR`
- `STEP5_LIGHTNING_LOGS_DIR`
- `STEP5_LIGHTNING_POLL_INTERVAL`
- `STEP5_LIGHTNING_TRANSFER_MODE=studio_cp|drive|job_artifacts`
- `STEP5_LIGHTNING_FALLBACK_MODE=fail|mediapipe_cpu_local|local_insightface_if_available`

Important : `WorkflowCommandsConfig` n’a pas besoin de devenir “cloud aware” au sens large. Il peut rester le référentiel STEP5 local par défaut, avec éventuellement un **metadata block** additionnel pour le mode distant, mais sans changer la commande MediaPipe CPU actuelle.

#### 3.2 Isoler explicitement la branche InsightFace distante
Cibles probables :
- `services/workflow_service.py`
- **nouveau** `services/step5_remote_lightning_service.py`
- éventuellement **nouveau** `services/step5_transfer_service.py`

Responsabilités recommandées :
- `WorkflowService` : reste orchestrateur haut niveau ; choisit local vs remote selon config/moteur.
- `Step5RemoteLightningService` : encapsule la logique Lightning (préparation du lot, upload, lancement, polling, download, erreurs).
- `Step5TransferService` : abstrait transport I/O (CLI, SDK, Drive, artifacts) si vous voulez éviter de mélanger transfert et orchestration.

#### 3.3 Adapter le point de lancement STEP5 dans `app_new.py` sans logique métier lourde
Aujourd’hui `app_new.py` :
- prépare les vidéos STEP5 ;
- appelle `WorkflowService.prepare_tracking_step()` ;
- crée `videos_json_path` ;
- lance la commande STEP5 locale.

Évolution minimale :
- conserver ce flux pour MediaPipe local ;
- ajouter une bifurcation : si moteur InsightFace + `remote_lightning`, alors `run_process_async("STEP5")` délègue au service métier distant au lieu d’appeler directement `subprocess.Popen` local du manager.

Le backend Flask ne doit pas porter la logique Lightning ; il ne fait qu’appeler le service, mettre à jour le `WorkflowState`, streamer les logs structurés, puis terminer l’étape.

#### 3.4 Préparer les inputs STEP5 avant envoi
Entrées minimales à transférer :
- la/les vidéos détectées par `WorkflowService.prepare_tracking_step()` ;
- le JSON de lot (`videos_json_path` ou un manifest dérivé) ;
- éventuellement un petit fichier de config d’exécution STEP5 distant ;
- pas nécessairement les modèles si ceux-ci sont préinstallés/cachés sur le Studio.

Stratégie recommandée MVP :
- garder un manifest local par exécution (`run_id`) ;
- créer un répertoire d’exécution distant par lot : `.../step5_runs/<run_id>/input`, `output`, `logs` ;
- uploader uniquement les vidéos réellement à traiter + manifest.

#### 3.5 Transport des vidéos / logs / sorties
Ordre de préférence pragmatique :
1. **MVP** : `lightning studio cp` / SDK upload-download vers un Studio donné.
2. **Phase 2** : Drive / artifacts / job files pour mieux structurer la persistance.
3. **Contexte gros volumes** : data connections / cloud folders si les vidéos deviennent trop lourdes pour un upload ad hoc.

À récupérer côté local :
- `*_tracking.json`
- logs manager/worker
- métriques éventuelles (CSV ou JSON)
- statut final / code retour / erreurs détaillées

#### 3.6 Polling, reprise, idempotence
Recommandation :
- poller le statut toutes les `N` secondes depuis `WorkflowState` via le service distant ;
- identifier chaque run par un `run_id` stable ;
- considérer un run “terminé” seulement si les artefacts attendus existent ;
- en cas de relance, réutiliser `run_id` ou détecter les outputs déjà présents pour éviter les doublons.

Idempotence pragmatique :
- si `*_tracking.json` distant existe déjà et est complet, ne pas retraiter ;
- si résultat partiel/corrompu, marquer l’exécution comme retryable ;
- journaliser localement le mapping `run_id -> studio/job/output path`.

#### 3.7 Fallback local si Lightning indisponible
Recommandation simple :
- **par défaut** : `fail fast` si l’utilisateur a explicitement demandé `insightface + remote_lightning` et que Lightning est indisponible ;
- **fallback optionnel configurable** : basculer sur **MediaPipe CPU local** si l’objectif métier accepte une dégradation de moteur ;
- **ne jamais basculer MediaPipe en GPU**.

Cela doit être un choix explicite de config, pas un comportement implicite.

#### 3.8 Impact sur WorkflowState et UX opérateur
Ajouter des états intermédiaires lisibles :
- `STEP5_REMOTE_PREPARING`
- `STEP5_REMOTE_UPLOADING`
- `STEP5_REMOTE_STARTING`
- `STEP5_REMOTE_RUNNING`
- `STEP5_REMOTE_DOWNLOADING`
- `STEP5_REMOTE_FINALIZING`

Messages UI attendus :
- studio/job ciblé
- run_id
- progression transfert
- progression exécution distante
- statut récupération artefacts
- fallback éventuel

#### 3.9 Tests à prévoir
**Unitaires**
- sélection local vs remote selon moteur/config ;
- validation qu’InsightFace distant n’est jamais utilisé pour MediaPipe ;
- parsing des états distants ;
- stratégie de fallback ;
- idempotence upload/download/manifests.

**Intégration**
- STEP5 MediaPipe local intact ;
- STEP5 InsightFace remote avec mock CLI/SDK Lightning ;
- reprise après échec d’upload ;
- récupération correcte des `*_tracking.json`.

**Robustesse**
- coupure réseau ;
- studio stoppé/sleep ;
- artefact absent ou incomplet ;
- mismatch version environnement distant.

## 4. Plan d’action distant Lightning.ai (infra / exploitation / ops)

### 4.1 Mise en place MVP sur Lightning
**Voie recommandée MVP** : 1 Studio dédié `workflow-step5-insightface`.

Étapes :
1. Créer un Studio CPU, cloner le repo, installer dépendances de base.
2. Préparer l’environnement tant que le Studio est en CPU pour économiser.
3. Basculer ensuite sur un GPU adapté (`L4` ou `L40s` à privilégier avant A100/H100 pour commencer, selon VRAM et coût).
4. Installer/valider :
   - Python compatible avec `requirements-insightface_env.txt`
   - `insightface`
   - `onnxruntime-gpu`
   - dépendances OpenCV / numpy / éventuels system libs
   - validation `ort.get_available_providers()` contient `CUDAExecutionProvider`
5. Précharger/cacher les modèles InsightFace (`INSIGHTFACE_HOME` contrôlé) et vérifier qu’ils persistent.
6. Définir une arborescence distante stable :
   - `/teamspace/studios/<studio>/workflow_mediapipe/`
   - `runs/<run_id>/input`
   - `runs/<run_id>/output`
   - `runs/<run_id>/logs`

### 4.2 Commande conceptuelle de lancement distant
Le plus simple est de réutiliser le script existant et le moteur existant, par exemple conceptuellement :
- `STEP5_ENABLE_GPU=1`
- `STEP5_GPU_ENGINES=insightface`
- `STEP5_TRACKING_ENGINE=insightface`
- exécution de `workflow_scripts/step5/run_tracking_manager.py --videos_json_path <manifest>`

Cela respecte l’architecture actuelle : on ne réécrit pas STEP5, on relance simplement son exécution dans un environnement Lightning où `insightface_env`/CUDA sont valides.

### 4.3 Données, modèles, sorties
**Modèles**
- idéalement préinstallés et cache persisté dans le Studio ;
- éviter de les réuploader à chaque run ;
- utiliser Drive/artifacts uniquement pour les propager si plusieurs Studios/jobs doivent partager le cache.

**Inputs**
- MVP : upload direct par CLI/SDK ;
- si volume vidéo significatif : envisager S3/GCS/Data connections/Cloud folders plutôt qu’un upload ad hoc.

**Outputs**
- écrire systématiquement les `*_tracking.json`, logs et métriques dans un dossier de run ;
- récupérer ensuite par `studio cp`, SDK ou Drive download.

### 4.4 Exploitation quotidienne
**Option A exploitation**
- `lightning studio start` avant run si studio endormi ;
- upload lot ;
- déclenchement commande ;
- polling ;
- download résultats ;
- `lightning studio stop` après inactivité si besoin de réduire les coûts.

**Option B exploitation**
- garder un Studio “golden” ;
- soumettre un job avec `lightning run job --studio=<studio> --command="..."` ;
- suivre le job ;
- rapatrier les outputs via Drive/job files.

### 4.5 Snapshot / réutilisation d’environnement
Pertinence : forte.
- Studio persistant = excellent pour stabiliser `insightface + onnxruntime-gpu + cache modèles`.
- Batch jobs depuis Studio = très bon compromis pour rejouer un environnement validé.
- Déploiement snapshot/API = à garder pour une phase ultérieure, pas pour le MVP.

### 4.6 Choix GPU / coût / disponibilité
Recommandation initiale :
- démarrer avec **L4 ou L40s** si disponibles ;
- réserver A100/H100 aux cas où la perf/VRAM le justifie réellement ;
- rester **on-demand** pour MVP ;
- envisager **reserved** ou **preprovisioned** seulement si :
  - runs fréquents,
  - cold start pénalisant,
  - ou besoin de capacité garantie.

### 4.7 Sécurité / secrets / contrôle opérateur
- utiliser les secrets Lightning pour identifiants nécessaires ;
- éviter d’exposer une API publique en MVP ;
- si données sensibles : BYOC/VPC privé devient pertinent ;
- tagger les ressources si contexte org pour coût/traçabilité ;
- contrôler les accès Teamspace/Drive finement.

### 4.8 Quand BYOC / multi-cloud / reserved devient justifié
BYOC / VPC :
- si les vidéos ne peuvent pas quitter un cloud donné ;
- si des engagements AWS/GCP doivent être consommés ;
- si conformité ou régionalisation imposent un périmètre réseau privé.

Reserved / preprovisioning :
- si l’opérateur subit des ruptures de disponibilité GPU ;
- si STEP5 devient fréquent et critique en délai ;
- si cold start + provisioning dégradent trop l’expérience.

Multi-cloud :
- si les familles GPU visées sont souvent sold out ;
- si l’équipe veut arbitrer les coûts entre fournisseurs.

## Risques, inconnues et points à valider avant implémentation

### Risques techniques
- **Volume des vidéos à transférer** : peut devenir le principal coût/temps de bout en bout.
- **Coût réseau et temps de transfert** : potentiellement plus pénalisants que l’inférence elle-même pour petits lots dispersés.
- **Compatibilité exacte `insightface` / `onnxruntime-gpu` / CUDA** sur la machine Lightning choisie.
- **Cache des modèles InsightFace** : emplacement, persistance, corruption, permissions.
- **Cold start Studio/Job** : peut dégrader fortement l’expérience si runs courts.
- **Gestion des erreurs réseau** : upload interrompu, download incomplet, commande distante perdue.
- **Reprise après échec** : nécessité de définir run_id/idempotence/artefacts attendus.

### Risques ops / coût
- **Disponibilité réelle des GPU on-demand**.
- **Quotas/régions si BYOC**.
- **Coût d’un Studio laissé éveillé** ou d’un preprovisioning mal maîtrisé.
- **Stockage Drive / cloud folders** si accumulation d’artefacts vidéo/logs.

### Risques produit / UX opérateur
- allongement du délai STEP5 perçu si le transfert domine ;
- complexité opérateur accrue si plusieurs états distants sont opaques ;
- besoin d’un feedback UI clair sur upload/exécution/download/fallback.

### Points de validation avant implémentation
1. Taille moyenne et max des lots vidéo STEP5.
2. Temps moyen d’upload/download acceptable pour l’opérateur.
3. Machine Lightning minimale compatible (`L4`/`L40s`/autre) avec `onnxruntime-gpu` + InsightFace.
4. Stratégie retenue pour les modèles : cache local Studio ou Drive partagé.
5. Politique de fallback : fail fast vs repli MediaPipe CPU local.
6. Format exact des artefacts rapatriés attendus par les étapes aval.
7. Choix du transport MVP : `studio cp`/SDK direct vs Drive/job files.
8. Besoin ou non d’un contexte sécurité renforcé (BYOC/VPC).

### Conclusion pragmatique et priorisée
1. **Solution MVP** : mettre en place un **Studio Lightning GPU persistant** dédié à la branche **InsightFace** de STEP5, piloté comme machine distante depuis Workflow MediaPipe, avec uploads/downloads ciblés et sans modifier la branche **MediaPipe CPU local**.
2. **Trajectoire d’industrialisation** : une fois la faisabilité validée, passer à un modèle **Studio de référence + Batch Jobs** pour rendre l’exécution plus robuste, plus reproductible et plus exploitable en mode ponctuel ou par lot.

En bref : **ne touchez pas à MediaPipe**, gardez-le **CPU-only local**, et ajoutez une **branche d’orchestration distante Lightning exclusivement pour `insightface`**. C’est la voie la plus compatible avec l’architecture actuelle, la plus incrémentale, et la plus rationnelle opérationnellement.