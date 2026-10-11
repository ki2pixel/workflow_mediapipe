# Compatibilité EffectCraft 0.8.0 — MediaSolution-EC, étape 8 et outils

**Date** : 2026-10-11
**Objet** : vérifier l'impact d'une mise à jour EffectCraft 0.7.0 → 0.8.0 (release du 11/10/2026) sur l'intégration Linux : panel `MediaSolution.jsx`, étape 8 headless du workflow, outils Python de `scripts/MediaSolution-EC/tools/`.

## Méthode

- Sources 0.8.0 (tag `v0.8.0`, commit `f953cd2`) clonées et diffées avec le checkout local 0.7.0.
- Release notes v0.8.0 + PRs ciblées (#479 `importFile`, #558 scripts par nom, #676 chemins relatifs).
- Tests réels avec le binaire `effectcraft-cli 0.8.0` extrait du tarball Linux (`XDG_CONFIG_HOME` isolé), sans toucher à l'installation système 0.7.0 ni à la configuration de l'utilisateur.

## Compatible ✔

### Format `.ecproj`

- `schema: 2` **inchangé** ; seul ajout de format : `settings.working_gamma` (défaut 2.2, `#[serde(default)]`) et un type de paramètre d'effet dans `props.rs`. Aucune clé lue par les convertisseurs n'est renommée ou supprimée.
- **Rétrocompatibilité de lecture vérifiée** : le binaire 0.8.0 réouvre un `.ecproj` 0.7.0 (fixture `Camille-test`) — `app.project.numItems` → `3 items, comp=clip1_9x16`.
- `.ecprojx` (nouveau) est la variante **XML** de « Save a Copy As XML » : sans rapport avec `.ecproj`.

### Tools Python (`scripts/MediaSolution-EC/tools/`)

- `ecproj_to_aep.py` convertit un `.ecproj` produit par la 0.8.0 (test réel comp + solide → `.aep` écrit, avertissement normal sur le média source absent).
- Les raccourcis Bureau utilisent `/usr/bin/python3` (py_aep + fontTools) ; le venv `env` du projet n'a pas ces dépendances — sans lien avec EffectCraft.

### Panel `MediaSolution.jsx`

- Toutes les APIs utilisées (`app.project`, `CompItem`, `layers`, `msProp` → `transform.property`, `duplicate()/remove()/parent`, `audioEnabled`, `label`, `File`/`Folder`, `writeLn`, `$.global`) existent en 0.8.0 : le diff de `prelude.js` (48 lignes) ne touche aucune de ces zones.
- `importFile(ImportOptions)` importe désormais **un seul fichier** sauf si `ImportOptions.sequence` est vrai — exactement notre usage (correction en notre faveur).
- `writeLn`, `effectcraft-cli script FILE.jsx [F.ecproj] | --eval` intacts ; `script.run` accepte toujours un chemin de fichier arbitraire (refus limité aux `.jsxbin`).
- `scripting.allowScriptsWriteFiles` existe toujours dans les préférences.

## Incompatible ✘ — le mode headless des scripts

**En 0.8.0, un script ne peut plus s'octroyer les droits d'écriture, et le CLI headless n'honore pas la préférence utilisateur.**

- Nouveau garde-fou (`crates/engine/src/commands/settings.rs`) : `prefs.set` lancé **depuis un script** est refusé dès qu'il change les permissions de scripting :
  > `Scripts can't change what scripts are allowed to do. Change it yourself in Settings ▸ Scripting & Expressions ▸ Application Scripting.`
- Le CLI headless ne charge pas `prefs.json` (seul `auto_save` est lu, avec `--autosave`) : `prefs.get scripting.allowScriptsWriteFiles` renvoie `false` même quand la configuration utilisateur dit `true`.
- Le gate de script (`crates/script/src/runtime.rs`) bloque alors **toute lecture hors dossier projet et toute écriture** ; le panel voit les dossiers comme « introuvables ».

Preuves (binaire 0.8.0 extrait, fixture `Camille-test`) :

```
$ effectcraft-cli script step8_driver_*.jsx
…:1851:8: Scripts can't change what scripts are allowed to do. Change it yourself in
Settings ▸ Scripting & Expressions ▸ Application Scripting.

# Même driver sans la ligne prefs.set :
[WARNING] 14:36:55 | Dossier ignoré (introuvable) : /…/Camille-test
MS_BATCH_RESULT: {"ok":false,"error":"Aucun projet à traiter (vérifiez docs/ et les exclusions)"}
```

→ L'étape 8, `tests/smoke_driver.js` et `tests/run_batch_headless.js` sont **inutilisables en headless pur** en 0.8.0 (0.7.0 : validés).

## Option retenue : mode bridge (implémenté et validé)

L'étape 8 supporte désormais deux modes d'exécution, avec auto-détection de version (`STEP8_MODE=auto`) :

| EffectCraft | Mode | Comportement |
|---|---|---|
| ≤ 0.7.0 | `headless` | inchangé : `effectcraft-cli script` autonome |
| ≥ 0.8.0 | `bridge` | `effectcraft-cli script <driver> --bridge <port>` : le driver tourne dans l'application ouverte (qui charge `prefs.json`), avec pré-vol `exec prefs.set` via le bridge |

Prérequis du mode bridge : lancer l'application avec `effectcraft --control 9877`
(`STEP8_BRIDGE_PORT` configurable). Sans instance en écoute, l'étape échoue avec un message clair.

**Validation réelle (2026-10-11, binaire 0.8.0 extrait, application `--control 9879`, config copiée)** :

- Auto-détection : `Mode d'exécution : bridge (effectcraft-cli 0.8.0)` ; pré-vol `prefs.set` accepté (`prefs.get` → `true`).
- Lancement automatique réel (14:59) : application démarrée par le wrapper (`effectcraft --control 9878 --empty`), canal prêt en 0,5 s, batch 2/2 `.ecproj`, exit 0. L'application reste ouverte après le batch (`STEP8_AUTO_LAUNCH_APP=false` ou `--no-launch-app` pour revenir à l'erreur explicite).
- Batch complet sur la fixture : 2/2 `.ecproj` produits (`savedBy: "0.8.0"`, `schema: 2`), exit 0.
- Conversion `tools/ecproj_to_aep.py --verify` du projet 0.8.0 : comp 1080×1920, 2 segments, labels/ancres/positions identiques au comportement 0.7.0.
- Non-régression 0.7.0 : smoke headless (`auto` → `headless`) 2/2 `.ecproj`, exit 0.

### Alternatives écartées

- **Rester en 0.7.0** : tout fonctionne, mais aucune raison de retarder la mise à jour une fois le bridge en place ; le mode headless reste le défaut pour les versions ≤ 0.7.0.
- **Remonter l'issue en amont** : reste utile (le CLI headless devrait charger la préférence ou offrir un drapeau), mais n'est plus bloquant pour l'usage.

## Vérifications à refaire après une éventuelle installation

- Smoke complet headless : `env/bin/python workflow_scripts/step8/run_mediasolution_ec.py --folder <copie fixture>`.
- Smoke via bridge : `effectcraft --control 9878` puis `effectcraft-cli --bridge 9878 script <driver>`.
- Conversion : `python3 scripts/MediaSolution-EC/tools/ecproj_to_aep.py <ecproj du panel> --verify`.
- Rejouer `scripts/MediaSolution-EC/tests/smoke_driver.js` dans l'application.
