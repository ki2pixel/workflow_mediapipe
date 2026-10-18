# Installation — Media Solution v12.0 CEP

**TL;DR** : copier le dossier dans le répertoire d'extensions CEP, activer le mode debug dans After Effects, redémarrer, ouvrir le panel. Cinq minutes, sans build ni dépendance à installer.

## Prérequis

- **After Effects 2024** (v24.0) ou plus récent (compatible v13.0+ via fallback ExtendScript)
- **PyShiftBridge** dans `%USERPROFILE%\Documents\Scripts\PyShiftBridge\` (dossier recherché par défaut par l'extension)
- **Python 3.10+** pour l'environnement système global
- **Workflow MediaPipe v4.1** : les CSV de cuts et les fichiers de tracking JSON dans le sous-dossier `docs/` du projet

> **PyShiftAE** : la version installée est la **v1.0.1** (migrée le 14/07/2026 via `PyShiftBridge/tools/migrate_to_1.0.1.py`). Le transport effectif est **Mailbox pour le host ExtendScript + fallback ExtendScript**; le pipe nommé maison (`\\.\pipe\mediasolution`, serveur ctypes dans `bridge_daemon.py`) est le transport **du client (Node)** depuis le 07/08/2026. Le pipe CEPy d'origine n'existe pas dans PyShiftAE (voir `confirmation_diagnostic.md`).

## Installation rapide

1. Copier le dossier `MediaSolution-CEP` dans le répertoire d'extensions CEP :
   - **Windows** : `%APPDATA%\Adobe\CEP\extensions\`
   - **macOS** : `~/Library/Application Support/Adobe/CEP/extensions/` (non testé, support non garanti)
2. Ouvrir After Effects, activer `Help > Enable Debugging`, redémarrer.
3. Ouvrir `Window > Extensions > Media Solution v12.0` (le menu réel est celui du manifest : sans "CEP" dans le nom).

## Configuration de la liaison Python

Dans le panel, une seule variable à renseigner :

- **Python Command** : chemin complet vers `python.exe`, ou vide pour la résolution via `python`/`py -3` dans le PATH.

Le dossier CEPy machine (`manifest.py`, `entry.py` copiés dans le dossier CEP machine, via `PyShiftBridge/tools/copy_cepy_config.py`) ne sert qu'au mode pipe natif, jamais validé avec PyShiftAE. L'extension fonctionne sans cette configuration; elle reste inoffensive mais inerte.

## Vérification

1. Ouvrir le panel.
2. Dans la console de logs, le transport doit afficher `Transport PyShiftBridge: pipe` (mode nominal depuis le 07/08/2026), avec repli `mailbox` si le démon n'est pas encore prêt (la bascule est automatique au health check suivant).
3. Sélectionner avec "Parcourir..." un dossier projet contenant `docs/` avec vidéos, CSV de cuts et tracking JSON.
4. Lancer "Diagnostics" pour valider la structure.

## Dépannage

| Symptôme | Causes possibles | Solutions |
|---|---|---|
| L'extension n'apparaît pas dans le menu | Dossier mal placé, debug désactivé, permissions | Vérifier l'emplacement, activer `Help > Enable Debugging`, redémarrer AE, vérifier les droits en lecture/écriture du dossier |
| Erreur de communication CEP | Cache CEP, `CSInterface.js` manquant | Redémarrer AE (purge le cache), vérifier `client/CSInterface.js`, ouvrir la console CEP (F12) |
| Ponts Python non fonctionnels | Mauvais chemin python, scripts inaccessibles | Vérifier le chemin dans la config, tester `python` en ligne de commande, lire les logs `[PY]` du panel |
| Démon reste indisponible / voyant rouge | Ancien verrou orphelin PID (résolu le 20/08/2026 par Mutex Windows) | Supprimer `Documents/PyShiftAE_CEP_Bridge/bridge_daemon.lock` si sur ancienne version, mettre à jour `bridge_daemon.py`, relancer via le bouton "Relancer" |
| Transport bloqué en `mailbox` alors que le démon tourne | Serveur pipe du démon muet (bug flush `DisconnectNamedPipe` corrigé le 07/08/2026) | Vérifier `daemon_loop.log` (`[pipe] Connexion pipe traitee` sans réponse), relancer le démon, mettre à jour `bridge_daemon.py` |
| Dossier projet non reconnu | Structure manquante | Le dossier doit contenir un sous-dossier `docs/` avec les vidéos et fichiers de tracking; lancer "Diagnostics" pour les erreurs précises |

## Mise à jour et sauvegarde

- **Mise à jour** : fermer AE, remplacer le dossier `MediaSolution-CEP`, redémarrer. La configuration survit via localStorage.
- **Sauvegarde** : "Exporter Config" produit un JSON à restaurer avec "Importer Config".

## Aller plus loin

- Architecture et concepts : [README.md](./README.md)
- Debug approfondi (pollution JSON, ponts, gels) : [DEBUG_CHECKLIST.md](./DEBUG_CHECKLIST.md)
- Guides des bibliothèques Python : [PYSHIFTAE_DEVELOPER_GUIDE.md](./PYSHIFTAE_DEVELOPER_GUIDE.md) et [PY_AEP_DEVELOPER_GUIDE.md](./PY_AEP_DEVELOPER_GUIDE.md)
