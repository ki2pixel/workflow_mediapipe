## 1. Synthèse exécutive

**Optimiser STEP5 via une architecture dual-GPU orientée séparation de charges.** Il faut distinguer clairement : **1) la faisabilité matérielle réelle, 2) l’intégration logicielle/runtime, 3) l’impact pipeline STEP5, 4) le risque opérationnel.**

Conclusion ferme : **à court terme, le scénario le plus réaliste et compatible avec l’architecture actuelle est un dual-GPU de séparation stricte des rôles (S2), mais seulement comme évolution conditionnelle, progressive et réversible**. En revanche, **une orchestration applicative multi-GPU hétérogène explicite dans STEP5 (S3) n’est pas actuellement supportée par la stack et supposerait une refonte partielle du runtime, de l’observabilité et des mécanismes de sélection device**. La baseline actuelle (S1) doit rester la **référence de sécurité**, le **rollback natif**, et le **filet de sécurité opérationnel**.

Rappels non négociables : **MediaPipe ne doit pas être transformé en moteur GPU dans cette stack** ; **AMD/NVIDIA hétérogènes n’impliquent aucun gain cumulé automatique** ; **InsightFace reste aujourd’hui le seul moteur STEP5 GPU-compatible via ONNX Runtime CUDA** ; **aucune recommandation n’est valide sans protocole de test associé**.

---

## 2. Reformulation de l’objectif et distinction faisabilité matérielle vs intégration logicielle

**Objectif reformulé**
- **Optimiser STEP5 via une architecture dual-GPU orientée séparation de charges.**
- Distinguer clairement :
  1. **la faisabilité matérielle réelle**,  
  2. **l’intégration logicielle/runtime**,  
  3. **l’impact pipeline STEP5**,  
  4. **le risque opérationnel**.

**Lecture architecturale**
- **Faisabilité matérielle** : plausible sur X399 selon le rapport matériel existant, mais **non encore validée sur la machine cible**.
- **Intégration logicielle** : aujourd’hui, **STEP5 ne sait pas orchestrer plusieurs GPU hétérogènes comme ressources explicites**. Il sait seulement :
  - MediaPipe CPU via `tracking_env_slim`.
  - InsightFace GPU via `insightface_env` + ONNX Runtime CUDA.
- **Impact pipeline** : toute évolution doit préserver `WorkflowCommandsConfig`, `WorkflowState`, les logs STEP5, les contrats JSON STEP5→STEP6→STEP7 et le fallback CPU.
- **Risque opérationnel** : élevé si l’on tente une orchestration multi-device explicite sans validation matérielle, sans observabilité device-level, et sans rollback instantané.

---

## 3. Hypothèses / inconnues / bloqueurs

### 3.1 Hypothèses matérielles nécessaires

**Probables mais à vérifier**
- Carte mère X399 effectivement capable d’accueillir 2 GPU en **PCIEX16_1 + PCIEX16_2**.
- **PSU suffisante** pour Threadripper + GTX 1650 + RX 580 + stockage + ventilation.
- Présence des **connecteurs PCIe natifs** requis : au minimum 1×8-pin pour RX 580, éventuellement 1×6-pin pour GTX 1650 selon modèle.
- **Boîtier** avec dégagement physique suffisant pour deux cartes et airflow correct.
- **Refroidissement** suffisant pour éviter throttling / shutdown / instabilité.
- BIOS/UEFI suffisamment à jour, avec possibilité d’activer **Above 4G Decoding** si nécessaire.

**Inconnues bloquantes**
- Puissance et qualité exactes de l’alimentation.
- Modèles exacts des cartes (connectique, dimensions, TDP réels AIB).
- Températures actuelles CPU/GPU/VRM/boîtier en charge.
- Stabilité réelle de boot avec les slots retenus.

**Tests minimum pour lever les inconnues**
- Inventaire physique PSU/câbles/slots.
- 5 à 10 cycles de boot froid/chaud avec les deux cartes installées.
- Relevé thermique au repos et en charge.
- Vérification BIOS : version, Above 4G, mode PCIe.

