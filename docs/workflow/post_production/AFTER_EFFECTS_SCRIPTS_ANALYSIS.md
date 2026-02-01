# Analyse des Scripts After Effects - Post-Production MediaPipe

## Date d'analyse
2026-01-30

## Scripts analysés
- `Media-Solution-v11.2-production.jsx` - Script principal de post-production
- `Analyse-Écart-X-depuis-JSON-et-Label-Vidéo36_good.jsx` - Script de recentrage intelligent

## 1. Rôle dans le Workflow MediaPipe

### Positionnement
Les scripts After Effects opèrent **offline** sur Windows (car AE n'existe pas sur Linux) et interviennent **après STEP7** comme phase de post-production créative.

### Media-Solution-v11.2.jsx
**Fonction**: Automatisation de la création de projets AE à partir des données STEP7
- Lit la structure `CACHE_ROOT_DIR/project_name/docs/`
- Crée des compositions 1080x1920 (format mobile 9:16)
- Applique les découpes de scènes (STEP3) via CSV
- Génère des fichiers AEP dans sous-dossier `projets/`

### Analyse-Écart-X.jsx
**Fonction**: Recentrage intelligent basé sur les données de tracking (STEP5)
- Analyse les JSON tracking frame-by-frame
- Corrèle les données audio (STEP4) pour confirmation des locuteurs
- Applique un recentrage statique optimisé dans AE

## 2. Cohérence avec les Données STEP4/5

### ✅ Points Cohérents
- **Corrélation audio-visuelle**: Utilisation correcte de `is_speech_present` et `active_speaker_labels`
- **Priorisation intelligente**: Hiérarchie face>person avec confirmation audio
- **Support bbox**: Exploitation de `bbox_width/height` pour optimisation
- **Mapping speakers**: Correspondance `video_speakers` ↔ `active_speaker_labels`

### ❌ Incohérences et Lacunes
- **Format JSON STEP5**: Recherche manuelle de noms de champs variables au lieu du format standard
- **Exploitation partielle STEP4**: Utilisation superficielle des données audio riches (embeddings, diarization ignorés)
- **Gestion temporelle fragile**: Correction linéaire approximative pour désalignement frames
- **Contrainte technique critique**: Les JSON enrichis de STEP5 (blendshapes) sont trop massifs pour After Effects et provoquent des crashs
- **Données STEP6 sous-exploitées**: Le JSON reducer de STEP6 devrait être la source primaire, mais manque de données de tracking enrichies

### 🔄 Stratégie Recommandée STEP5/STEP6

**Problème identifié**:
- STEP5 génère des JSON massifs avec blendshapes (plusieurs MB) → Crashs After Effects
- STEP6 produit des JSON réduits mais perd des données de tracking utiles
- Scripts AE tentent de parser STEP5 directement → Instabilité

**Solution proposée**:

1. **Parsing optimisé STEP5**:
   - Implémenter un streaming parser pour éviter de charger tout le JSON en mémoire
   - Extraire uniquement les champs nécessaires (centroid_x, bbox_width/height, confidence)
   - Ignorer les blendshapes et landmarks volumineux dans AE

2. **Enrichissement STEP6**:
   - Ajouter à STEP6 les données de tracking essentielles de STEP5 si manquantes
   - Conserver centroid_x, bbox_width/height, source, label, confidence
   - Générer un JSON intermédiaire optimisé pour AE

3. **Fallback intelligent**:
   - Prioriser STEP6 si disponible et complet
   - Compléter avec parsing sélectif de STEP5 si données manquantes
   - Validation de cohérence entre les deux sources

### Exploitation des Données STEP4/5

#### STEP4 (Audio) - Exploitation Partielle

**✅ Utilisé**:
- `is_speech_present`: Détection parole
- `active_speaker_labels`: Identification locuteurs

**❌ Non Exploité**:
```json
// Données STEP4 riches ignorées
{
  "speaker_embeddings": [...],      // Embeddings locuteurs
  "diarization": {...},            // Segmentation temporelle
  "vad": {...},                    // Voice Activity Detection
  "audio_features": [...]          // Caractéristiques audio
}
```

#### STEP5 (Tracking) - Exploitation Partielle mais Optimisée

**✅ Bien Exploité**:
- `centroid_x`: Positionnement horizontal
- `bbox_width/height`: Surface pour tie-breaker
- `source`: Type de détecteur (face_landmarker/object_detector)
- `label`: Classification (person)

**⚠️ Contrainte Technique**:
- **JSON massifs**: Les fichiers complets avec blendshapes (plusieurs MB) provoquent des crashs AE
- **Parsing limité**: Nécessité d'extraction sélective pour éviter surcharge mémoire

**❌ Non Exploité (volontaire)**:
```json
// Données STEP5 ignorées pour stabilité AE
{
  "landmarks": [...],              // Points faciaux détaillés (trop volumineux)
  "blendshapes": [...],            // Expressions faciales (crashs AE)
  "tracking_quality": {...}        // Qualité de suivi (secondaire)
}
```

**Solution actuelle**: Parsing manuel `optimizedScanEngine()` pour extraire uniquement les champs nécessaires

## 3. Améliorations Recommandées

### Priorité Haute
1. **Implémenter stratégie STEP5/STEP6**: Prioriser STEP6 + parsing sélectif STEP5 pour éviter crashs AE
2. **Parser streaming STEP5**: Implémenter lecture par chunks pour gérer JSON massifs sans crash
3. **Enrichir STEP6**: Ajouter données tracking essentielles (centroid, bbox, confidence) dans reducer
4. **Validation temporelle**: Vérifier cohérence frames audio/vidéo entre sources

### Priorité Moyenne
1. **Fallback intelligent**: Logique de complétion STEP5 → STEP6 pour données manquantes ✅
2. **Exploiter embeddings locuteurs**: Matching audio-visuel plus robuste (différé)
3. **Support multi-faces**: Layout intelligent pour plusieurs cibles (différé)
4. **Optimisation mémoire**: Gestion proactive des gros JSON dans environnement AE ✅

### Priorité Basse
1. **Utiliser blendshapes (conditionnel)**: Détection expressions uniquement si système robuste
2. **Confidence weighting**: Pondération par scores de détection
3. **Analytics avancés**: Rapports qualité de recentrage

## 4. Limitations Techniques

### Contraintes Environnement
- **Windows uniquement**: After Effects non disponible sur Linux
- **Offline**: Pas d'intégration directe avec backend Flask
- **ExtendScript ES3**: Limitations JavaScript vs. standards modernes

### Performance
- **Memory management**: Risque de leaks sur gros JSON
- **Synchronous operations**: Blocage UI AE
- **No multiprocessing**: Traitement séquentiel uniquement

## 5. Recommandations d'Usage

### Workflow Optimisé
```
STEP7 (Finalisation) → Fichiers dans CACHE_ROOT_DIR/
↓
Media-Solution.jsx → Création AEPs avec découpes
↓  
Analyse-Écart-X.jsx → Recentrage intelligent
↓
Post-production créative manuelle
```

### Bonnes Pratiques
1. **Vérifier structure STEP7**: Assurer `docs/` complet avec vidéos + métadonnées
2. **Valider JSON**: Contrôler intégrité fichiers tracking/audio
3. **Prioriser STEP6**: Utiliser JSON réduits comme source principale pour stabilité AE
4. **Parsing sélectif**: N'extraire que les champs nécessaires de STEP5 si complément requis
5. **Monitoring**: Observer logs pour détection problèmes et crashs mémoire
6. **Backup**: Conserver AEPs originaux avant recentrage

## 6. Conclusion

Les scripts After Effects sont **fonctionnels et pertinents** pour la post-production MediaPipe. Le script principal (`Media-Solution`) remplit correctement son rôle de bridge STEP7→AE. Le script de recentrage (`Analyse-Écart-X`) est **cohérent** avec les données STEP4/5 mais fait face à une **contrainte technique majeure** : les JSON massifs de STEP5 provoquent des crashs dans After Effects.

La **stratégie recommandée** est d'optimiser l'utilisation des données en :
1. **Priorisant STEP6** comme source principale (JSON réduits)
2. **Enrichissant STEP6** avec les données essentielles de STEP5
3. **Implémentant un parsing sélectif** de STEP5 uniquement en complément

Cette approche permettrait de maintenir la stabilité d'After Effects tout en exploitant intelligemment les richesses des données de tracking. Le script `Analyse-Écart-X` reste particulièrement pertinent pour la post-production créative mais nécessite ces adaptations pour une utilisation robuste en production.

Malgré les contraintes techniques (Windows, ES3, limitation mémoire AE), ces scripts constituent une extension précieuse du workflow MediaPipe pour la création post-production.

## 7. Implémentation (2026-01-30) — Points Priorité Haute ✅

### Changements livrés
- `workflow_scripts/step6/json_reducer.py`
  - Sortie tracking enrichie: `confidence`, `fps`, `total_frames`.
  - Sortie tracking standardisée: écrit en priorité `*_tracking.json` (en conservant le format `frames_analysis`).
  - Ajout d'un bloc non-bloquant `temporal_alignment` (warning mismatch fps/frames audio↔vidéo).
  - Écriture atomique + skip des schémas inattendus (évite d'écraser des JSON non conformes).
- `scripts/after_effects/Analyse-Écart-X-depuis-JSON-et-Label-Vidéo36_good.jsx`
  - Priorise `*_tracking.json` (STEP6) lors de l’auto-détection.
  - Fallback STEP5: parsing streaming basé sur `readln()` + buffer (pas de `file.read()` complet).
  - Support `confidence` côté parsing (non bloquant).

### Procédure opérateur (≤200 mots)
1. Après STEP7, ouvrir le projet AE et vérifier que la vidéo est sous `docs/`.
2. Vérifier la présence de `nom_video_tracking.json` (STEP6) et `nom_video_audio.json`.
3. Lancer le script `Analyse-Écart-X...jsx`.
4. Si `*_tracking.json` est présent, il sera utilisé en priorité (plus stable). Si absent, le script tentera le `.json` STEP5 en parsing streaming.
5. En cas de désalignement audio/vidéo, consulter le log du script AE et/ou le champ `temporal_alignment` dans `*_tracking.json`.

### Validation
- `python3 -m py_compile workflow_scripts/step6/json_reducer.py`
- `pytest -q tests/unit/test_step6_json_reducer.py`

---

## 8. Implémentation (2026-01-30) — Points Priorité Moyenne ✅/↩︎

### Changements livrés
- `workflow_scripts/step6/json_reducer.py`
  - **Fallback intelligent STEP6⇄STEP5 (legacy)** : si `*_tracking.json` (STEP6) existe mais est **incomplet** (champs essentiels manquants), le reducer tente de réduire aussi `*.json` (STEP5 legacy) et **merge** les champs manquants par `frame` + `id`.
  - Merge non destructif : ne remplace pas les valeurs déjà présentes dans STEP6.
  - Garde-fou : enrichissement uniquement si un fichier legacy est disponible *et* si le schéma STEP6 est détecté comme incomplet.
- `workflow_scripts/step6/json_reducer.py` (audio)
  - Ajout `speaker_stats` (léger) dans `*_audio.json` réduit : `unique_speakers` + `speaker_frame_counts` (utile pour diagnostiquer / stabiliser des heuristiques de matching côté AE sans charger le JSON complet).

### Validation
- `pytest -q tests/unit/test_step6_json_reducer.py` (inclut un test d’enrichissement legacy + test `speaker_stats`).

### Notes (différé)
- **Embeddings locuteurs** : les sorties STEP4 actuelles (Pyannote + Lemonfox wrapper) ne persistents pas d’`speaker_embeddings` dans le JSON `*_audio.json` consommé côté AE. **Implémenté (2026-01-30)** : activation via `AUDIO_INCLUDE_SPEAKER_EMBEDDINGS=1`, extraction Pyannote, préservation par STEP6 reducer.
- **Support multi-faces / layout** : le script AE `Analyse-Écart-X...jsx` sélectionne actuellement une cible unique (face/person) avec tie-breakers (présence, bbox, audio confirm). Un mode multi-cibles nécessiterait un contrat explicite (liste de cibles, split screen, règles de composition) et n’est pas livré dans cette passe.

---

## 9. Implémentation (2026-02-01) — Points Priorité Basse ✅

### Changements livrés
- `workflow_scripts/step6/json_reducer.py`
  - Ajout `tracking_analytics` (léger) dans `*_tracking.json` : histogramme de confidence + stats par objet (`avg_confidence`, `presence_ratio`, `avg_bbox_surface`, etc.).
  - Ajout `expression_summary` (léger) dérivé de `blendshapes` (si présents) pour éviter tout export lourd côté AE.
  - Variables d'environnement :
    - `STEP6_INCLUDE_TRACKING_ANALYTICS` (défaut: activé)
    - `STEP6_INCLUDE_EXPRESSION_SUMMARY` (défaut: désactivé)
    - `STEP6_EXPRESSION_KEYS` (défaut: `jawOpen`)
- `scripts/after_effects/Analyse-Écart-X-depuis-JSON-et-Label-Vidéo36_good.jsx`
  - Pondération des décisions par `confidence` (moyenne par objet sur la durée du calque) via `ENABLE_CONFIDENCE_WEIGHTING` + `CONFIDENCE_WEIGHT`.
  - Lecture (si parsing JSON complet possible) de `tracking_analytics` + `expression_summary`, et log des métriques utiles pour diagnostiquer la qualité du recentrage.
  - Fallback streaming STEP5 conservé (aucune dépendance à ces champs si le JSON complet n'est pas parsable).
- `tests/unit/test_step6_json_reducer.py`
  - Tests ajoutés pour `tracking_analytics` et `expression_summary`.

### Validation
- `pytest -q tests/unit/test_step6_json_reducer.py`

*Document généré le 30 janvier 2026 - Analyse des scripts After Effects dans le contexte du pipeline MediaPipe v4.x*
