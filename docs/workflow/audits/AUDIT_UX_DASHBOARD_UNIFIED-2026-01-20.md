# Audit UX Unifié — Dashboard Workflow v4.2

**Date** : 2026-01-20  
**Version** : v4.2  
**Auteur** : Expert UI/UX & Lead Frontend  
**Scope** : Pipeline des 7 étapes - Dashboard `index_new.html`  
**Sources** : Unification de AUDIT_UX_DASHBOARD_CONCEPT-1.md et AUDIT_UX_DASHBOARD_CONCEPT-2.md

---

## 1. Analyse Critique de l'Existant

### 1.1 Problèmes Fondamentaux Identifiés

**Structure et Perception**
- ❌ **Flux visuel brisé** : Les étapes apparaissent comme des cartes indépendantes, pas comme un pipeline connecté
- ❌ **Signal d'état localisé** : La couleur d'état est cantonnée aux badges et un fin filet gauche, peu de contraste à distance
- ❌ **Répétition visuelle** : Typographies, espacements et boutons identiques créent un "mur" de contrôles
- ❌ **Spatialisation limitée** : La colonne unique ne suggère pas le cheminement complet (préparation → exécution → consolidation)

**Ergonomie et Interaction**
- ❌ **Charge cognitive** : L'utilisateur doit mentalement connecter les étapes
- ❌ **Fatigue visuelle** : Répétition visuelle des 7 cartes identiques
- ❌ **Micro-interactions minimales** : Hover basique, transitions peu fluides, pas de feedback contextuel
- ❌ **Manque de contexte** : Pas de vue d'ensemble du pipeline

**Points Forts Conservés**
- ✅ **Fonctionnalité** : Chaque étape est clairement identifiable avec ses contrôles
- ✅ **Accessibilité** : Structure sémantique HTML5 avec ARIA approprié
- ✅ **États visuels** : Badges de statut distincts (idle, running, success, failed)
- ✅ **Compact mode** : Adaptation responsive bien pensée

---

## 2. Concepts de Visualisation Pipeline

### 2.1 Concept Principal : Timeline Connectée (Recommandé)

**Principe** : Transformer la liste en une ligne temporelle verticale continue avec des nœuds connectés par un tracé lumineux. Les états changent la couleur du tronçon amont/aval pour renforcer la lecture de progression.

**Visual Structure**
```
┌── Nœud 1 ── Connecteur ── Nœud 2 ── Connecteur ── Nœud 3 ──┐
│   ↓           ↓             ↓           ↓             ↓   │
│ [Details]   [Details]     [Details]   [Details]   [Details] │
└─────────────────────────────────────────────────────────────┘
```

**Avantages**
- 🎯 **Flux évident** : La progression naturelle est immédiatement visible
- 🎯 **Élégance premium** : Design moderne rappelant les interfaces DevOps/Media Production
- 🎯 **Scannabilité** : Vue d'ensemble instantanée du statut global
- 🎯 **Continuité** : Les steps en succès affichent une traînée dégradée jusqu'au nœud suivant

### 2.2 Concept Alternatif : Grid Cards Modulaire

**Principe** : Grid 2x4 avec progression visuelle par couches superposées, regroupant les étapes par phase.

**Groupement Logique**
- **Phase 1** : Préparation (STEP1-2)
- **Phase 2** : Analyse (STEP3-5)  
- **Phase 3** : Consolidation (STEP6-7)

**Avantages**
- 🎯 **Densité information** : Plus de détails visibles simultanément
- 🎯 **Stats secondaires** : Temps total phase, ressources
- 🎯 **Actions centralisées** : Zone dédiée pour les contrôles globaux

### 2.3 Concept Avancé : Pipeline Orbit

**Principe** : Représentation semi-circulaire où chaque étape est un module radial autour d'un noyau "Workflow".

**Cas d'usage** : Grands écrans ou murs d'ops, look "Mission Control"

**Contraintes**
- ⚠️ **Implémentation lourde** : Exigeante côté responsive
- ⚠️ **Lecture textuelle** : Moins directe que la timeline

---

## 3. Hiérarchie Visuelle des États

### 3.1 Système de Couches Visuelles

**Priorité 1 : Contour Dynamique**
```css
.step-pipeline[data-status="running"] {
    background: linear-gradient(135deg, 
        rgba(var(--status-running-rgb), 0.1) 0%, 
        rgba(var(--status-running-rgb), 0.05) 100%);
    border: 2px solid var(--status-running);
    box-shadow: 0 10px 30px rgba(94,114,228,0.25);
}
```

**Priorité 2 : Fond Adaptatif**
```css
.step-pipeline[data-status="success"] {
    background: rgba(var(--status-success-rgb), 0.08);
    border-color: var(--status-success);
    transform: scale(1.02);
}
```