### 3.2 Hypothèses logicielles nécessaires

**Confirmé côté projet**
- STEP5 n’a que deux moteurs opérationnels : **MediaPipe CPU** et **InsightFace GPU**.
- **MediaPipe doit rester CPU-only**.
- **InsightFace est GPU-only** et dépend de **`CUDAExecutionProvider`** dans ONNX Runtime.
- La configuration passe par **`.env` → `config/settings.py` → `WorkflowCommandsConfig`**.
- Le fallback CPU existe déjà via **`STEP5_GPU_FALLBACK_AUTO`**.

**Probables mais à vérifier**
- OS cible exact pour la future config dual-GPU.
- Version réelle des drivers NVIDIA/AMD.
- Version réelle CUDA / ONNX Runtime dans `insightface_env`.
- Détection correcte du GPU NVIDIA quand un GPU AMD est aussi présent.
- Possibilité de sélectionner explicitement le bon GPU NVIDIA pour InsightFace quand plusieurs adaptateurs coexistent.

**Inconnues bloquantes**
- OS exact de la machine cible.
- Comportement de `nvidia-smi`, NVML et ONNX Runtime avec la future topologie.
- Présence d’un mécanisme robuste de **sélection de device GPU explicite** actuellement exploitable dans STEP5.
- Support réel du routing applicatif vers plusieurs devices dans la stack existante.

**Tests minimum pour lever les inconnues**
- `nvidia-smi` / NVML avec les 2 cartes installées.
- Vérification des providers ONNX Runtime dans `insightface_env`.
- Test de démarrage InsightFace avec coexistence AMD/NVIDIA.
- Test de sélection contrôlée d’un GPU NVIDIA précis si plusieurs GPU NVIDIA sont un jour présents.

### 3.3 Bloqueurs projet/architecture observés

**Bloqueur technique confirmé**
- `run_tracking_manager.py` résout encore `tracking_env` pour certains chemins Python internes alors que la baseline projet/documentation est **`tracking_env_slim`**. Ce n’est pas un bloqueur pour l’analyse, mais **c’est une incohérence à traiter avant toute évolution dual-GPU**, car elle fragilise la lisibilité et le rollback.

**Bloqueur fonctionnel majeur**
- L’observabilité GPU actuelle (`MonitoringService`) est **mono-GPU index 0** via NVML. Elle n’est pas prête pour une exploitation multi-device.

**Bloqueur d’architecture**
- Le scheduler STEP5 actuel orchestre **CPU + éventuel GPU** comme ressources génériques, mais **pas un parc explicite de devices hétérogènes adressables et tracés individuellement**.

---

## 4. Analyse par 4 axes

### Axe 1 — Matériel

#### Confirmé
- Le rapport matériel indique que la plateforme X399 est **matériellement plausible** pour un dual-GPU.
- L’intérêt principal du dual-GPU hétérogène est **la séparation des usages**, pas la fusion des performances.
- Les slots **PCIEX16_1 + PCIEX16_2** sont les candidats les plus crédibles pour un premier essai.

#### Probable mais à tester
- Dual-GPU stable sur X399 avec AMD + NVIDIA si PSU, cooling et BIOS sont corrects.
- Coexistence bootable sans incident si slots bien choisis et BIOS propre.

#### Inconnus bloquants
- PSU réelle disponible et marge de sécurité.
- Dégagement boîtier, airflow, courbe thermique réelle.
- Sensibilité réelle de la machine au POST multi-GPU.

#### Évaluation
- **Slots PCIe exploitables** : probable oui, mais validation physique indispensable.
- **Partage de lignes / placement** : acceptable sur le papier, mais il faut confirmer l’impact sur autres périphériques installés.
- **PSU / connecteurs** : risque élevé si la machine est déjà proche de sa limite.
- **Thermique** : risque réel, surtout si RX 580 chauffe fortement et recycle l’air.
- **BIOS/UEFI / boot** : risque modéré à élevé tant qu’aucun test de redémarrage répété n’a été fait.
- **Risque AMD + NVIDIA** : matériellement plausible, opérationnellement plus fragile qu’un single-vendor.

