# Sécurité — Workflow MediaPipe

Ce document décrit les mécanismes de sécurité **effectivement implémentés** dans le codebase (v4.1/v4.2) et les règles d’usage associées.

## Architecture (source de vérité)

### Monitoring et téléchargements : Webhook-only

Le monitoring des liens de téléchargement repose sur une **source unique** : un endpoint JSON externe configuré via `WEBHOOK_JSON_URL`.

- Backend :
  - `services/webhook_service.py` récupère et normalise les enregistrements (cache TTL + retries).
  - `services/csv_service.py` consomme ces enregistrements et expose un statut “data_source: webhook”.
- Il n’existe plus de fallback “CSV/MySQL/Airtable” en production : les modules legacy sont conservés uniquement comme historique/compatibilité.

Objectif sécurité : réduire la surface d’attaque (moins de connecteurs, moins de secrets, moins de flux parallèles) et centraliser la validation.

### Ouverture explorateur (CACHE_ROOT_DIR uniquement)

- Fonction `FilesystemService.open_path_in_explorer()` n’est plus utilisable par défaut hors environnement bureau contrôlé.
- Gardes d’activation :
  - `DISABLE_EXPLORER_OPEN=1` force le blocage, quelle que soit la configuration.
  - `ENABLE_EXPLORER_OPEN=1` (à activer **explicitement** pour un poste local) autorise l’ouverture même hors DEBUG, tant que l’environnement n’est pas headless.
  - En production/headless (`DISPLAY` et `WAYLAND_DISPLAY` absents), l’ouverture est refusée sauf opt-in clair (`ENABLE_EXPLORER_OPEN=1`).
- Confinement : tout chemin doit appartenir à `CACHE_ROOT_DIR` (issu de `config.settings.Config`), sinon l’opération échoue.
- Journalisation : chaque tentative réussie/échouée est loggée pour audit, les tests `tests/unit/test_filesystem_service.py` valident les garde-fous.

## Validation des entrées

### STEP1 — Sanitisation des noms de fichiers (archives)

Lors de l’extraction des archives (ZIP/RAR/TAR), chaque chemin/membre est filtré via `FilenameSanitizer`.

- Code :
  - `utils/filename_security.py` : `FilenameSanitizer` + `validate_extraction_path()`
  - `workflow_scripts/step1/extract_archives.py` : appel systématique sur chaque membre.

Garanties principales :
- Détection et mitigation des patterns dangereux (path traversal `../`, chemins absolus, etc.).
- Normalisation Unicode (`NFKC`) pour limiter des attaques par homoglyphes.
- Filtrage caractères de contrôle / null byte.
- Compatibilité Windows/Unix : remplacement des caractères interdits et gestion des noms réservés (`CON`, `PRN`, etc.).
- Troncature sur limites conservatrices (chemins/fichiers) + fallback de nom si vide.
- Validation finale que le chemin extrait reste sous le répertoire d’extraction (anti traversal).

### Normalisation des URLs (monitoring Webhook / historique)

Les URLs provenant du webhook (ou persistées dans `download_history.json`) sont normalisées pour éviter des doublons et des variantes malformées.

- Code : `services/csv_service.py` → `CSVService._normalize_url()`

Règles principales (best-effort) :
- `strip()` + `html.unescape()`
- Nettoyage de séquences double-encodées fréquentes (ex: `amp%3B`)
- Normalisation `scheme` + `hostname` en minuscules
- Suppression ports par défaut (80/443)
- Normalisation du `path` (unquote → suppression `//` → trim `/` final → quote)
- Normalisation du querystring (tri, suppression entrées vides)
- Cas Dropbox : forçage `dl=1` et déduplication des paramètres `dl`

Note : cette normalisation vise la **déduplication** et la stabilité d’identifiants. Elle ne constitue pas à elle seule une politique d’autorisation réseau (allowlist) ; le système applique ensuite ses règles “Dropbox-only” côté auto-download.

## Prévention XSS (Frontend)