**Priorité 3 : Timeline/Connecteurs Colorés**
```css
.timeline-spine {
    background: linear-gradient(180deg, transparent, var(--accent-primary));
}

.timeline-step[data-status="success"] .timeline-node {
    border-color: var(--status-success);
    box-shadow: 0 0 16px color-mix(in oklab, var(--status-success) 45%, transparent);
}
```

**Priorité 4 : Badge de Confirmation**
- Information textuelle secondaire
- Confirmation visuelle de l'état

### 3.2 Variables CSS Core

```css
:root {
    --pipeline-node-size: 80px;
    --pipeline-connector-width: 3px;
    --pipeline-gap: 2rem;
    --pipeline-color-idle: var(--gray-400);
    --pipeline-color-running: var(--blue-500);
    --pipeline-color-success: var(--green-500);
    --pipeline-color-error: var(--red-500);
}
```

---

## 4. Micro-interactions & Transitions

### 4.1 Respect `prefers-reduced-motion`

```css
@media (prefers-reduced-motion: reduce) {
    .step-pipeline {
        transition: none !important;
        animation: none !important;
    }
}
```

### 4.2 Transitions Premium (Motion ON)

**Hover States**
```css
.step-pipeline {
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.step-pipeline:hover {
    transform: translateY(-8px) scale(1.02);
    box-shadow: 
        0 20px 40px rgba(0,0,0,0.15),
        0 0 0 1px rgba(var(--accent-primary-rgb), 0.2);
}
```

**State Changes**
```css
.step-pipeline[data-status="running"] {
    animation: gentle-pulse 3s ease-in-out infinite;
}

@keyframes gentle-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.95; }
}
```

**Connection Animations**
```css
.pipeline-connector {
    stroke-dasharray: 5, 5;
    stroke-dashoffset: 0;
    animation: flow 2s linear infinite;
}

@keyframes flow {
    to { stroke-dashoffset: -10; }
}
```

**Activation Step → Timeline**
- Lors d'un run, le nœud actif augmente légèrement de taille
- Le segment précédent diffuse un dégradé vers l'avant
- En mode `prefers-reduced-motion`, conserver uniquement la variation de couleur

---

## 5. Ergonomie des Contrôles

### 5.1 Zonage Intelligent