#### Décision axe matériel
- **Faisabilité matérielle : probable mais non confirmée.**
- Sans validation PSU + boot + température, **aucune décision ferme de déploiement dual-GPU ne doit être prise**.

---

### Axe 2 — Runtime / Drivers / Orchestration système

#### Confirmé dans le code
- `Config.check_gpu_availability()` est centré sur :
  - **NVML / `nvidia-smi`**
  - contrôle **VRAM libre**
  - contrôle **ONNX Runtime CUDA provider**
- `face_engines.py` impose **`CUDAExecutionProvider`** pour InsightFace.
- `create_face_engine()` n’expose que :
  - MediaPipe implicite
  - InsightFace via GPU
- `run_tracking_manager.py` n’a pas de notion de **liste de devices GPU adressables** ; il a juste un booléen GPU actif/inactif.

#### Conséquences
- **AMD n’apporte rien à InsightFace/ONNX Runtime CUDA** dans l’état actuel. InsightFace reste de fait **NVIDIA-bound** dans cette stack.
- La présence d’un GPU AMD peut être utile pour **affichage/desktop/usage auxiliaire**, mais **pas pour accélérer InsightFace** avec l’implémentation actuelle.
- La coexistence AMD/NVIDIA peut être acceptable au niveau OS, mais **le runtime STEP5 ne sait pas en tirer un bénéfice direct sans refonte partielle**.

#### Probable mais à tester
- Le système d’exploitation peut tolérer la coexistence AMD/NVIDIA.
- ONNX Runtime CUDA continuera de voir le GPU NVIDIA si les drivers NVIDIA restent sains.

#### Inconnus bloquants
- OS cible exact.
- Comportement réel des pilotes et overlays en cohabitation.
- Robustesse de la sélection device si la topologie change.

#### Décision axe runtime
- **Support runtime multi-GPU hétérogène explicite : non confirmé, aujourd’hui insuffisant.**
- **Support séparation de rôles par OS/process : plausible.**
- **Support orchestration applicative multi-device dans STEP5 : non mature.**

---

### Axe 3 — Pipeline STEP5

#### Confirmé dans le projet
- `WorkflowCommandsConfig` lance STEP5 avec `tracking_env_slim`.
- `run_tracking_manager.py` choisit aujourd’hui entre :
  - CPU MediaPipe
  - GPU InsightFace
- `STEP5_ENABLE_GPU`, `STEP5_TRACKING_ENGINE`, `STEP5_GPU_ENGINES`, `STEP5_GPU_FALLBACK_AUTO`, `TRACKING_CPU_WORKERS` pilotent déjà le runtime.
- Si moteur = `insightface`, alors :
  - GPU requis
  - `insightface_env` requis
  - fallback CPU possible seulement si on revient au moteur CPU baseline, pas en continuant InsightFace sans GPU.
- Les contrats JSON restent un point dur à préserver pour STEP6/STEP7.

#### Lecture pipeline
- **CPU-only qui doit rester CPU-only** : MediaPipe + multiprocessing `tracking_env_slim`.
- **GPU-routeable aujourd’hui** : uniquement InsightFace via `insightface_env`.
- **Points d’entrée config à étendre si évolution** : uniquement la couche config centralisée, pas de hardcode dans les workers.
- **Composants à adapter** si on allait plus loin :
  - validation GPU
  - sélection device
  - scheduler/resource model
  - logs manager/worker
  - monitoring multi-GPU
- **Compatibilité STEP6/STEP7** : doit être considérée comme non négociable.

#### Point critique de cohérence
- La documentation pipeline contient des traces hétérogènes (par exemple “Hybrid Auto”, variables obsolètes), tandis que le code réel est plus strict. Il faut donc **faire primer le code + les règles projet** dans la décision.

#### Décision axe pipeline
- **Le pipeline STEP5 actuel est compatible avec une séparation de rôles externe au process**, mais **pas avec une vraie abstraction multi-GPU hétérogène interne**.
- Toute cible dual-GPU doit donc **préserver le moteur CPU baseline et ne toucher le moteur GPU qu’avec extension minimaliste et réversible**.

