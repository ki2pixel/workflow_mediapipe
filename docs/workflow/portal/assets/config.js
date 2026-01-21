// Configuration for the documentation portal

const PORTAL_CONFIG = {
    // Site information
    site: {
        title: "Documentation Workflow MediaPipe v4.1",
        description: "Système de traitement vidéo automatisé en 7 étapes avec architecture orientée services",
        version: "4.1",
        author: "Équipe Workflow MediaPipe"
    },

    // Navigation structure
    navigation: [
        {
            section: "Vue d'ensemble",
            items: [
                { id: "welcome", title: "Accueil", icon: "🏠" },
                { id: "ARCHITECTURE_COMPLETE_FR", title: "Architecture Complète", icon: "🏗️" }
            ]
        },
        {
            section: "Guides",
            items: [
                { id: "GUIDE_DEMARRAGE_RAPIDE", title: "Guide de Démarrage", icon: "🚀" },
                { id: "REFERENCE_RAPIDE_DEVELOPPEURS", title: "Référence Développeurs", icon: "👨‍💻" }
            ]
        },
        {
            section: "Étapes du Pipeline",
            items: [
                { id: "STEP1_EXTRACTION", title: "Étape 1: Extraction", icon: "📦" },
                { id: "STEP2_CONVERSION", title: "Étape 2: Conversion", icon: "🎬" },
                { id: "STEP3_DETECTION_SCENES", title: "Étape 3: Détection Scènes", icon: "🎯" },
                { id: "STEP4_ANALYSE_AUDIO", title: "Étape 4: Analyse Audio", icon: "🎵" },
                { id: "STEP5_SUIVI_VIDEO", title: "Étape 5: Suivi Vidéo", icon: "👁️" },
                { id: "STEP6_REDUCTION_JSON", title: "Étape 6: Réduction JSON", icon: "🧩" },
                { id: "STEP7_FINALISATION", title: "Étape 7: Finalisation", icon: "✅" }
            ]
        },
        {
            section: "Fonctionnalités",
            items: [
                { id: "DIAGNOSTICS_FEATURE", title: "Diagnostics Système", icon: "🩺" },
                { id: "RESULTS_ARCHIVER_SERVICE", title: "Archiver Résultats", icon: "🗂️" }
            ]
        },
        {
            section: "Documentation Technique",
            items: [
                { id: "WEBHOOK_INTEGRATION", title: "Integration Webhook", icon: "🔗" },
                { id: "SYSTEM_MONITORING_ENHANCEMENTS", title: "Monitoring Système", icon: "📊" },
                { id: "TESTING_STRATEGY", title: "Stratégie de Tests", icon: "🧪" },
                { id: "SECURITY", title: "Sécurité", icon: "🔒" },
                { id: "API_INSTRUMENTATION", title: "Instrumentation API", icon: "⚡" }
            ]
        }
    ],

    // Document titles mapping
    documentTitles: {
        'ARCHITECTURE_COMPLETE_FR': 'Architecture Complète',
        'GUIDE_DEMARRAGE_RAPIDE': 'Guide de Démarrage',
        'REFERENCE_RAPIDE_DEVELOPPEURS': 'Référence Développeurs',
        'STEP1_EXTRACTION': 'Étape 1: Extraction',
        'STEP2_CONVERSION': 'Étape 2: Conversion',
        'STEP3_DETECTION_SCENES': 'Étape 3: Détection Scènes',
        'STEP4_ANALYSE_AUDIO': 'Étape 4: Analyse Audio',
        'STEP5_SUIVI_VIDEO': 'Étape 5: Suivi Vidéo',
        'STEP6_REDUCTION_JSON': 'Étape 6: Réduction JSON',
        'STEP7_FINALISATION': 'Étape 7: Finalisation',
        'DIAGNOSTICS_FEATURE': 'Diagnostics Système',
        'RESULTS_ARCHIVER_SERVICE': 'Service d\'Archivage',
        'SYSTEM_MONITORING_ENHANCEMENTS': 'Monitoring Système',
        'WEBHOOK_INTEGRATION': 'Integration Webhook',
        'TESTING_STRATEGY': 'Stratégie de Tests',
        'SECURITY': 'Sécurité',
        'API_INSTRUMENTATION': 'Instrumentation API'
    },

    // Document paths mapping (NEW STRUCTURE)
    documentPaths: {
        'ARCHITECTURE_COMPLETE_FR': 'core/ARCHITECTURE_COMPLETE_FR.md',
        'GUIDE_DEMARRAGE_RAPIDE': 'core/GUIDE_DEMARRAGE_RAPIDE.md',
        'REFERENCE_RAPIDE_DEVELOPPEURS': 'core/REFERENCE_RAPIDE_DEVELOPPEURS.md',
        'STEP1_EXTRACTION': 'pipeline/STEP1_EXTRACTION.md',
        'STEP2_CONVERSION': 'pipeline/STEP2_CONVERSION.md',
        'STEP3_DETECTION_SCENES': 'pipeline/STEP3_DETECTION_SCENES.md',
        'STEP4_ANALYSE_AUDIO': 'pipeline/STEP4_ANALYSE_AUDIO.md',
        'STEP5_SUIVI_VIDEO': 'pipeline/STEP5_SUIVI_VIDEO.md',
        'STEP6_REDUCTION_JSON': 'pipeline/STEP6_REDUCTION_JSON.md',
        'STEP7_FINALISATION': 'pipeline/STEP7_FINALISATION.md',
        'DIAGNOSTICS_FEATURE': 'features/DIAGNOSTICS_FEATURE.md',
        'RESULTS_ARCHIVER_SERVICE': 'features/RESULTS_ARCHIVER_SERVICE.md',
        'SYSTEM_MONITORING_ENHANCEMENTS': 'technical/SYSTEM_MONITORING_ENHANCEMENTS.md',
        'WEBHOOK_INTEGRATION': 'technical/WEBHOOK_INTEGRATION.md',
        'TESTING_STRATEGY': 'technical/TESTING_STRATEGY.md',
        'SECURITY': 'technical/SECURITY.md',
        'API_INSTRUMENTATION': 'technical/API_INSTRUMENTATION.md'
    },

    // Feature cards for welcome page
    features: [
        {
            icon: "🏗️",
            title: "Architecture Modulaire",
            description: "5 services centralisés, routes Blueprint Flask, et frontend optimisé avec état centralisé"
        },
        {
            icon: "🎬",
            title: "Pipeline Complet",
            description: "7 étapes automatisées : extraction, conversion, détection scènes, analyse audio, tracking, réduction JSON, finalisation"
        },
        {
            icon: "⚡",
            title: "Performances Optimisées",
            description: "GPU/CPU adaptatif, multiprocessing, environnements virtuels spécialisés"
        },
        {
            icon: "🔒",
            title: "Sécurité Renforcée",
            description: "Sanitisation des fichiers, protection path traversal, validation d'intégrité"
        },
        {
            icon: "📊",
            title: "Monitoring Avancé",
            description: "Logs structurés, métriques temps réel, surveillance des ressources système"
        },
        {
            icon: "🧪",
            title: "Tests Complets",
            description: "Tests unitaires, intégration, validation automatique, scripts de debugging"
        }
    ],

    // Search configuration
    search: {
        enabled: true,
        minQueryLength: 3,
        maxResults: 10,
        debounceDelay: 300,
        highlightClass: "search-highlight"
    },

    // Table of contents configuration
    tableOfContents: {
        enabled: true,
        maxDepth: 4,
        minHeadings: 2,
        scrollOffset: 100,
        autoCollapse: false
    },

    // Theme configuration
    themes: {
        default: "light",
        available: ["light", "dark"],
        storageKey: "workflow-docs-theme"
    },

    // Code highlighting configuration
    codeHighlighting: {
        enabled: true,
        theme: "tomorrow",
        copyButton: true,
        lineNumbers: false,
        languages: [
            "javascript", "python", "bash", "json", "css", "html", "markdown"
        ]
    },

    // Mermaid diagram configuration
    mermaid: {
        enabled: true,
        theme: "default", // Will be overridden based on current theme
        securityLevel: "loose",
        startOnLoad: true,
        fontFamily: "inherit"
    },

    // Performance settings
    performance: {
        lazyLoadImages: true,
        enableServiceWorker: false,
        cacheDocuments: true,
        preloadCriticalDocs: ["ARCHITECTURE_COMPLETE_FR", "GUIDE_DEMARRAGE_RAPIDE"]
    },

    // UI settings
    ui: {
        sidebarWidth: "280px",
        headerHeight: "60px",
        enableBackToTop: true,
        enableReadingProgress: true,
        enableBreadcrumbs: true,
        mobileBreakpoint: "768px"
    },

    // External CDN URLs
    cdn: {
        marked: "https://cdn.jsdelivr.net/npm/marked@9.1.6/marked.min.js",
        mermaid: "https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js",
        prismCore: "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-core.min.js",
        prismAutoloader: "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/autoloader/prism-autoloader.min.js",
        prismTheme: "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css"
    },

    // Analytics (optional)
    analytics: {
        enabled: false,
        trackingId: null,
        trackPageViews: true,
        trackSearchQueries: true
    },

    // Accessibility settings
    accessibility: {
        enableKeyboardNavigation: true,
        enableScreenReaderSupport: true,
        highContrastMode: false,
        reducedMotion: false
    },

    // Development settings
    development: {
        enableDebugMode: false,
        showPerformanceMetrics: false,
        enableHotReload: false
    }
};