**Zone 1 : Timeline (Vue d'ensemble)**
- Nœuds d'étape avec statut visuel
- Connecteurs animés de progression
- Click pour expand/collapse détails

**Zone 2 : Panneau Latéral (Actions contextuelles)**
- Contrôles de l'étape sélectionnée
- Logs en temps réel
- Actions rapides (restart, skip)

**Zone 3 : Barre Supérieure (Actions globales)**
- Workflow complet
- Séquences personnalisées
- Paramètres système

### 5.2 Placement Optimisé des Contrôles

**Boutons Primaire/Secondaire**
```html
<div class="timeline-controls">
    <button class="run-button" data-step="{{ step_key }}">Lancer</button>
    <button class="cancel-button" data-step="{{ step_key }}" disabled>Annuler</button>
    <button class="log-button" data-step="{{ step_key }}">Logs</button>
</div>
```

**Regroupement Actions Logs**
- Rapprocher les boutons "Logs spécifiques" de la timeline
- Placement dans un pill latéral aligné sur le spine
- Casser l'impression d'annexe

**Sélection Séquence**
- Convertir les checkboxes en "chips" ancrées à la timeline
- Indicateur numéroté apparaissant directement sur le nœud
- Moins de mouvement oculaire entre titre et contrôle

---

## 6. Implémentation Technique : Timeline Connectée

### 6.1 Structure HTML Sémantique

```html
<section class="workflow-pipeline" role="region" aria-label="Pipeline de traitement">
    <!-- En-tête du pipeline -->
    <header class="pipeline-header">
        <h2>Workflow MediaPipe - Pipeline de Traitement</h2>
        <div class="pipeline-overview">
            <span class="overview-progress">3/7 étapes complétées</span>
            <span class="overview-time">Temps estimé : ~15min</span>
        </div>
    </header>
    
    <!-- Timeline principale -->
    <div class="pipeline-timeline" role="list">
        <div class="timeline-node" data-step="1" role="listitem">
            <div class="node-visual">
                <div class="node-icon">📦</div>
                <div class="node-connector"></div>
            </div>
            <div class="node-content">
                <h3 class="node-title">1. Extraction</h3>
                <p class="node-description">Extraction sécurisée des archives</p>
                <div class="node-status">
                    <span class="status-badge status-success">✓ Terminé</span>
                    <span class="node-duration">2:34</span>
                </div>
            </div>
            <div class="node-actions">
                <button class="btn-icon" aria-label="Voir les logs">📋</button>
                <button class="btn-icon" aria-label="Relancer">🔄</button>
            </div>
        </div>
        
        <!-- Pattern répété pour les 7 étapes -->
    </div>
    
    <!-- Panneau de détails -->
    <aside class="pipeline-details" role="complementary">
        <div class="details-content">
            <!-- Dynamiquement rempli selon l'étape sélectionnée -->
        </div>
    </aside>
</section>
```

### 6.2 CSS Core Implementation

```css
.pipeline-timeline {
    position: relative;
    margin: 0 auto;
    padding-left: 2.5rem;
    border-left: 2px solid color-mix(in oklab, var(--border-color) 60%, transparent);
}

.timeline-step {
    position: relative;
    padding: 1.5rem 1.5rem 1.25rem;
    margin-bottom: 1.5rem;
    border-radius: 20px;
    background: color-mix(in oklab, var(--bg-card) 92%, transparent);
    transition: background 0.3s ease, box-shadow 0.3s ease;
}

.timeline-step[data-status="running"] {
    background: color-mix(in oklab, var(--status-running) 12%, var(--bg-card));
    box-shadow: 0 10px 30px rgba(94,114,228,0.25);
}

.timeline-spine {
    position: absolute;
    left: -2.5rem;
    top: 0;
    bottom: -1.5rem;
    width: 2px;
    background: linear-gradient(180deg, transparent, var(--accent-primary));
}

.timeline-node {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--bg-dark);
    border: 3px solid var(--status-idle);
    box-shadow: 0 0 12px rgba(0,0,0,0.25);
}

.timeline-step[data-status="success"] .timeline-node {
    border-color: var(--status-success);
    box-shadow: 0 0 16px color-mix(in oklab, var(--status-success) 45%, transparent);
}

.timeline-head { 
    display: flex; 
    align-items: center; 
    gap: 1rem; 
}

.timeline-body { 
    margin-top: 1rem; 
    display: grid; 
    gap: 0.75rem; 
}

.timeline-controls { 
    display: flex; 
    gap: 0.5rem; 
    flex-wrap: wrap; 
}

@media (prefers-reduced-motion: reduce) {
    .timeline-step, .timeline-node { 
        transition: none; 
    }
}
```

### 6.3 JavaScript Pattern (AppState Compatible)

```javascript
class PipelineTimeline {
    constructor() {
        this.selectedStep = null;
        this.setupEventListeners();
        this.bindToAppState();
    }
    
    bindToAppState() {
        // Écouter les changements d'état via AppState
        AppState.subscribe('workflowSteps', this.updateTimeline.bind(this));
    }
    
    updateTimeline(stepsState) {
        Object.entries(stepsState).forEach(([stepKey, state]) => {
            const node = document.querySelector(`[data-step="${stepKey}"]`);
            this.updateNodeVisual(node, state);
        });
    }
    
    updateNodeVisual(node, state) {
        // Mise à jour DOMBatcher-compatible
        DOMBatcher.scheduleUpdate(() => {
            node.setAttribute('data-status', state.status);
            const badge = node.querySelector('.status-badge');
            badge.textContent = this.getStatusText(state.status);
            badge.className = `status-badge status-${state.status}`;
        });
    }
}
```

---

## 7. Feuille de Route d'Implémentation

### Phase 1 : Structure Foundation (1-2 jours)
- ✅ Création du HTML sémantique
- ✅ Variables CSS et base styling
- ✅ Intégration AppState existante

### Phase 2 : Visual Polish (2-3 jours)
- ✅ Animations et transitions
- ✅ États hover et focus
- ✅ Responsive design

### Phase 3 : Advanced Features (1-2 jours)
- ✅ Panneau détails contextuel
- ✅ Accessibilité complète
- ✅ Performance optimization

---

## 8. Conclusion et Recommandations

La **Timeline Connectée** offre le meilleur équilibre entre :
- **Élégance visuelle** : Design moderne et premium
- **Ergonomie** : Flux naturel et intuitif  
- **Maintenabilité** : Compatible avec l'architecture existante
- **Accessibilité** : Respect des standards WCAG

### Forces de l'Unification

**De l'AUDIT_1**
- Structure détaillée et concepts variés
- Feuille de route d'implémentation claire
- JavaScript pattern compatible AppState

**De l'AUDIT_2**
- Analyse critique percutante
- Snippets techniques concrets
- CSS avancé avec `color-mix()`

### Recommandation Finale

Ce redesign transformera l'interface utilitaire actuelle en une expérience utilisateur mémorable tout en préservant la robustesse technique du système Workflow MediaPipe v4.2.

**Next Steps** : Validation du concept → Implémentation progressive → Tests utilisateurs → Déploiement

---

**Compatibilité** : Cette solution est entièrement compatible avec l'architecture existante (pas de framework, pas de `innerHTML`, structure HTML sémantique) et respecte les patterns établis (AppState, DOMBatcher, sécurité XSS).