---

### Axe 4 — Opérations / Exploitation

#### Confirmé
- Les logs STEP5 distinguent déjà manager / worker CPU / worker GPU.
- Le fallback CPU existe déjà côté logique de validation GPU.
- `WorkflowState` permet de préserver un état centralisé propre.

#### Faiblesses actuelles
- Monitoring GPU mono-device seulement.
- Pas de télémétrie explicite “job → device”.
- Pas de matrice de santé spécifique multi-GPU.
- Pas de rollback documenté “dual-GPU off → baseline on” puisque la cible n’existe pas encore.

#### Risques opérationnels
- Debug difficile si conflit driver intermittent.
- Difficile de prouver où un job a tourné sans enrichissement des logs.
- Risque de dette cachée si la sélection device est implicite et non tracée.

#### Décision axe opérations
- **Avant toute expérimentation dual-GPU**, il faut imposer :
  - logs device-aware,
  - monitoring multi-device minimal,
  - rollback explicite,
  - smoke tests standardisés.

---

## 5. Comparatif détaillé S1 / S2 / S3

### S1 — Baseline actuelle conservée

**Principe**
- MediaPipe = CPU par défaut via `tracking_env_slim`.
- InsightFace = GPU optionnel via `insightface_env` + ONNX Runtime CUDA.
- Fallback CPU existant si validation GPU échoue.

**Prérequis**
- Aucun changement matériel.
- Aucun changement d’architecture.

**Modifications attendues**
- Aucune pour fonctionner.
- Seulement clarification documentaire et correction d’incohérences éventuelles.

**Bénéfices**
- Stabilité maximale.
- Rollback natif : il n’y a rien à rollback.
- Compatibilité STEP6/STEP7 déjà acquise.
- Complexité opérationnelle minimale.

**Risques**
- Aucun gain dual-GPU.
- STEP5 GPU reste limité à un seul GPU NVIDIA.
- Capacité d’optimisation plafonnée.

**Niveau de complexité**
- **Faible**.

**Compatibilité projet existant**
- **Totale**.

**Recommandation finale**
- **Retenu comme référence de sécurité et rollback absolu.**

---

### S2 — Dual-GPU avec séparation stricte des rôles

**Principe**
- Un GPU sert au **desktop / affichage / encodage / tâches auxiliaires**.
- L’autre GPU NVIDIA reste **réservé au compute STEP5 pertinent**, c’est-à-dire InsightFace.
- On **ne cherche pas à fusionner** les performances ni à faire de la coopération intra-process entre AMD et NVIDIA.

**Prérequis**
- Validation matérielle PSU / slots / refroidissement / BIOS.
- Validation de coexistence drivers AMD/NVIDIA.
- Garantie que le GPU NVIDIA reste visible et stable pour ONNX Runtime CUDA.
- Clarification des mécanismes de sélection du GPU compute si nécessaire.

**Modifications attendues**
- Faibles à modérées si on reste strict :
  - enrichir validation GPU,
  - enrichir logs/observabilité,
  - documenter procédure d’exploitation,
  - éventuellement exposer une config de ciblage device sans casser l’existant.

**Bénéfices**
- Réduction potentielle de contention entre desktop/affichage et compute.
- Stabilisation du GPU compute s’il n’est plus sollicité par l’OS pour l’affichage.
- Meilleur usage pratique du dual-GPU sans prétention de scaling artificiel.

**Risques**
- Conflits drivers AMD/NVIDIA.
- Complexité matérielle/thermique.
- Gain STEP5 non garanti si la contention actuelle est déjà faible.
- Besoin d’observabilité renforcée.

**Niveau de complexité**
- **Moyen**.

**Compatibilité projet existant**
- **Bonne, sous conditions**, car on ne change pas le cœur logique des moteurs.

**Recommandation finale**
- **Retenu sous conditions.**
- **C’est le scénario le plus pragmatique** si l’objectif est d’améliorer le contexte d’exécution STEP5 sans refondre la stack.

---

### S3 — Dual-GPU avec orchestration applicative ciblée

