# Miroir des workers Cloudflare R2

> **Source de vérité : Cloudflare.** Ces fichiers sont une copie de sauvegarde des workers déployés,
> récupérés le 2026-09-21. Toute modification ici n'a **aucun effet** tant qu'elle n'est pas redéployée
> (`wrangler deploy`), et toute modification distante doit être reportée ici pour garder l'audit à jour.
> Voir `docs/audits/audit_telechargement_r2.md` (section « Contrat du worker distant »).

## Rôle des trois workers

| Fichier | Rôle | Entrée | Sortie |
|---|---|---|---|
| `r2-fetch-worker.js` | **Ingestion** (pull) : télécharge une source externe et la publie dans le bucket R2 | `POST` JSON `{source_url, object_key, bucket, provider, email_id}` + en-tête `X-R2-FETCH-TOKEN` | `{success, r2_url, original_filename, content_length, …}` |
| `r2-cleanup-worker.js` | **Purge planifiée** : supprime les objets R2 échus (`customMetadata.expiresAt`) | déclencheur cron | — |
| `server.js` | **Service public** consommé par le pipeline local | `GET/HEAD https://server.kidpixel.workers.dev/<key>` | corps de l'objet R2 |

Chaîne complète :

```
mail → service amont (Render) → r2-fetch-worker (POST) → bucket R2 (TTL 24 h)
                                        │
                                        └─ renvoie r2_url → JSON webhook
                                                              │
                             pipeline local (DownloadService) ─┘  ← server.js sert l'objet
                             puis r2-cleanup-worker purge après 24 h
```

## Points de contrat dont dépend le pipeline local

1. **TTL des objets = 24 h** (`r2-fetch-worker.js` : `expiresAt = now + 24h`, puis purge par
   `r2-cleanup-worker.js`). Au-delà, l'URL `r2_url` répond 404 et l'application bascule sur le lien Dropbox
   d'origine — c'est le **chemin nominal** pour toute archive non récupérée le jour même.
   Diagnostic : `python scripts/check_r2_objects.py` (liste les objets `[EN ATTENTE]` manquants).
2. **404 = objet expiré** ⇒ `DownloadResult.error_kind == 'not_found'` ⇒ repli Dropbox immédiat,
   échec persisté dans `download_failures`, et tentative Dropbox en premier aux essais suivants.
3. **Le préfixe `/dropbox/` de l'URL est une convention de l'appelant** (`server.js` sert n'importe quelle clé
   du bucket). Trois heuristiques locales en dépendent : `csv_service._is_dropbox_proxy_url`,
   `webhook_service._classify_url_type`, `static/csvWorkflowPrompt.js:isDropboxProxyUrl`. Si ce préfixe change
   en amont, l'auto-téléchargement s'arrête **silencieusement** : à surveiller.
4. **`server.js` n'implémente pas `Range`** (vérifié en direct le 2026-09-21 : `Range: bytes=100-199` ⇒ `200`
   avec le corps complet). Conséquence : sur le R2, une coupure repart de zéro ; la reprise effective a lieu
   sur le lien Dropbox et à travers la bascule R2 → Dropbox (le `.part` est réutilisé). Le correctif proposé
   (transmettre `range` à `env.R2_BUCKET.get`) est fourni dans le rapport d'audit ; il ne nécessite **aucun**
   changement côté application.
5. **Aucune authentification** sur `server.js` : tout objet du bucket est lisible par qui possède l'URL.
   Un contrôle de préfixe (`key.startsWith('dropbox/')`) ou un token de lecture serait un durcissement simple.
6. **Le worker d'ingestion refuse les pages HTML** (`text/html` ⇒ 502) : un objet stocké est un vrai fichier.
   La validation locale (signature `PK`, `zipfile.is_zipfile`) reste utile pour le repli Dropbox, qui peut
   renvoyer des pages intermédiaires en 200.
7. **Limite d'ingestion des partages Dropbox sans `Content-Length`** : le worker bufferise alors le flux en
   mémoire et abandonne au-delà de **50 Mo** (`413`, `r2-fetch-worker.js:372-390`), avec un timeout de 120 s
   pour les partages de dossier (`:226`). Un partage volumineux qui n'expose pas de `Content-Length` n'obtient
   donc **aucune** copie R2 : seule la voie Dropbox locale reste possible. Les archives actuellement servies par
   R2 exposent une taille, la limite n'est donc pas atteinte en pratique.

## Modifier un worker

1. Éditer le fichier **chez Cloudflare** (ou ici puis déployer) ; le token `R2_FETCH_TOKEN` et la variable
   `R2_PUBLIC_BASE_URL` sont configurés dans l'environnement du worker, pas dans ce dépôt.
2. Redéployer, puis **re-synchroniser ce miroir** et ajuster `docs/audits/audit_telechargement_r2.md`.
3. Contrôle post-déploiement : `python scripts/check_r2_objects.py --limit 5 --show-ok` doit renvoyer `OK`
   pour les objets récents, et (si le patch `Range` est appliqué) la reprise doit être visible dans
   `logs/app.log` via `resuming at …` sur une archive interrompue > 1,5 Go.
