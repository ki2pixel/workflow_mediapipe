# Points Chauds de Complexité - Workflow MediaPipe v4.2

## Analyse Radon (2026-01-30)

### Vue d'ensemble des Métriques
- **Total lignes de code** : 109,330 (Python: 15,211, JavaScript: 5,641, CSS: 3,594)
- **Complexité moyenne** : D (22.68)
- **Blocs analysés** : 88 (classes, fonctions, méthodes)

---

## Services Critiques (Score F/E)

### CSVService - Score F
**Méthodes critiques** :
- `_check_csv_for_downloads` (F) - Parsing complexe d'URLs avec gestion des encodages multiples
- `_normalize_url` (F) - Normalisation avancée des URLs (double encodage, entités HTML)

**Documentation** : ✅ `features/CSV_SERVICE.md` (complet)
- Couvre la logique de normalisation, gestion des doublons, stratégie webhook
- Explique les patterns d'encodage et fallbacks

### VisualizationService - Score D
**Méthodes critiques** :
- `_get_video_metadata` (D) - Chargement métadonnées vidéo via FFmpeg
- `_load_tracking_data` (D) - Parsing JSON volumineux avec optimisations
- `_load_audio_data` (C) - Traitement données audio STEP4
- `get_project_timeline` (C) - Agrégation multi-sources

**Documentation** : 🔄 `features/VISUALIZATION_SERVICE.md` (à créer)

### ReportService - Score F
**Méthodes critiques** :
- `generate_monthly_archive_report` (F) - Génération rapports HTML complexes
- `analyze_monthly_report_html` (E) - Parsing HTML avec extraction données

**Documentation** : ✅ Référencé dans `ARCHITECTURE_COMPLETE_FR.md`

---

## Workflow Scripts Critiques

### STEP5 Tracking - Score F/E
**Scripts critiques** :
- `process_video_worker.py` (F) - Multiprocessing complexe avec GPU/CPU
- `run_tracking_manager.py` (F) - Orchestration workers et profiling
- `process_video_worker_multiprocessing.py` (F) - Gestion chunks parallèles

**Face Engines - Score E** :
- `InsightFaceEngine.detect` (E) - Détection faciale GPU optimisée
- `OpenSeeFaceEngine.detect` (D) - Pipeline OpenSeeFace complet
- `EosFaceEngine.detect` (E) - Fit 3DMM complexe
- `OpenCVYuNetPyFeatEngine.detect` (D) - Hybride YuNet + py-feat

**Documentation** : ✅ `pipeline/STEP5_SUIVI_VIDEO.md` (complet)
- Couvre tous les moteurs, configuration GPU/CPU, multiprocessing
- Explique les optimisations et patterns de performance

### Autres Scripts Notables
- `STEP4/run_audio_analysis.py` (F) - Pipeline audio Lemonfox/Pyannote
- `STEP3/run_transnet.py` (E) - Détection scènes TransNetV2
- `STEP6/json_reducer.py` (D) - Réduction JSON optimisée

**Documentation** : ✅ `pipeline/STEP*_*.md` (complets)

---

## Recommandations par Priorité

### 🔴 Priorité Immédiate
1. **VisualizationService** : Créer documentation pour méthodes D
2. **Monitoring performance** : Ajouter logs temps d'exécution dans méthodes F
3. **Tests ciblés** : Couverture renforcée pour points chauds F/E

### 🟡 Priorité Moyenne
1. **Refactoring méthodique** : Analyser opportunités de réduction complexité F/E
2. **Documentation patterns** : Standardiser explication des algorithmes complexes
3. **Profiling continu** : Intégrer monitoring complexité dans CI/CD

### 🟢 Priorité Basse
1. **Architecture alternatives** : Explorer simplifications design pour services F
2. **Extraction utilitaires** : Isoler logique complexe réutilisable
3. **Formation équipe** : Sessions sur patterns de code complexes

---

## Traçabilité Code→Documentation

| Composant | Score Complexité | Documentation | Statut |
|-----------|------------------|----------------|---------|
| CSVService | F | `features/CSV_SERVICE.md` | ✅ Complet |
| STEP5 Tracking | F/E | `pipeline/STEP5_SUIVI_VIDEO.md` | ✅ Complet |
| VisualizationService | D | `features/VISUALIZATION_SERVICE.md` | 🔄 À créer |
| ReportService | F | `ARCHITECTURE_COMPLETE_FR.md` | ✅ Référencé |
| STEP4 Audio | F | `pipeline/STEP4_ANALYSE_AUDIO.md` | ✅ Complet |
| STEP3 Scenes | E | `pipeline/STEP3_DETECTION_SCENES.md` | ✅ Complet |

---

## Conclusion

L'audit révèle une **excellente traçabilité** entre code complexe et documentation. Les services critiques (Score F/E) sont majoritairement documentés, démontrant une maturité architecturale remarquable.

**Actions immédiates** :
1. Documenter VisualizationService (seul service D non documenté)
2. Mettre à jour métriques dans `COMPLEXITY_ANALYSIS.md`
3. Maintenir cette traçabilité pour futures évolutions

La documentation existante constitue une **base solide** pour la maintenance et l'évolution du système.