**Principe**
- La stack ferait du **job routing explicite / process routing / device selection explicite** selon moteur, job ou charge.
- Elle tenterait d’utiliser plusieurs devices comme ressources adressables du scheduler.

**Prérequis**
- Abstraction de ressources GPU multi-device.
- Sélection explicite de device robuste par process.
- Observabilité par device.
- Tests runtime multi-vendeur.
- Clarification de ce qui est routable côté moteur.

**Modifications attendues**
- Modérées à lourdes :
  - refonte partielle du scheduler STEP5,
  - extension forte de la config,
  - enrichissement du monitoring,
  - adaptation des logs,
  - gestion d’erreurs runtime multi-device,
  - matrice de compatibilité OS/driver/provider.

**Bénéfices**
- Meilleur contrôle théorique du runtime.
- Préparation éventuelle à de futurs cas multi-device homogènes.

**Risques**
- **Très élevé** avec AMD/NVIDIA hétérogènes.
- Peu pertinent tant que seul InsightFace exploite CUDA/NVIDIA.
- Bénéfice faible par rapport au coût si le second GPU est AMD.
- Régression possible sur stabilité, fallback et maintenabilité.

**Niveau de complexité**
- **Élevé**.

**Compatibilité projet existant**
- **Partielle seulement** ; suppose une refonte partielle.

**Recommandation finale**
- **Non retenu à court terme.**
- Au mieux : **acceptable comme piste moyen terme uniquement si la cible devient homogène NVIDIA/NVIDIA ou si la stack change profondément**.

---

## 6. Matrice de décision chiffrée

> Échelle : **10 = meilleur**.  
> Pour “complexité opérationnelle”, “risque driver/runtime” et “effort d’intégration”, la note reflète la **favorabilité** : plus c’est simple/sûr, plus la note est haute.

| Critère | S1 Baseline | S2 Dual-GPU séparation stricte | S3 Orchestration applicative ciblée |
|---|---:|---:|---:|
| Performance STEP5 | 5/10 | 7/10 | 6/10 |
| Stabilité | 9/10 | 6/10 | 3/10 |
| Complexité opérationnelle | 9/10 | 6/10 | 2/10 |
| Coût énergétique | 8/10 | 4/10 | 3/10 |
| Maintenabilité | 9/10 | 6/10 | 3/10 |
| Risque driver/runtime | 9/10 | 5/10 | 2/10 |
| Effort d’intégration | 9/10 | 6/10 | 2/10 |
| Qualité fallback/rollback | 10/10 | 8/10 | 4/10 |
| **Score synthèse** | **68/80** | **48/80** | **25/80** |

### Synthèse ferme
- **Scénario recommandé** : **S2**, mais **uniquement après validation matérielle et runtime**, et en gardant **S1 comme baseline active**.
- **Scénario acceptable mais risqué** : **S1**, si l’on privilégie la stabilité et qu’aucun gain démontré ne justifie S2.
- **Scénario à écarter** : **S3** à court terme.
- **Justification courte** : S2 est le seul compromis crédible entre bénéfice potentiel et compatibilité existante ; S3 est trop coûteux et trop peu aligné avec la stack réelle ; S1 reste la sécurité absolue.

---

## 7. Architecture cible recommandée

### Recommandation
**Architecture cible recommandée : S2 — dual-GPU avec séparation stricte des rôles, sans fusion artificielle des performances.**

### Pourquoi
- Respecte les faits projet :
  - MediaPipe reste CPU-only.
  - InsightFace reste GPU-only NVIDIA/ONNX.
  - Les environnements spécialisés restent séparés.
  - Le pipeline STEP5 → STEP6 → STEP7 reste inchangé dans ses contrats.
- Minimise l’ampleur de changement.
- Préserve le fallback CPU et la réversibilité.

### Formulation opérationnelle
- **GPU NVIDIA** : réservé au compute STEP5 quand `STEP5_TRACKING_ENGINE=insightface` et que la validation GPU passe.
- **GPU secondaire AMD** : réservé à l’affichage / desktop / usage auxiliaire / vidéo / encodage si pertinent, mais **pas intégré comme accélérateur STEP5** dans la stack actuelle.