### ✅ Corrections appliquées (Audit 2026-01-17)
- **apiService.js** : Remplacement de `.innerHTML +=` par `appendItalicLineToMainLog()` utilisant `textContent`
- **Validation** : Fonction `appendItalicLineToMainLog()` crée avec `i.textContent = String(message ?? '')` (DOM-safe)

### Règle
Toute donnée dynamique (logs, messages, URLs, noms de fichiers) doit être traitée comme **non fiable**.

### Mécanismes en place
- Utilitaire : `static/utils/DOMBatcher.js` → `DOMUpdateUtils.escapeHtml(text)`
- Logs UI : `static/uiUpdater.js` → `parseAndStyleLogContent()` applique `escapeHtml()` **avant** de générer du HTML stylé (`<span class="log-line ...">`).

Bonnes pratiques imposées :
- Privilégier `textContent` pour les chaînes qui n’ont pas besoin de markup.
- Si un rendu HTML est nécessaire (ex: logs avec classes CSS), **ne jamais injecter** une chaîne non échappée : utiliser `DOMUpdateUtils.escapeHtml()` puis uniquement ajouter du markup contrôlé (tags/classes fixes).

### Optimisations Performance vs Sécurité (v4.2)

Les optimisations récentes de `parseAndStyleLogContent()` maintiennent la sécurité XSS tout en améliorant les performances :

```javascript
// static/uiUpdater.js - approche optimisée
function parseAndStyleLogContent(content) {
    // Regex pré-compilées pour réduire la pression CPU/GC
    const patterns = {
        error: /\[ERROR\]|\[ERREUR\]/gi,
        warning: /\[WARNING\]|\[AVERTISSEMENT\]/gi,
        // ... autres patterns
    };
    
    // Échappement XSS APPLIQUÉ AVANT tout traitement HTML
    const escapedContent = DOMUpdateUtils.escapeHtml(content);
    
    // Traitement linéaire avec boucle optimisée
    return escapedContent.replace(/\n/g, '<br>')
                       .replace(patterns.error, '<span class="log-error">$&</span>')
                       // ... autres remplacements
                       .trim();
}
```

**Points clés :**
- `DOMUpdateUtils.escapeHtml()` reste **obligatoire** et est appliqué **en premier**
- Les regex sont pré-compilées pour éviter la ré-compilation à chaque appel
- La boucle de traitement est linéaire pour réduire la pression sur le garbage collector
- Export de la fonction pour les tests Node : `export { parseAndStyleLogContent }`

## Contrôle d’accès (endpoints internes)

Certaines routes sont réservées aux communications internes (workers/serveurs).

- Variable d’environnement : `INTERNAL_WORKER_COMMS_TOKEN`
- Contrôle : header HTTP `X-Worker-Token`
- Implémentation : `config/security.py` → décorateur `@require_internal_worker_token`
- Exemples d’usage : `routes/api_routes.py` (endpoints `/api/*` protégés)

En l’absence de token configuré, l’API répond avec une erreur (configuration invalide). En production, ce token ne doit jamais être un “dev default”.

## Filesystem (STEP7) — robustesse NTFS/fuseblk

La finalisation (STEP7) doit fonctionner même lorsque la destination est un montage NTFS via FUSE (`fuseblk`) où `chmod/utime` échouent souvent (`EPERM`).

- Code : `workflow_scripts/step7/finalize_and_copy.py`

Stratégie implémentée :
1. **Sélection d’une destination inscriptible** :
   - Utilise `OUTPUT_DIR` si test d’écriture réussi.
   - Sinon bascule vers `FALLBACK_OUTPUT_DIR` si défini.
   - Sinon bascule vers `_finalized_output/` dans la racine du dépôt.
2. **Détection support `chmod`** sur la destination (création d’un fichier temporaire + tentative `os.chmod`).
3. **Copie sans préservation des permissions** si `chmod` n’est pas supporté :
   - Tentative `rsync -a --no-perms --no-owner --no-group --no-times`
   - Sinon `cp -r --no-preserve=mode,ownership`
   - Sinon fallback Python (`os.walk` + `shutil.copyfile` sans `copystat`).

Objectif sécurité/robustesse : préserver l’intégrité des données copiées sans échouer sur des métadonnées POSIX non supportées.
