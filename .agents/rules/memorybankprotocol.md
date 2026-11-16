---
trigger: always_on
description: Memory Bank Protocol (Version Fast-Filesystem MCP-Optimized)
globs: 
---

# Protocole Memory Bank (MCP fast-filesystem Optimisé)

Cycle de vie du contexte persistant du projet via le serveur MCP `fast-filesystem` pour minimiser le coût en tokens.

## 1. Protocole d'Initialisation Sélective
- **Déclencheur** : `first_interaction` | **Priorité** : immédiate | **Requis** : oui
- **Actions Requises** :
  1. **MCP Pull Initial** : Appeler `fast_read_file(path="/home/kidpixel/workflow_mediapipe/memory-bank/activeContext.md")`.
  2. **Vérification d'État** : Intégrer les bloqueurs, le focus courant et les prochaines étapes.
  3. **Contrainte de Sobriété** : Ne **jamais** charger `productContext.md` ou `systemPatterns.md` sans besoin explicite d'architecture.
  4. **Préfixe Obligatoire** : Débuter la réponse par `[MEMORY BANK: ACTIVE (MCP-PULL)]`.
  5. **Tolérance aux Pannes** : Si le serveur est indisponible, l'indiquer et poursuivre sans contexte mémoire.
  6. **Chemins Absolus Exclusifs** : Utiliser **uniquement** des chemins absolus (`/home/kidpixel/workflow_mediapipe/memory-bank/...`) avec les outils `fast_*`. Ne jamais utiliser de chemins relatifs.

## 2. Structure & Rôles des Fichiers
- **`productContext.md`** : Périmètre, finalité et exigences globales du projet.
- **`activeContext.md`** : État de session, décisions récentes et tâches actives.
- **`systemPatterns.md`** : Patrons récurrents (architecture, flux, tests).
- **`decisionLog.md`** : Décisions techniques majeures et arbitrages.
- **`progress.md`** : Suivi des réalisations, tâches en cours et prochaines étapes.

## 3. Normes de Mise à Jour & Archivage
- **Fréquence** : Mise à jour en fin de tâche majeure ou sur commande `UMB`.
- **Format Horodaté** : `[YYYY-MM-DD HH:MM:SS] - [Résumé]` (obligatoire pour tout log).
- **Politique de Rétention (90 jours)** : Archiver les entrées anciennes vers `memory-bank/archives/*.md` via `fast_write_file`.
- **Contrôle d'Intégrité** : Vérifier l'absence de marqueurs d'élision `⟦PRUNÉ…⟧` avant toute réécriture.

## 4. Règles Spécifiques au Contexte
- **Documentation** : Avant de répondre à des questions sur la doc, énoncer : *"I will consult the project's internal documentation."*
- **Architecture & Code** : Avant toute refonte, énoncer : *"I will adhere to the project's mandatory architectural and coding standards."* et consulter [codingstandards.md](file:///home/kidpixel/workflow_mediapipe/.agents/rules/codingstandards.md).

## 5. Commande Spéciale : Update Memory Bank (UMB)
- Déclencheur : Message utilisateur correspondant à `^(Update Memory Bank|UMB)$`.
- Processus : Acknowledger avec `[MEMORY BANK: UPDATING]`, auditer les deltas de la session, synchroniser `progress.md` et `activeContext.md` via `edit_file`, sans dupliquer l'historique complet.
