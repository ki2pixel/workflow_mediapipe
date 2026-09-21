# Audit — Téléchargement automatique Cloudflare R2 (proxy worker)

**Date** : 2026-09-21
**Périmètre** : fiabilisation de la chaîne `webhook → CSV monitor → DownloadService` (archives `.zip` volumineuses),
widget de métriques CPU/GPU/RAM, objets R2 manquants côté worker.
**Méthode** : analyse statique du code, exploitation des journaux réels (`logs/app.log*`, session du 21/09),
et sondage HTTP direct des objets R2 référencés par le webhook (`scripts/check_r2_objects.py`).

---

## 1. Chaîne actuelle

```
webhook (https://webhook.kidpixel.fr/webhook_proxy.php)
  → WebhookService.fetch_records()                 services/webhook_service.py
  → CSVService._normalize_url() / heuristiques     services/csv_service.py
  → check_csv_for_downloads()                      services/csv_monitor.py      (1 thread par URL)
  → execute_csv_download_worker()                  services/csv_downloader.py
  → DownloadService.download_dropbox_file()        services/download_service.py (HEAD + GET streamé)
```

Le « R2 » n'est pas un SDK : c'est une simple URL HTTP `r2_url`
(`https://server.kidpixel.workers.dev/dropbox/<a>/<b>/file`) **préférée** à `source_url`
(lien Dropbox d'origine), ce dernier servant de repli. Aucun identifiant R2 n'existe dans le dépôt.

---

## 2. Constats

| # | Constat | Preuve |
|---|---|---|
| C1 | **1 mise à jour d'état + 1 log DEBUG par chunk de 512 Ko** : ~1 700 lignes de log et ~1 700 prises de `RLock` par Go téléchargé | `logs/app.log:69401-71097` → 1668 × `csv_ee7a8289 -> downloading` pour `197_Camille.zip` (833 Mo) |
| C2 | **Deux écrivains concurrents sur `app.log`** (RotatingFileHandler + `>> app.log` du lanceur) → rotation cassée, octets NUL, journal détecté comme binaire (grep aveugle au-delà) | `app_new.py:233-248` + `start_workflow.sh:181` |
| C3 | **Aucun échec HTTP journalisé** : ni `CSV DOWNLOAD: Failed`, ni `Network error` dans `app.log` et ses rotations | `grep -a` sur `logs/app.log*` |
| C4 | **Aucune validation pour les liens non `/scl/fo/`** : `_validate_download()` retournait `True` pour tout payload → une réponse **200 + corps HTML/JSON** était écrite sur disque puis **les 2 URLs inscrites en historique** (plus aucun retry possible) | `download_service.py` (avant correctif), `csv_downloader.py:86-89` |
| C5 | **Aucune reprise `Range`, aucun watchdog de stall** (read timeout 3600 s), **1 seule tentative par URL**, aucun contrôle d'intégrité ZIP | constantes `download_service.py` (avant correctif) |
| C6 | `/api/system_monitor` exécutait tout **inline et bloquant** : `psutil.cpu_percent(interval=0.1)` (100 ms garantis), NVML, `disk_usage`, `mkdir` par requête, sans cache | `monitoring_service.py`, `routes/api_routes.py` |
| C7 | Le frontend **empilait les polls** (aucune garde anti-empilement) et **arrêtait définitivement** un poller après N erreurs consécutives | `static/utils/PollingManager.js`, `static/main.js` |
| C8 | **Pas de fichier `.part`** : une application interrompue en plein transfert laissait un `.zip` tronqué crédible ; la tentative suivante écrivait `..._1.zip` | `download_service.py` (avant correctif) |
| C9 | **Les copies R2 sont éphémères (TTL 24 h)** : sur 318 `r2_url` publiées par le webhook, seules les **5 plus récentes** répondent 200 ; **313 renvoient 404** | `scripts/check_r2_objects.py` (2026-09-21) + `scripts/R2/r2-fetch-worker.js:414-416` (`expiresAt = now + 24h`) et `scripts/R2/r2-cleanup-worker.js:29-36` |

### C9 — le constat déterminant

```
OK          178 Camille.zip   …/dropbox/fb0cfafc/9fb4b348/file   (2026-09-21)
OK          180 Camille.zip   …/dropbox/87690436/defebc68/file   (2026-09-21)
OK          185 Camille.zip   …/dropbox/09cf1661/5deec1d2/file   (2026-09-21)
OK          194 Camille.zip   …/dropbox/e4bac9f9/b22535aa/file   (2026-09-21)
OK          197 Camille.zip   …/dropbox/9529f228/6d6c3f94/file   (2026-09-21)
MISSING     175 Camille.zip   …/dropbox/65e13bcd/459fdf41/file   (2026-09-18)   → 404
MISSING     154 Camille.zip   …/dropbox/83c44035/3e28a43d/file   (2026-09-17)   → 404
… 313 objets indisponibles / 318 enregistrements
```

Le mécanisme est confirmé par le code des workers (miroir dans `scripts/R2/`) : le worker d'ingestion
(`r2-fetch-worker.js`) estampille chaque objet d'un `customMetadata.expiresAt = maintenant + 24 h`
(lignes 414-416) et le worker planifié (`r2-cleanup-worker.js`) supprime tout objet échu (lignes 29-36).
**Une copie R2 vit donc 24 heures**, pas « quelques jours » — le JSON du webhook, lui, conserve tous les
enregistrements indéfiniment.

Conséquences directes :

1. **Bug « certains .zip n'existent pas côté worker »** : l'objet R2 n'est pas *manquant par erreur*, il est
   **expiré** (TTL 24 h + purge planifiée). Le lien Dropbox reste la source de vérité.
2. **Le repli Dropbox n'est pas un cas exceptionnel, c'est le chemin nominal** dès qu'une archive n'a pas été
   récupérée dans les 24 h suivant sa mise à disposition.
3. **Toute archive non téléchargée rapidement n'est récupérable que via Dropbox** — d'où l'importance de la
   validation de payload : Dropbox comme le worker peuvent répondre 200 avec une page HTML intermédiaire.
4. **La fenêtre utile est courte** : si l'application n'est pas lancée le jour de la réception du mail, c'est
   Dropbox qui sert le fichier (débit et robustesse différents, d'où les réglages de reprise/watchdog).

---

## 3. Correctifs appliqués

### 3.1 Moteur de téléchargement (`services/download_service.py`)

- Écriture systématique dans `<nom>.part` + `os.replace()` **atomique** vers `<nom>.zip` uniquement si le
  transfert est complet **et** le payload validé (corrige C4 et C8).
- **Reprise HTTP `Range`** : le `.part` est repris au prochain essai ; `416` ou serveur ignorant `Range`
  → redémarrage propre (aucune concaténation corrompue). Vérifié sur le worker déployé : **`server.js` ignore
  `Range`** (il appelle `env.R2_BUCKET.get(key)` sans transmettre l'en-tête et répond toujours 200 avec le corps
  complet). La reprise est donc effective :
  - sur le lien **Dropbox** de repli (qui honore `Range`) ;
  - **à travers la bascule R2 → Dropbox** : le `.part` laissé par le R2 est réutilisé par la tentative Dropbox,
    qui reprend à l'octet atteint (verrouillé par `test_resume_continues_across_url_switch`).
  Sur le R2 seul, une coupure entraîne un redémarrage à zéro (comportement sûr, coût en bande passante).
- **Watchdog de stall** : attente maximale entre deux chunks (défaut 60 s, `DOWNLOAD_CHUNK_TIMEOUT_S`) au lieu
  de 3600 s ; un transfert bloqué est interrompu et repris là où il s'était arrêté.
- **Tentatives bornées** avec backoff exponentiel (`DOWNLOAD_MAX_ATTEMPTS`, `DOWNLOAD_RETRY_BACKOFF_S`).
- **Validation systématique** (plus seulement les liens `/scl/fo/`) : rejet des payloads `text/html`,
  `application/json`, XML ; contrôle de la taille vs `Content-Length` ; vérification ZIP (`zipfile.is_zipfile`).
- **Erreurs typées** : `DownloadResult.error_kind` ∈ `not_found | auth | http_error | network | stalled |
  invalid_payload | incomplete | local_io` + `status_code`, `attempts`, `resumed_from`.
- **Progression throttlée** (`DOWNLOAD_PROGRESS_MIN_INTERVAL_S`, défaut 1 s) : ~30 événements par Go au lieu de
  1 700 (corrige C1).
- En-tête `Accept-Encoding: identity` : `Content-Length` reste exact (reprise et contrôle de taille fiables).

### 3.2 Repli R2 → Dropbox (`services/csv_downloader.py`)

- Un `404` sur le `r2_url` déclenche **immédiatement** le repli sur `source_url` + log explicite
  `CSV DOWNLOAD: R2_MISSING url=… filename=…`.
- Si le R2 est **déjà connu comme manquant** (table `download_failures`), le lien Dropbox est tenté **en
  premier** : plus de requête inutile sur un objet expiré (C9).
- Message UI enrichi : « … (R2 absent - repli Dropbox utilisé) ».
- Sur échec définitif : `record_download_failure()` ; sur succès : `clear_download_failure()`.

### 3.3 Persistance et cooldown des échecs

- Nouvelle table `download_failures` (`services/download_history_repository.py`) :
  `url, kind, status_code, attempts, last_error, first_seen_at, last_attempt_at`.
- `services/csv_monitor.py` : cooldown exponentiel `min(15 s × 2^(tentatives-1), DOWNLOAD_COOLDOWN_MAX_S)`
  → fini le re-téléchargement d'un objet expiré toutes les 15 secondes.
- `CSVService.get_monitor_status()` expose `failed_urls` / `failed_urls_count`.

### 3.4 Widget CPU/GPU/RAM (corrige C6 et C7)

- `MonitoringService` publie un **snapshot** rafraîchi par un thread daemon (`start_snapshot_sampler`,
  `SYSTEM_SNAPSHOT_INTERVAL_S` = 2 s) ; `/api/system_monitor` et `/api/stats/dashboard` servent
  désormais ce snapshot (`get_system_status_cached()`) : **plus aucun appel psutil/NVML ni `mkdir`** sur le
  chemin requête.
- `psutil.cpu_percent(interval=None)` : mesure non bloquante (l'ancien `interval=0.1` bloquait 100 ms par appel).
- `routes/decorators.py` : toute réponse API > `SLOW_API_THRESHOLD_MS` (défaut 1 000 ms) est journalisée
  (`SLOW_API …`) — instrumentation permanente du gel.
- `static/utils/PollingManager.js` : garde anti-empilement (un tick est sauté si le précédent n'est pas résolu)
  + backoff progressif sur erreur au lieu de l'arrêt définitif ; compteur `skippedTicks` exposé.
- `static/main.js` : mesure de la durée du `fetch` et du retard de repaint du widget (avertissement > 1 s).

### 3.5 Hygiène des journaux (corrige C1 et C2)

- Le `StreamHandler` est désactivé quand stdout cible déjà `app.log` (`os.path.samefile`) : un seul écrivain.
- `start_workflow.sh` redirige stdout/stderr vers `logs/stdout.log` (rotation dédiée).
- Loggers du chemin chaud (`services.download_service`, `services.csv_downloader`, `services.csv_service`)
  forcés à `INFO`.

### 3.6 Outillage

- `scripts/check_r2_objects.py` : audit lecture seule des `r2_url` (état, taille, `[EN ATTENTE]`/`[déjà traité]`,
  sortie JSON, code 1 si un objet attendu est manquant).

---

## 4. Réglages ajoutés (`.env` / `config/settings.py`)

| Clé | Défaut | Rôle |
|---|---|---|
| `DOWNLOAD_CHUNK_SIZE_BYTES` | 524288 | Taille des écritures disque |
| `DOWNLOAD_CONNECT_TIMEOUT_S` / `DOWNLOAD_CHUNK_TIMEOUT_S` | 15 / 60 | Connexion / watchdog de stall |
| `DOWNLOAD_PROBE_TIMEOUT_S` | 10 | Sonde HEAD |
| `DOWNLOAD_MAX_ATTEMPTS` / `DOWNLOAD_RETRY_BACKOFF_S` | 3 / 1.0 | Tentatives et backoff |
| `DOWNLOAD_PROGRESS_MIN_INTERVAL_S` | 1.0 | Throttle des mises à jour de progression |
| `DOWNLOAD_MIN_ZIP_SIZE_BYTES` / `DOWNLOAD_VALIDATE_ZIP` | 1000000 / true | Validation des archives |
| `DOWNLOAD_COOLDOWN_MAX_S` | 3600 | Plafond du cooldown après échecs |
| `SYSTEM_SNAPSHOT_INTERVAL_S` | 2.0 | Période d'échantillonnage des métriques |
| `SLOW_API_THRESHOLD_MS` | 1000 | Seuil d'alerte des API lentes |

---

## 5. Procédures de vérification

```bash
# 1. Tests
pytest tests/unit tests/integration && npm run test:frontend

# 2. État des objets R2 (code 1 si une archive en attente est manquante)
python scripts/check_r2_objects.py            # ajouter --show-ok / --json / --limit N

# 3. Reprise après interruption : lancer une archive > 1,5 Go puis Ctrl+C en plein transfert
ls -la ~/Téléchargements/*.part               # le reliquat est conservé
grep "resuming at" logs/app.log               # la reprise repart de l'octet atteint, pas de 0

# 4. Réactivité du widget pendant un téléchargement
for i in $(seq 5); do curl -s -o /dev/null -w '%{time_total}\n' http://127.0.0.1:5003/api/system_monitor; done
# attendu : < 0,05 s ; toute réponse lente apparaît en SLOW_API dans app.log

# 5. Volume de journal après un téléchargement de 1 Go
grep -c "CSV download updated" logs/app.log   # attendu : quelques dizaines (au lieu de ~1 700)
grep -c "SLOW_API" logs/app.log
```

---

## 6. Contrat du worker distant (miroir `scripts/R2/`)

Les sources récupérées se répartissent en trois rôles distincts :

| Fichier | Rôle | Déploiement |
|---|---|---|
| `r2-fetch-worker.js` | **Ingestion** : POST authentifié (`X-R2-FETCH-TOKEN`) qui télécharge une source (Dropbox/FromSmash/SwissTransfer) et la publie dans R2, puis renvoie `r2_url` | Worker appelé par le service en amont (Render) |
| `r2-cleanup-worker.js` | **Purge planifiée** : supprime les objets dont `customMetadata.expiresAt` est dépassé | Cron Worker |
| `server.js` | **Service public** : `GET/HEAD https://server.kidpixel.workers.dev/<key>` → corps de l'objet R2 | `server.kidpixel.workers.dev` |

Vérification de cohérence (sondage réel du 2026-09-21 + lecture du code) :

| Comportement attendu côté application | Réalité du worker | Verdict |
|---|---|---|
| Objet absent ⇒ HTTP **404** exploitable comme « R2 expiré » | `server.js:10-12` renvoie `404 Not Found` (corps texte) | ✅ conforme → `error_kind='not_found'` |
| `Content-Type: application/zip` sur les archives | `server.js:17` renvoie le `contentType` R2 (les logs réels montrent `application/zip`) | ✅ conforme |
| `Content-Length` fiable sur le `GET` | fourni par le runtime (ex. `873662065` observé) | ✅ conforme → contrôle de complétude OK |
| `HEAD` sans corps | `200` avec `Content-Type`, **sans** `Content-Length` ni `Content-Disposition` | ✅ géré (la taille vient du `GET`) |
| Le nom de fichier d'origine est disponible | **écart** : le worker d'ingestion *stocke* `contentDisposition` (`r2-fetch-worker.js:425`) mais `server.js` ne le renvoie pas ⇒ `_extract_filename` retombe sur `download_<ts>.zip` pour les enregistrements sans `original_filename` | ⚠️ sans impact en pratique (le webhook fournit toujours `original_filename`, qui a priorité) |
| Reprise HTTP `Range` | **écart** : `server.js:9` appelle `env.R2_BUCKET.get(key)` sans l'option `range` et répond toujours `200` avec le corps complet — vérifié en direct (`Range: bytes=100-199` ⇒ `200`, `content-length: 873662065`) | ⚠️ voir patch ci-dessous |
| Aucune authentification requise pour télécharger | conforme (seul le worker d'ingestion exige un token) | ✅ conforme |
| Le préfixe `/dropbox/` de l'URL | **convention de l'appelant** : `server.js` sert n'importe quelle clé (`pathname`), le préfixe vient du `object_key` construit en amont | ⚠️ couplage : les heuristiques locales (`_is_dropbox_proxy_url`, `_classify_url_type`, `isDropboxProxyUrl`) **exigent** `/dropbox/` dans le chemin ; un changement de préfixe en amont désactiverait l'auto-téléchargement |
| Cache | `Cache-Control: public, max-age=3600` | ✅ sans impact (une réponse en cache reste un corps valide) |

### Patch proposé pour `server.js` (reprise des gros fichiers)

```js
export default {
    async fetch(request, env) {
        const url = new URL(request.url);
        const key = url.pathname.replace(/^\/+/, "");
        if (!key) {
            return new Response("Missing key", { status: 400 });
        }

        // Transmet l'en-tête Range à R2 (R2 renvoie alors un objet partiel)
        const object = await env.R2_BUCKET.get(key, { range: request.headers });
        if (!object) {
            return new Response("Not Found", { status: 404 });
        }

        const headers = {
            "Content-Type": object.httpMetadata?.contentType || "application/octet-stream",
            "Cache-Control": "public, max-age=3600",
            "Accept-Ranges": "bytes",
        };
        // Optionnel : restitue aussi le nom d'origine stocké à l'ingestion
        if (object.httpMetadata?.contentDisposition) {
            headers["Content-Disposition"] = object.httpMetadata.contentDisposition;
        }
        if (object.range) {
            const start = object.range.offset || 0;
            const length = object.range.length ?? (object.size - start);
            headers["Content-Range"] = `bytes ${start}-${start + length - 1}/${object.size}`;
            headers["Content-Length"] = String(length);
            return new Response(object.body, { status: 206, headers });
        }

        return new Response(object.body, { status: 200, headers });
    },
};
```

Aucun changement n'est nécessaire côté application : elle envoie déjà `Range` et gère `200`, `206`, `416`
ainsi que l'absence de support. Le patch fait passer la reprise de « utile sur Dropbox » à « utile partout ».

> **Note sécurité** : `server.js` sert toute clé du bucket sans contrôle d'accès ni validation de préfixe. Les
> clés (`dropbox/<8 hex>/<8 hex>/file`) sont difficiles à énumérer, mais tout objet est lisible par quiconque
> possède l'URL. Une vérification de préfixe (`key.startsWith('dropbox/')`) ou un token de lecture serait un
> durcissement peu coûteux.

---

## 7. Risques résiduels et recommandations

1. **Côté worker (hors dépôt)** : les copies R2 disparaissent après **24 h** (C9). Deux options :
   allonger le TTL (`r2-fetch-worker.js:415`, `setHours(+24)`) ou assumer le repli Dropbox comme chemin
   nominal — c'est le comportement actuel, et `scripts/check_r2_objects.py` permet de suivre la fenêtre utile.
2. **Dropbox comme source de repli** : les liens de dossier peuvent renvoyer des pages intermédiaires ; elles sont
   désormais **rejetées** (validation de payload) au lieu d'être acceptées silencieusement.
3. **Reprise `Range`** : ignorée par `server.js` (constaté en direct) ⇒ sur le R2, une coupure redémarre de zéro ;
   la reprise s'applique sur Dropbox et à travers la bascule R2 → Dropbox. Le patch `server.js` ci-dessus
   supprime cette limitation sans modification locale.
4. **Couplage au préfixe `/dropbox/`** : trois heuristiques locales en dépendent. À surveiller si la convention
   du `object_key` évolue en amont (sinon : plus d'auto-téléchargement, sans erreur explicite).
5. **Fusion hétérogène en cas de changement de source** : si le lien Dropbox pointait vers une *autre* archive
   que celle partiellement téléchargée depuis R2, l'ajout produirait un ZIP invalide — celui-ci est **rejeté**
   par la validation (`zipfile.is_zipfile`) et le `.part` est supprimé, donc jamais de fichier corrompu silencieux.
6. **Fraîcheur des métriques** : le widget affiche une valeur âgée d'au plus `SYSTEM_SNAPSHOT_INTERVAL_S` (2 s)
   au lieu d'un échantillonnage par requête ; `snapshot_age_s` est exposé dans la réponse API.
7. **Découverte pytest** : les exclusions `!test_step5_*.py` de `pytest.ini` ne sont pas appliquées quand un
   répertoire est passé explicitement, d'où des erreurs de collecte `numpy`/`cv2` dans l'environnement `env`
   (indépendant de cet audit, à traiter séparément si souhaité). Pollution connexe : `tests/integration/test_workflow_routes.py:15`
   force `DRY_RUN_DOWNLOADS=true` à l'import, ce qui affecte toute la session de tests.