// Export configuration for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PORTAL_CONFIG;
} else if (typeof window !== 'undefined') {
    window.PORTAL_CONFIG = PORTAL_CONFIG;
}

// Configuration validation
function validateConfig(config) {
    const required = ['site', 'navigation', 'documentTitles'];
    const missing = required.filter(key => !config[key]);
    
    if (missing.length > 0) {
        console.error('Missing required configuration keys:', missing);
        return false;
    }
    
    // Validate navigation structure
    if (!Array.isArray(config.navigation)) {
        console.error('Navigation must be an array');
        return false;
    }
    
    for (const section of config.navigation) {
        if (!section.section || !Array.isArray(section.items)) {
            console.error('Invalid navigation section:', section);
            return false;
        }
        
        for (const item of section.items) {
            if (!item.id || !item.title) {
                console.error('Invalid navigation item:', item);
                return false;
            }
        }
    }
    
    return true;
}

// Initialize configuration
if (typeof window !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function() {
        if (!validateConfig(PORTAL_CONFIG)) {
            console.error('Invalid portal configuration');
            return;
        }
        
        // Apply configuration to the portal
        if (window.applyPortalConfig) {
            window.applyPortalConfig(PORTAL_CONFIG);
        }
    });
}

// Helper functions for configuration access
const ConfigHelper = {
    get: function(path, defaultValue = null) {
        const keys = path.split('.');
        let current = PORTAL_CONFIG;
        
        for (const key of keys) {
            if (current && typeof current === 'object' && key in current) {
                current = current[key];
            } else {
                return defaultValue;
            }
        }
        
        return current;
    },
    
    set: function(path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        let current = PORTAL_CONFIG;
        
        for (const key of keys) {
            if (!(key in current) || typeof current[key] !== 'object') {
                current[key] = {};
            }
            current = current[key];
        }
        
        current[lastKey] = value;
    },
    
    getDocumentTitle: function(docId) {
        return this.get(`documentTitles.${docId}`, docId);
    },
    
    isFeatureEnabled: function(feature) {
        return this.get(feature, false);
    }
};

// Export helper if in module environment
if (typeof module !== 'undefined' && module.exports) {
    module.exports.ConfigHelper = ConfigHelper;
} else if (typeof window !== 'undefined') {
    window.ConfigHelper = ConfigHelper;
}