### Limite assumée
- Cette architecture **n’augmente pas automatiquement la performance brute de STEP5**. Elle vise d’abord **la séparation des charges**, la réduction de contention et la stabilisation du GPU de calcul.

---

## 8. Tableau risques / mitigations

| Risque | Niveau | Nature | Mitigation | Test associé |
|---|---|---|---|---|
| PSU insuffisante | Élevé | Matériel | Validation puissance + connecteurs + marge | charge GPU + reboot loop |
| POST instable dual-GPU | Élevé | Matériel/BIOS | slots x16+x16, BIOS à jour, Above 4G si requis | 5-10 boots froid/chaud |
| Conflit drivers AMD/NVIDIA | Élevé | Runtime | procédure clean install + versioning drivers | smoke OS + redémarrages |
| ONNX Runtime ne voit plus CUDA | Élevé | Runtime | test provider dans `insightface_env` | smoke InsightFace |
| Mauvaise sélection device | Moyen | Runtime | config explicite + logs device-aware | run ciblé par device |
| Régression STEP5 baseline | Critique | Pipeline | baseline conservée, activation feature-flag | comparaison A/B |
| Logs insuffisants | Moyen | Opérations | enrichir logs manager/worker avec device/provider | revue logs |
| Monitoring mono-GPU insuffisant | Moyen | Ops | étendre monitoring par device | dashboard / API health |
| JSON STEP5 modifié par erreur | Critique | Pipeline | interdiction de changer le contrat sans test régression | validation STEP6/STEP7 |
| Dette cachée rollback | Élevé | Opérations | rollback en procédure courte et documentée | test rollback complet |

---

## 9. Cartographie des ajustements STEP5

| Composant concerné | Rôle actuel | Adaptation probable | Risque associé | Test requis avant validation |
|---|---|---|---|---|
| `.env` | Active moteur GPU/CPU et fallback | Ajouter uniquement des flags de ciblage/observabilité si nécessaire, sans casser les clés actuelles | dérive config / ambiguïté | validation parsing + défaut baseline |
| `config/settings.py` | Centralise flags STEP5 + validation GPU | Étendre validation pour topologie multi-device sans hardcode | faux positifs / faux négatifs GPU | smoke config + détection devices |
| `WorkflowCommandsConfig` | Pointe STEP5 vers `tracking_env_slim` | Préserver interface ; pas de complexité runtime ici | confusion env | test commande STEP5 générée |
| `run_tracking_manager.py` | Scheduler CPU/GPU simple | Clarifier modèle ressource, enrichir logs, éventuellement ciblage GPU explicite | régression scheduler | tests unitaires + runs comparatifs |
| Validation GPU (`Config.check_gpu_availability`) | Vérifie NVML, VRAM, ONNX CUDA | Étendre à multi-device visible et sélectionnable | erreur de décision fallback | smoke provider + VRAM + device mapping |
| `face_engines.py` / `InsightFaceEngine` | Initialise FaceAnalysis sur CUDA | Exposer si besoin un ciblage device strictement encadré | régression moteur GPU | init InsightFace + inference stable |
| `tracking_env_slim` / `insightface_env` | Isolation CPU/GPU | Aucun mélange ; seulement clarifier orchestration | confusion environnementale | test venv par moteur |
| Logs manager / worker | Observabilité process | Ajouter IDs device/provider/venv utilisés | debug insuffisant si absent | revue logs sur run réel |
| `MonitoringService` | CPU/RAM/GPU index 0 | Étendre à multi-device minimum | observabilité partielle | comparaison télémétrie OS vs app |
| Sorties JSON STEP5 | Contrat consommé par STEP6/STEP7 | **Aucune évolution fonctionnelle autorisée** | casse pipeline | validation JSON + STEP6 + STEP7 |
| Séquencement STEP5→STEP6→STEP7 | Pipeline existant | Aucun changement contractuel | régression silencieuse | run pipeline complet |

---

## 10. Check-list d’implémentation ordonnée (sans code)

