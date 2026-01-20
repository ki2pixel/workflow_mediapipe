# Portail de Documentation Workflow MediaPipe v4.1

## Vue d'ensemble

Ce portail de documentation HTML fournit une interface complète et interactive pour explorer la documentation du système de workflow MediaPipe. Il offre une expérience de navigation fluide avec des fonctionnalités avancées pour faciliter la consultation et la recherche d'informations.

## 🏗️ Structure Organisée (Nouvelle v4.1)

La documentation a été réorganisée thématiquement pour une navigation intuitive :

### 📖 Core Documentation (Essentielle)
- **[ARCHITECTURE_COMPLETE_FR.md](core/ARCHITECTURE_COMPLETE_FR.md)** — Architecture complète du système
- **[GUIDE_DEMARRAGE_RAPIDE.md](core/GUIDE_DEMARRAGE_RAPIDE.md)** — Guide de démarrage rapide
- **[REFERENCE_RAPIDE_DEVELOPPEURS.md](core/REFERENCE_RAPIDE_DEVELOPPEURS.md)** — Référence développeurs

### 🔄 Pipeline Workflow (Étapes 1-7)
- **[STEP1_EXTRACTION.md](pipeline/STEP1_EXTRACTION.md)** — Extraction d'archives
- **[STEP2_CONVERSION.md](pipeline/STEP2_CONVERSION.md)** — Conversion vidéo
- **[STEP3_DETECTION_SCENES.md](pipeline/STEP3_DETECTION_SCENES.md)** — Détection de scènes
- **[STEP4_ANALYSE_AUDIO.md](pipeline/STEP4_ANALYSE_AUDIO.md)** — Analyse audio
- **[STEP5_SUIVI_VIDEO.md](pipeline/STEP5_SUIVI_VIDEO.md)** — Suivi vidéo
- **[STEP6_REDUCTION_JSON.md](pipeline/STEP6_REDUCTION_JSON.md)** — Réduction JSON
- **[STEP7_FINALISATION.md](pipeline/STEP7_FINALISATION.md)** — Finalisation

### 🛠️ Technical Documentation
- **[API_INSTRUMENTATION.md](technical/API_INSTRUMENTATION.md)** — Instrumentation API
- **[WEBHOOK_INTEGRATION.md](technical/WEBHOOK_INTEGRATION.md)** — Integration Webhook
- **[CSV_DOWNLOADS_MANAGEMENT.md](technical/CSV_DOWNLOADS_MANAGEMENT.md)** — Gestion téléchargements
- **[SYSTEM_MONITORING_ENHANCEMENTS.md](technical/SYSTEM_MONITORING_ENHANCEMENTS.md)** — Monitoring système
- **[TESTING_STRATEGY.md](technical/TESTING_STRATEGY.md)** — Stratégie de tests
- **[SECURITY.md](technical/SECURITY.md)** — Sécurité

### 🚀 Features & Functionality
- **[SMART_UPLOAD_FEATURE.md](features/SMART_UPLOAD_FEATURE.md)** — Upload intelligent
- **[DIAGNOSTICS_FEATURE.md](features/DIAGNOSTICS_FEATURE.md)** — Diagnostics système
- **[RESULTS_ARCHIVER_SERVICE.md](features/RESULTS_ARCHIVER_SERVICE.md)** — Service d'archivage

### 🔧 Optimization & Performance
- **[Alternatives GPU pour Tracking Facial Blendshapes.md](optimization/Alternatives GPU pour Tracking Facial Blendshapes.md)** — Optimisations GPU

### 📋 Practical Guides
- **[FRONTEND_GUIDE_RACCourcis_A11Y_LOADERS.md](guides/FRONTEND_GUIDE_RACCourcis_A11Y_LOADERS.md)** — Guide frontend A11y
- **[LIGHTBOX_DEBUGGING_GUIDE.md](guides/LIGHTBOX_DEBUGGING_GUIDE.md)** — Debug lightbox
- **[CLICK_EVENT_FIXES_GUIDE.md](guides/CLICK_EVENT_FIXES_GUIDE.md)** — Fixes clics

### 🗂️ Administration & Maintenance
- **[UPDATE_DOCUMENTATION_SUMMARY.md](admin/UPDATE_DOCUMENTATION_SUMMARY.md)** — Historique mises à jour
- **[MIGRATION_STATUS.md](admin/MIGRATION_STATUS.md)** — Statut migrations
- **[AUDIT_TECHNIQUE_2026_01.md](admin/AUDIT_TECHNIQUE_2026_01.md)** — Audit technique

### 🏛️ Web Portal
- **[Portal HTML](portal/index.html)** — Portail web interactif
- **[Portal Assets](portal/assets/)** — Styles et JavaScript

### ⚙️ Configuration & Deployment
- **[Apache Config](config/.htaccess)** — Configuration Apache
- **[Deployment Scripts](config/deploy.sh)** — Scripts de déploiement

