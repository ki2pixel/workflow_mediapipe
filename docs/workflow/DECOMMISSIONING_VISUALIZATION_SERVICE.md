# Plan de Décommissionnement - VisualizationService

**TL;DR** : Suppression complète du service VisualizationService et de ses dépendances frontend/backend, car l'UI principale ne l'utilise plus.

---

## 1. Contexte et Justification

### État Actuel
- **Backend** : `VisualizationService` (services/visualization_service.py) toujours présent avec API `/api/visualization/projects`
- **Frontend principal** : `templates/index_new.html` ne contient plus aucun markup lié aux rapports (pas de `report-overlay`, ni boutons)
- **Scripts JS** : `static/reportViewer.js` importé conditionnellement dans `main.js` mais inopérant faute de markup
- **Documentation** : `docs/workflow/services/visualization-service.md` encore présent mais obsolète

### Raison de la Suppression
L'interface utilisateur a été retirée (legacy) mais le service backend persiste, créant une dette technique inutile. Le service n'est plus consommé par l'UI principale.

---

## 2. Impact Analysis

### Backend Impact
- **Routes à supprimer** : `/api/visualization/projects` (routes/api_routes.py:562-591)
- **Service à supprimer** : `services/visualization_service.py` (782 lignes)
- **Tests impactés** : Aucun test trouvé utilisant directement ce service

### Frontend Impact
- **Scripts à supprimer** : `static/reportViewer.js` (682 lignes)
- **Imports à nettoyer** : Import dans `static/main.js` (lignes 22-23, 389-391)
- **CSS à supprimer** : `static/css/features/reports.css` (si présent)

### Documentation Impact
- **Documentation à archiver** : `docs/workflow/services/visualization-service.md`
- **Références à nettoyer** : Recherche globale dans les docs

---

## 3. Checklist de Suppression

### Phase 1 : Backend
- [ ] Supprimer la route `/api/visualization/projects` dans `routes/api_routes.py`
- [ ] Supprimer le fichier `services/visualization_service.py`
- [ ] Vérifier qu'aucun autre service n'importe `VisualizationService`
- [ ] Tester que l'application démarre toujours (`python3 -m py_compile app_new.py`)

### Phase 2 : Frontend
- [ ] Supprimer `static/reportViewer.js`
- [ ] Retirer l'import et l'initialisation dans `static/main.js`
  - Ligne 22 : `import { reportViewer } from './reportViewer.js';`
  - Ligne 389-391 : Bloc conditionnel `if (document.getElementById('report-overlay'))`
- [ ] Supprimer `static/css/features/reports.css` (si existant)
- [ ] Vérifier que `npm run test:frontend` passe toujours

### Phase 3 : Documentation
- [ ] Archiver `docs/workflow/services/visualization-service.md` vers `docs/workflow/archives/`
- [ ] Rechercher et supprimer toutes les références à "VisualizationService" dans la documentation
- [ ] Mettre à jour `docs/workflow/README.md` si nécessaire

### Phase 4 : Validation
- [ ] Démarrer l'application et vérifier l'absence d'erreurs 404 sur `/api/visualization/projects`
- [ ] Vérifier que la console JavaScript ne contient pas d'erreurs liées à `reportViewer`
- [ ] Confirmer que toutes les fonctionnalités principales (workflow, logs, téléchargements) fonctionnent

---

## 4. Commandes de Suppression (à exécuter dans l'ordre)

### Backend
```bash
# Suppression de la route API
sed -i '/@api_bp.route.*visualization\.projects/,/return jsonify({"error": "Unable to list visualization projects"}), 500/d' routes/api_routes.py

# Suppression du service
rm services/visualization_service.py

# Vérification de compilation
python3 -m py_compile app_new.py
```

### Frontend
```bash
# Suppression du script JS
rm static/reportViewer.js

# Nettoyage des imports dans main.js
sed -i '/import.*reportViewer/d' static/main.js
sed -i '/if (document.getElementById.*report-overlay.)/,/}/d' static/main.js

# Suppression CSS si présent
rm -f static/css/features/reports.css

# Tests frontend
npm run test:frontend
```

### Documentation
```bash
# Archivage de la documentation
mkdir -p docs/workflow/archives
mv docs/workflow/services/visualization-service.md docs/workflow/archives/

# Recherche des références restantes
grep -r "VisualizationService" docs/workflow/ || echo "Aucune référence trouvée"
```

---

## 5. Risques et Mitigations

### Risques Identifiés
1. **Régression cachée** : Un autre composant pourrait utiliser l'API sans être évident
2. **Documentation obsolète** : Références pourraient exister dans des documents non scannés
3. **Tests manquants** : Absence de tests pourrait masquer des dépendances

### Mitigations
1. **Recherche exhaustive** : `grep -r "visualization/" . --exclude-dir=.git` avant suppression
2. **Validation étendue** : Tester tous les workflows après suppression
3. **Rollback准备** : Garder une branche de sauvegarde avant les suppressions

---

## 6. Timeline Recommandée

| Phase | Durée | Qui | Dépendances |
|-------|-------|-----|-------------|
| Phase 1 (Backend) | 30 min | Dev | None |
| Phase 2 (Frontend) | 30 min | Dev | Phase 1 |
| Phase 3 (Documentation) | 15 min | Tech Writer | Phase 2 |
| Phase 4 (Validation) | 45 min | QA | Phase 3 |

**Total estimé** : 2 heures

---

## 7. Post-Suppression

### Actions de Suivi
- [ ] Mettre à jour la Memory Bank avec la décision de décommissionnement
- [ ] Ajouter une note dans `decisionLog.md` pour traçabilité
- [ ] Vérifier que les monitors/health checks ne tentent plus de contacter l'API supprimée

### Bénéfices Attendus
- **Réduction de la dette technique** : -782 lignes de code backend
- **Simplification** : Moins de routes à maintenir et documenter
- **Performance** : Réduction de la surface d'attaque et du temps de chargement

---

## 8. Golden Rule

**Archive avant de supprimer ; sinon tu perds la traçabilité des décisions architecturales et la capacité à revenir en arrière si besoin.**

---

*Créé le 2026-02-08*  
*Statut : Prêt pour exécution*