1. **Geler la baseline S1 comme référence officielle de sécurité**.
2. **Corriger les incohérences STEP5/doc/runtime** avant toute expérimentation (notamment la référence `tracking_env` vs `tracking_env_slim`).
3. **Valider la machine cible** : PSU, slots, connectique, airflow, BIOS.
4. **Valider la coexistence OS/drivers AMD/NVIDIA** hors pipeline.
5. **Valider l’intégrité du runtime InsightFace** avec le GPU NVIDIA dans la topologie dual-GPU.
6. **Étendre l’observabilité minimale** : logs device/provider/venv ; monitoring multi-device.
7. **Définir un mode “dual-GPU separation” strictement feature-flagged** et désactivé par défaut.
8. **Tester le fallback CPU automatique** depuis ce mode sans toucher aux contrats JSON.
9. **Comparer S1 vs S2 sur charge réelle** avec métriques objectives.
10. **Décider Go/No-Go** uniquement si le gain observé compense clairement la complexité ajoutée.
11. **Documenter rollback court** et l’exercer réellement.
12. **Ne considérer S3 qu’après validation complète de S2 et seulement si un besoin métier concret l’impose**.

---

## 11. Plan de validation & observabilité

### Niveau 1 — Smoke tests

**Objectif** : prouver que la machine et le runtime restent sains.

Vérifications minimales :
- La machine **boote** avec 2 GPU.
- Les 2 GPU sont **vus correctement par l’OS**.
- Les drivers **coexistent** sans erreur majeure.
- STEP5 baseline MediaPipe CPU fonctionne toujours.
- InsightFace GPU fonctionne encore via ONNX Runtime CUDA.
- Le fallback CPU automatique reste effectif si GPU indisponible.

**Mesures attendues**
- 5 à 10 redémarrages sans échec.
- Aucun crash driver visible.
- Un run STEP5 MediaPipe baseline réussi.
- Un run STEP5 InsightFace GPU réussi.

### Niveau 2 — Tests de charge

**Objectif** : mesurer le comportement sous pression.

À mesurer :
- comportement CPU en mode MediaPipe,
- comportement GPU en mode InsightFace,
- saturation VRAM,
- contention PCIe/IO éventuelle,
- stabilité du scheduler,
- comportement avec plusieurs vidéos successives.

**Mesures attendues**
- temps STEP5 total,
- taux d’utilisation CPU/GPU par phase,
- VRAM libre minimale,
- incidents runtime,
- temps moyen par vidéo.

### Niveau 3 — Endurance

**Objectif** : vérifier la tenue dans le temps.

À mesurer :
- stabilité thermique,
- dérive performance,
- fuite mémoire,
- erreurs runtime tardives,
- résilience du fallback.

**Mesures attendues**
- séries longues de traitements sans crash,
- températures dans l’enveloppe acceptable,
- pas de montée mémoire incontrôlée,
- pas d’érosion significative run-to-run.

### Niveau 4 — Comparaison baseline vs cible

**Objectif** : décider objectivement.

Comparer :
- temps total STEP5,
- stabilité run-to-run,
- consommation/échauffement,
- qualité de sortie JSON,
- taux d’échec,
- gains réels vs complexité ajoutée.

### Observabilité obligatoire
- Log manager : moteur, venv, provider, device ciblé, raison du fallback.
- Log worker : vidéo, engine, device effectif, statut fin, durée.
- Monitoring : CPU, RAM, GPU(s), température(s), VRAM, état santé.
- Corrélation : run id / vidéo / worker / device.

### Acceptance criteria Go / No-Go

**Go minimal**
- Aucune régression sur baseline CPU.
- Aucun échec de boot après **N=5** redémarrages minimum.
- Aucun crash driver sur **N=10** runs minimum.
- Fallback CPU automatique effectif et traçable.
- Contrats JSON inchangés et STEP6/STEP7 valides.
- Gain mesurable suffisant pour justifier la complexité ajoutée.

**Seuil recommandé pour justifier S2**
- soit **gain de temps STEP5 ≥ 10-15%** sur la charge réelle,
- soit **stabilité GPU perceptiblement meilleure** (moins de contention, moins d’échecs, moins de saturation),
- sinon **No-Go** et maintien S1.