### 📦 Archives (Historique)
- **[Deprecated](archives/deprecated/)** — Fonctionnalités obsolètes
- **[Legacy](legacy/)** — Documentation historique

## Par où commencer ?

- Pour une vision globale de l'architecture, commencez par → **[ARCHITECTURE_COMPLETE_FR.md](core/ARCHITECTURE_COMPLETE_FR.md)**
- Pour comprendre le widget d'upload intelligent → **[SMART_UPLOAD_FEATURE.md](features/SMART_UPLOAD_FEATURE.md)**
- Pour les métriques système et l'instrumentation API → **[SYSTEM_MONITORING_ENHANCEMENTS.md](technical/SYSTEM_MONITORING_ENHANCEMENTS.md)**
- Pour mettre en place/étendre les tests → **[TESTING_STRATEGY.md](technical/TESTING_STRATEGY.md)**
- Pour les développeurs (raccourcis et patterns obligatoires) → **[REFERENCE_RAPIDE_DEVELOPPEURS.md](core/REFERENCE_RAPIDE_DEVELOPPEURS.md)**

## Fonctionnalités

### 🎯 Navigation Intuitive
- **Menu latéral organisé** : Navigation par catégories (Vue d'ensemble, Guides, Étapes du Pipeline)
- **Fil d'Ariane** : Indication claire de la position actuelle dans la documentation
- **Navigation responsive** : Adaptation automatique aux écrans mobiles et desktop

### 🔍 Recherche Avancée
- **Recherche en temps réel** : Indexation complète de tous les documents
- **Résultats contextuels** : Extraits pertinents avec mise en évidence des termes recherchés
- **Recherche intelligente** : Support des termes multiples avec intersection des résultats

### 📋 Table des Matières Dynamique
- **Génération automatique** : TOC créée à partir des titres du document
- **Navigation par ancres** : Liens directs vers les sections
- **Indicateur de progression** : Surlignage de la section actuellement visible

### 🎨 Interface Moderne
- **Thème sombre/clair** : Basculement facile entre les modes d'affichage
- **Design responsive** : Optimisé pour tous les types d'écrans
- **Typographie soignée** : Lisibilité optimisée pour la documentation technique

### 💻 Fonctionnalités Développeur
- **Coloration syntaxique** : Mise en évidence du code avec Prism.js
- **Copie de code** : Boutons de copie sur tous les blocs de code
- **Diagrammes Mermaid** : Rendu interactif des diagrammes d'architecture
- **Liens d'ancrage** : Liens directs vers les sections avec symbole #

### 📊 Visualisations
- **Diagrammes d'architecture** : Représentation visuelle du système complet
- **Flux d'exécution** : Séquences détaillées des workflows
- **Rendu adaptatif** : Diagrammes qui s'adaptent au thème choisi

## Structure des Fichiers

```
docs/workflow/
├── index.html                          # Portail principal
├── assets/
│   ├── styles.css                      # Styles CSS avancés
│   └── app.js                          # Fonctionnalités JavaScript
├── README.md                           # Ce fichier
├── ARCHITECTURE_COMPLETE_FR.md         # Documentation architecture
├── GUIDE_DEMARRAGE_RAPIDE.md          # Guide de démarrage
├── REFERENCE_RAPIDE_DEVELOPPEURS.md   # Référence développeurs
├── WEBHOOK_INTEGRATION.md             # Documentation technique Webhook
├── STEP1_EXTRACTION.md                # Documentation Étape 1
├── STEP2_CONVERSION.md                # Documentation Étape 2
├── STEP3_DETECTION_SCENES.md          # Documentation Étape 3
├── STEP4_ANALYSE_AUDIO.md             # Documentation Étape 4
├── STEP4_LEMONFOX_IMPLEMENTATION_STATUS.md  # STEP4 Lemonfox (statut)
├── STEP4_LEMONFOX_AUDIO_PLAN.md            # STEP4 Lemonfox (plan)
├── STEP5_SUIVI_VIDEO.md               # Documentation Étape 5
├── STEP6_REDUCTION_JSON.md            # Documentation Étape 6
└── STEP7_FINALISATION.md              # Documentation Étape 7
```

## Utilisation

### Démarrage Rapide

1. **Ouvrir le portail** : Ouvrez `docs/workflow/index.html` dans votre navigateur web
2. **Navigation** : Utilisez le menu latéral pour accéder aux différentes sections
3. **Recherche** : Tapez dans la barre de recherche pour trouver des informations spécifiques
4. **Thème** : Cliquez sur l'icône 🌙/☀️ pour basculer entre les thèmes

### Navigation

#### Menu Principal
- **Vue d'ensemble** : Page d'accueil et architecture complète
- **Guides** : Documentation pour démarrer et référence développeurs
- **Intégration Webhook** : Configuration et utilisation du monitoring Webhook (source unique de données)
- **Étapes du Pipeline** : Documentation détaillée de chaque étape (1-7)

#### Raccourcis Clavier
- **Ctrl/Cmd + F** : Recherche dans le navigateur (recherche locale)
- **Échap** : Fermer les résultats de recherche
- **Tab** : Navigation au clavier dans l'interface

### Fonctionnalités Avancées

#### Recherche Intelligente
- Tapez au moins 3 caractères pour déclencher la recherche
- Utilisez plusieurs mots pour affiner les résultats
- Cliquez sur un résultat pour naviguer directement vers le document

#### Table des Matières
- Apparaît automatiquement pour les documents longs
- Clic sur une entrée pour naviguer vers la section
- Indicateur visuel de la section actuelle

#### Copie de Code
- Survolez un bloc de code pour voir le bouton "Copier"
- Clic pour copier le code dans le presse-papiers
- Confirmation visuelle "Copié !" pendant 2 secondes

#### Liens d'Ancrage
- Survolez un titre pour voir le symbole #
- Clic pour obtenir un lien direct vers cette section
- Partage facile de sections spécifiques

## Technologies Utilisées

### Bibliothèques Externes
- **[Marked.js](https://marked.js.org/)** v9.1.6 : Rendu Markdown vers HTML
- **[Mermaid](https://mermaid.js.org/)** v10.6.1 : Diagrammes et graphiques
- **[Prism.js](https://prismjs.com/)** v1.29.0 : Coloration syntaxique

### Fonctionnalités Natives
- **CSS Grid & Flexbox** : Layout responsive moderne
- **CSS Custom Properties** : Système de thèmes
- **Intersection Observer API** : Détection de scroll pour TOC
- **Clipboard API** : Copie de code
- **Local Storage** : Persistance des préférences

## Compatibilité

### Navigateurs Supportés
- **Chrome/Chromium** 88+
- **Firefox** 85+
- **Safari** 14+
- **Edge** 88+

### Fonctionnalités Dégradées
- **Anciens navigateurs** : Fonctionnalités de base disponibles
- **JavaScript désactivé** : Affichage statique du contenu
- **Hors ligne** : Fonctionnement complet une fois chargé

## Personnalisation

### Modification des Thèmes
Éditez les variables CSS dans `assets/styles.css` :

```css
:root {
    --primary-color: #2563eb;      /* Couleur principale */
    --accent-color: #0ea5e9;       /* Couleur d'accent */
    --background-color: #ffffff;   /* Arrière-plan */
    /* ... autres variables */
}
```

### Ajout de Documents
1. Placez le fichier `.md` dans le répertoire `docs/workflow/`
2. Ajoutez une entrée dans le menu de navigation (`index.html`)
3. Mettez à jour la liste des documents dans `assets/app.js`

### Modification des Styles
- **Styles globaux** : `index.html` (section `<style>`)
- **Styles avancés** : `assets/styles.css`
- **Responsive** : Media queries dans les fichiers CSS

## Maintenance

### Mise à Jour des Documents
- Modifiez directement les fichiers `.md`
- Le portail se met à jour automatiquement au rechargement
- Aucune recompilation nécessaire

### Mise à Jour des Bibliothèques
Remplacez les URLs CDN dans `index.html` :
```html
<script src="https://cdn.jsdelivr.net/npm/marked@VERSION/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@VERSION/dist/mermaid.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@VERSION/components/prism-core.min.js"></script>
```

### Optimisation des Performances
- **Mise en cache** : Les documents sont indexés au chargement
- **Lazy loading** : Chargement à la demande des documents
- **Compression** : Activez la compression gzip sur le serveur web

## Déploiement

### Serveur Web Local
```bash
# Python 3
python -m http.server 8000 --directory docs/workflow

# Node.js (avec serve)
npx serve docs/workflow

# Accès : http://localhost:8000
```

### Serveur Web de Production
- Copiez le répertoire `docs/workflow/` sur votre serveur
- Configurez le serveur web pour servir les fichiers statiques
- Activez la compression et la mise en cache pour les performances

### GitHub Pages
1. Poussez le répertoire vers GitHub
2. Activez GitHub Pages dans les paramètres du repository
3. Définissez le dossier source sur `docs/workflow/`

## Support et Contribution

### Signalement de Problèmes
- Vérifiez la console du navigateur pour les erreurs JavaScript
- Testez avec JavaScript activé et connexion internet
- Vérifiez la compatibilité du navigateur

### Amélioration de la Documentation
- Modifiez les fichiers `.md` pour le contenu
- Modifiez `assets/styles.css` pour l'apparence
- Modifiez `assets/app.js` pour les fonctionnalités

### Bonnes Pratiques
- **Markdown** : Utilisez une syntaxe Markdown standard
- **Images** : Placez les images dans un dossier `assets/images/`
- **Liens** : Utilisez des liens relatifs pour la portabilité
- **Accessibilité** : Respectez les standards WCAG pour l'accessibilité