---

## 12. Plan de rollback / retour automatique au baseline

### Principe
Le rollback doit **rétablir explicitement le mode STEP5 actuel**, pas un état hybride ambigu.

### Procédure courte de rollback
- Désactiver le mode dual-GPU expérimental via la configuration centralisée.
- Revenir à la baseline :
  - MediaPipe CPU par défaut via `tracking_env_slim`,
  - InsightFace GPU optionnel inchangé,
  - scheduler STEP5 standard,
  - monitoring standard.

### Conditions qui déclenchent le retour automatique au baseline
- échec de détection GPU stable,
- provider ONNX Runtime CUDA indisponible,
- crash driver répété,
- instabilité boot,
- température hors enveloppe,
- régression STEP5/STEP6/STEP7,
- gain non démontré.

### Indicateurs qui invalident la cible dual-GPU
- 1 seul incident de casse pipeline STEP5→STEP6→STEP7.
- instabilité boot répétée,
- logs incapables d’identifier le device utilisé,
- fallback non maîtrisé,
- bénéfice non mesurable.

### Stratégie de restauration baseline sans dette cachée
- aucune suppression du mode baseline,
- aucune mutation irréversible des contrats JSON,
- aucun remplacement implicite de moteur,
- activation dual-GPU strictement optionnelle et réversible.

---

## 13. Décisions ouvertes avec seuils Go / No-Go

### Décisions ouvertes
1. **La plateforme matérielle supporte-t-elle réellement le dual-GPU stable ?**  
   - Go si boots répétés + température maîtrisée + PSU validée.
2. **La coexistence AMD/NVIDIA perturbe-t-elle le runtime NVIDIA/ONNX ?**  
   - Go si InsightFace reste stable sur série de runs.
3. **La séparation des rôles apporte-t-elle un bénéfice concret à STEP5 ?**  
   - Go si gain de temps ou gain de stabilité est mesurable.
4. **Faut-il introduire une sélection device explicite dans STEP5 ?**  
   - Go seulement si besoin démontré et si la couche config + logs + validation suivent.
5. **Faut-il envisager S3 plus tard ?**  
   - Non, sauf changement de besoin métier et preuve que S2 plafonne réellement.

### Seuils Go / No-Go
- **No-Go immédiat** si :
  - boot instable,
  - driver conflictuel,
  - InsightFace instable,
  - fallback non fiable,
  - JSON impacté.
- **Go contrôlé vers S2** si :
  - matériel validé,
  - runtime validé,
  - observabilité enrichie,
  - rollback court éprouvé,
  - bénéfice démontré.
- **No-Go pour S3 à court terme** tant que la stack reste AMD/NVIDIA hétérogène et que seul InsightFace exploite CUDA.

---

## 14. Recommandation court terme / moyen terme

### Court terme
- **Conserver S1 comme baseline active et officielle.**
- **Ne pas lancer de design multi-GPU orchestral complexe.**
- Faire uniquement :
  - validation matérielle réelle,
  - validation runtime AMD/NVIDIA,
  - clarification des incohérences STEP5,
  - préparation observabilité + rollback.
- **Conclusion court terme** : si ces validations ne sont pas immédiatement concluantes, **la meilleure option reste l’état actuel**.

### Moyen terme
- Si la validation est positive, **déployer S2 comme mode optionnel, feature-flagged, documenté et réversible**.
- Mesurer objectivement les gains avant de considérer la cible comme utile.
- **Ne pas retenir S3** sauf évolution majeure de la stack ou besoin métier nouveau.

---

### Rappel explicite des garde-fous finaux
- **MediaPipe ne doit pas être transformé en moteur GPU dans cette stack.**
- **L’hétérogénéité AMD/NVIDIA n’implique pas un gain cumulé automatique.**
- **La baseline STEP5 actuelle reste la référence de sécurité.**
- **Toute évolution doit rester réversible rapidement.**
- **Aucune recommandation n’est considérée valide sans protocole de test associé.**