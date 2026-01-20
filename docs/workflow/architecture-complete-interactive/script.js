if (typeof joint === 'undefined') {
    console.error('JointJS library not loaded. Please check the script loading order.');
    throw new Error('JointJS library is required but not loaded.');
}

const { dia, shapes, highlighters, linkTools } = joint;

if (!dia || !shapes || !highlighters || !linkTools) {
    console.error('JointJS components not properly loaded:', { dia, shapes, highlighters, linkTools });
    throw new Error('Required JointJS components are not available.');
}

const unit = 4;
const bevel = 2 * unit;
const spacing = 2 * unit;
const flowSpacing = unit / 2;

const fontAttributes = {
    fontFamily: "PPFraktionSans, sans-serif",
    fontStyle: "normal",
    fontSize: 12,
    lineHeight: 15
};

let paperContainer, graph, paper;

function initializeDiagram() {
    paperContainer = document.getElementById("canvas");
    if (!paperContainer) {
        console.error('Canvas element not found. Make sure the HTML contains an element with id="canvas".');
        throw new Error('Canvas container element is required but not found.');
    }

    try {
        graph = new dia.Graph({}, { cellNamespace: shapes });
        console.log('✅ Graph created successfully');
    } catch (error) {
        console.error('❌ Failed to create graph:', error);
        throw new Error('Graph initialization failed: ' + error.message);
    }

    try {
        paper = new dia.Paper({
    model: graph,
    cellViewNamespace: shapes,
    width: "100%",
    height: "100%",
    async: true,
    sorting: dia.Paper.sorting.APPROX,
    background: { color: "transparent" },
    snapLabels: true,
    clickThreshold: 10,
    frozen: false,
    drawGrid: false,
    interactive: {
        elementMove: true,
        vertexAdd: false,
        vertexMove: false,  
        vertexRemove: false,
        arrowheadMove: false,
        linkMove: false,
        addLinkFromMagnet: false
    },
    gridSize: 5,
    defaultRouter: {
        name: 'manhattan',
        args: {
            padding: 40,
            step: 20,
            maximumLoops: 3000,
            maxAllowedDirectionChange: 60,
            perpendicular: true,
            excludeEnds: ['source', 'target'],
            startDirections: ['top', 'right', 'bottom', 'left'],
            endDirections: ['top', 'right', 'bottom', 'left'],
            fallbackRoute: function(from, to, opts) {
                return [];
            },
            directionMap: {
                'top': { x: 0, y: -1 },
                'bottom': { x: 0, y: 1 },
                'left': { x: -1, y: 0 },
                'right': { x: 1, y: 0 }
            }
        }
    },
    defaultConnector: { 
        name: 'rounded', 
        args: { radius: 8 } 
    },
    defaultAnchor: {
        name: 'perpendicular',
        args: {
            padding: 15,
            rotate: true
        }
    },
    defaultConnectionPoint: {
        name: 'boundary',
        args: {
            sticky: true,
            stroke: true,
            offset: 10,               // Add 10px offset from node boundary
            extrapolate: true,        // Extrapolate connection points for better routing
            insideout: false          // Ensure connections start from outside the node
        }
    }
});
        console.log('✅ Paper created successfully');
    } catch (error) {
        console.error('❌ Failed to create paper:', error);
        throw new Error('Paper initialization failed: ' + error.message);
    }

paperContainer.appendChild(paper.el);

// Node Creation Functions for Architecture Components
function createArchitectureNode(x, y, text, nodeClass = "frontend", width = 140, height = 70) {
    return new shapes.standard.Path({
        position: { x, y },
        size: { width, height },
        z: 100,  // High z-index to ensure nodes are above connections
        attrs: {
            body: {
                class: `jj-${nodeClass}-body`,
                d: `M 0 ${bevel} ${bevel} 0 calc(w-${bevel}) 0 calc(w) ${bevel} calc(w) calc(h-${bevel}) calc(w-${bevel}) calc(h) ${bevel} calc(h) 0 calc(h-${bevel}) Z`
            },
            label: {
                ...fontAttributes,
                class: `jj-${nodeClass}-text`,
                text,
                textWrap: {
                    width: -spacing * 2,
                    height: -spacing * 2
                }
            }
        }
    });
}

// Enhanced Flow Creation Function with Advanced Routing
function createFlow(source, target, labelText = "", sourceAnchor = null, targetAnchor = null) {
    // Auto-detect optimal anchors if not specified
    if (!sourceAnchor || !targetAnchor) {
        const sourceBBox = source.getBBox();
        const targetBBox = target.getBBox();

        // Calculate relative positions and distances
        const dx = targetBBox.center().x - sourceBBox.center().x;
        const dy = targetBBox.center().y - sourceBBox.center().y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Enhanced anchor selection optimized for improved layout spacing
        if (Math.abs(dx) > Math.abs(dy)) {
            // Horizontal connection preferred
            if (distance > 300) {
                // For long distances in spacious layout, prefer straight horizontal connections
                sourceAnchor = sourceAnchor || (dx > 0 ? "right" : "left");
                targetAnchor = targetAnchor || (dx > 0 ? "left" : "right");
            } else {
                // For shorter distances, consider vertical routing with increased threshold
                if (Math.abs(dy) > 100) {
                    sourceAnchor = sourceAnchor || (dy > 0 ? "bottom" : "top");
                    targetAnchor = targetAnchor || (dy > 0 ? "top" : "bottom");
                } else {
                    sourceAnchor = sourceAnchor || (dx > 0 ? "right" : "left");
                    targetAnchor = targetAnchor || (dx > 0 ? "left" : "right");
                }
            }
        } else {
            // Vertical connection preferred
            if (distance > 300) {
                // For long distances in spacious layout, prefer straight vertical connections
                sourceAnchor = sourceAnchor || (dy > 0 ? "bottom" : "top");
                targetAnchor = targetAnchor || (dy > 0 ? "top" : "bottom");
            } else {
                // For shorter distances, consider horizontal routing with increased threshold
                if (Math.abs(dx) > 100) {
                    sourceAnchor = sourceAnchor || (dx > 0 ? "right" : "left");
                    targetAnchor = targetAnchor || (dx > 0 ? "left" : "right");
                } else {
                    sourceAnchor = sourceAnchor || (dy > 0 ? "bottom" : "top");
                    targetAnchor = targetAnchor || (dy > 0 ? "top" : "bottom");
                }
            }
        }
    }

    const link = new shapes.standard.Link({
        source: { id: source.id, anchor: { name: sourceAnchor } },
        target: { id: target.id, anchor: { name: targetAnchor } },
        z: 1,  // Low z-index to ensure connections are behind nodes
        // Enhanced routing configuration optimized for improved layout
        router: {
            name: 'manhattan',
            args: {
                padding: 50,              // Optimized padding for spacious layout
                step: 18,                 // Larger steps for cleaner paths
                maximumLoops: 4000,       // Reduced loops for simpler routing
                maxAllowedDirectionChange: 45, // More flexible for better flow
                perpendicular: true,
                excludeEnds: ['source', 'target'],
                startDirections: ['top', 'right', 'bottom', 'left'],
                endDirections: ['top', 'right', 'bottom', 'left']
            }
        },
        connector: {
            name: 'rounded',
            args: {
                radius: 12,               // Larger radius for smoother curves
                raw: true                 // Use raw coordinates for better precision
            }
        },
        attrs: {
            line: {
                class: "jj-flow-line",
                targetMarker: {
                    class: "jj-flow-arrowhead",
                    d: `M 0 0 L ${2.5 * unit} ${1.25 * unit} L ${2.5 * unit} -${1.25 * unit} Z`
                }
            },
            outline: {
                class: "jj-flow-outline",
                connection: true
            }
        },
        markup: [
            {
                tagName: "path",
                selector: "wrapper",
                attributes: {
                    fill: "none",
                    cursor: "pointer",
                    stroke: "transparent",
                    "stroke-linecap": "round"
                }
            },
            {
                tagName: "path",
                selector: "outline",
                attributes: {
                    fill: "none",
                    "pointer-events": "none"
                }
            },
            {
                tagName: "path",
                selector: "line",
                attributes: {
                    fill: "none",
                    "pointer-events": "none"
                }
            }
        ],
        defaultLabel: {
            attrs: {
                labelBody: {
                    class: "jj-flow-label-body",
                    ref: "labelText",
                    d: `
                        M calc(x-${spacing}) calc(y-${spacing})
                        m 0 ${bevel} l ${bevel} -${bevel}
                        h calc(w+${2 * (spacing - bevel)}) l ${bevel} ${bevel}
                        v calc(h+${2 * (spacing - bevel)}) l -${bevel} ${bevel}
                        H calc(x-${spacing - bevel}) l -${bevel} -${bevel} Z
                    `
                },
                labelText: {
                    ...fontAttributes,
                    class: "jj-flow-label-text",
                    textAnchor: "middle",
                    textVerticalAnchor: "middle",
                    fontStyle: "italic"
                }
            },
            markup: [
                {
                    tagName: "path",
                    selector: "labelBody"
                },
                {
                    tagName: "text",
                    selector: "labelText"
                }
            ]
        }
    });

    // Add label if provided
    if (labelText) {
        link.labels([{ attrs: { labelText: { text: labelText } } }]);
    }

    return link;
}

// Function to create layer labels for better visual hierarchy
function createLayerLabel(x, y, text, color = "#666") {
    return new shapes.standard.Rectangle({
        position: { x, y },
        size: { width: 200, height: 40 },
        z: 50,  // Medium z-index between connections and nodes
        attrs: {
            body: {
                fill: 'transparent',
                stroke: 'none'
            },
            label: {
                ...fontAttributes,
                fontSize: 14,
                fontWeight: 'bold',
                fill: color,
                text: text,
                textAnchor: 'start',
                textVerticalAnchor: 'middle'
            }
        }
    });
}

const ui = createArchitectureNode(100, 80, "Interface Utilisateur\nWeb", "frontend", 180, 90);
const appState = createArchitectureNode(320, 80, "AppState.js\nÉtat Centralisé", "frontend", 160, 80);

// Frontend Utilities - Second row with more spacing
const domBatcher = createArchitectureNode(100, 200, "DOMBatcher.js\nOptimisation DOM", "frontend", 160, 80);
const perfOptimizer = createArchitectureNode(300, 200, "PerformanceOptimizer.js\nDebouncing/Throttling", "frontend", 180, 80);
const pollingManager = createArchitectureNode(520, 200, "PollingManager.js\nGestion Polling", "frontend", 160, 80);
const errorHandler = createArchitectureNode(720, 200, "ErrorHandler.js\nGestion Erreurs", "frontend", 160, 80);

const cssArch = createArchitectureNode(100, 320, "CSS Modulaire\nvariables.css\ncomponents/*.css", "frontend", 180, 90);

const flask = createArchitectureNode(1000, 80, "app_new.py\nApplication Flask\nPrincipale", "flask", 180, 100);
const apiBp = createArchitectureNode(920, 220, "api_routes.py\n12 endpoints\nsystème", "flask", 160, 90);
const wfBp = createArchitectureNode(1120, 220, "workflow_routes.py\n18 endpoints\nworkflow", "flask", 160, 90);

const workflowService = createArchitectureNode(100, 480, "WorkflowService\nGestion workflow\n& séquences", "service", 170, 90);
const monitoringService = createArchitectureNode(320, 480, "MonitoringService\nSurveillance\nsystème", "service", 170, 90);
const cacheService = createArchitectureNode(540, 480, "CacheService\nCache intelligent\nTTL", "service", 160, 90);

// Data & Performance Services - Bottom row
const performanceService = createArchitectureNode(100, 600, "PerformanceService\nMétriques\n& profiling", "service", 170, 90);
const webhookService = createArchitectureNode(320, 600, "WebhookService\nSource Webhook", "service", 160, 80);
const csvService = createArchitectureNode(540, 600, "CSVService\nMonitoring Webhook", "service", 160, 90);

const config = createArchitectureNode(800, 480, "config/settings.py\nConfiguration\ncentralisée", "config", 170, 90);
const security = createArchitectureNode(800, 600, "config/security.py\nSécurité & tokens", "config", 170, 80);

const envMain = createArchitectureNode(100, 780, "env/\nÉtapes 1, 2, 6\n+ Flask", "processing", 160, 90);
const envTrans = createArchitectureNode(300, 780, "transnet_env/\nÉtape 3\nDétection scènes", "processing", 160, 90);
const envAudio = createArchitectureNode(500, 780, "audio_env/\nÉtape 4\nAnalyse audio", "processing", 160, 90);
const envTrack = createArchitectureNode(700, 780, "tracking_env/\nÉtape 5\nSuivi vidéo", "processing", 160, 90);

// Workflow Scripts - Bottom row with better organization
const step1 = createArchitectureNode(100, 920, "step1/\nExtraction archives\nZIP/RAR/TAR", "processing", 160, 90);
const step2 = createArchitectureNode(300, 920, "step2/\nConversion vidéo\n25 FPS GPU", "processing", 160, 90);
const step3 = createArchitectureNode(500, 920, "step3/\nDétection scènes\nTransNetV2", "processing", 160, 90);
const step4 = createArchitectureNode(700, 920, "step4/\nAnalyse audio\nSpectrogrammes", "processing", 160, 90);
const step5 = createArchitectureNode(900, 920, "step5/\nSuivi vidéo\nMediaPipe CPU/GPU", "processing", 170, 90);
const step6 = createArchitectureNode(1100, 920, "step6/\nFinalisation\nArchives finales", "processing", 160, 90);

const projects = createArchitectureNode(1100, 480, "projets_extraits/\nDonnées de travail", "data", 170, 80);
const cacheDir = createArchitectureNode(1100, 600, "Cache système\nFichiers temporaires", "data", 170, 80);
const output = createArchitectureNode(1100, 720, "Destination finale\nArchives traitées", "data", 170, 80);

const webhookEndpoint = createArchitectureNode(1350, 480, "Webhook JSON\nDropbox-only", "external", 160, 80);
const gpu = createArchitectureNode(1350, 600, "GPU NVIDIA\nAccélération\nmatérielle", "external", 160, 90);
const system = createArchitectureNode(1350, 720, "Ressources Système\nCPU, RAM, Disque", "external", 170, 90);

// Layer Labels for Visual Hierarchy
const layer1Label = createLayerLabel(20, 40, "COUCHE 1: Interface Utilisateur", "#01579b");
const layer2Label = createLayerLabel(920, 40, "COUCHE 2: Application Web", "#e65100");
const layer3Label = createLayerLabel(20, 440, "COUCHE 3: Services Métier", "#4a148c");
const layer4Label = createLayerLabel(720, 440, "COUCHE 4: Configuration", "#1b5e20");
const layer5Label = createLayerLabel(20, 740, "COUCHE 5: Traitement", "#f57f17");
const layer6Label = createLayerLabel(1020, 440, "COUCHE 6: Données", "#880e4f");
const layer7Label = createLayerLabel(1270, 440, "COUCHE 7: Externe", "#33691e");

// Add all nodes to graph with enhanced organization
if (!graph) {
    console.error('❌ Graph not initialized - cannot add cells');
    throw new Error('Graph object is undefined');
}

console.log('🏗️ Adding architecture components to graph...');
graph.addCells([
    // Layer Labels for Visual Hierarchy
    layer1Label, layer2Label, layer3Label, layer4Label, layer5Label, layer6Label, layer7Label,

    // Frontend Layer
    ui, appState, domBatcher, perfOptimizer, pollingManager, errorHandler, cssArch,

    // Flask Application Layer
    flask, apiBp, wfBp,

    // Service Layer
    workflowService, monitoringService, cacheService, performanceService, webhookService, csvService,

    // Configuration & Security
    config, security,

    // Processing Layer - Environments
    envMain, envTrans, envAudio, envTrack,

    // Processing Layer - Scripts
    step1, step2, step3, step4, step5, step6,

    // Data Storage
    projects, cacheDir, output,

    // External Systems
    webhookEndpoint, gpu, system
]);

// Create Connections
const connections = [
    // Frontend to Flask connections
    createFlow(ui, apiBp),
    createFlow(ui, wfBp),
    createFlow(appState, ui),
    createFlow(domBatcher, ui),
    createFlow(perfOptimizer, ui),
    createFlow(pollingManager, ui),
    createFlow(errorHandler, ui),
    createFlow(cssArch, ui),

    // Flask to Services connections
    createFlow(apiBp, monitoringService),
    createFlow(apiBp, cacheService),
    createFlow(apiBp, performanceService),
    createFlow(apiBp, csvService),
    createFlow(wfBp, workflowService),
    createFlow(wfBp, monitoringService),
    createFlow(flask, config),
    createFlow(flask, security),

    // Service interconnections
    createFlow(workflowService, monitoringService),
    createFlow(workflowService, cacheService),
    createFlow(workflowService, performanceService),
    createFlow(csvService, webhookService),
    createFlow(cacheService, performanceService),

    // Services to Processing
    createFlow(workflowService, envMain),
    createFlow(workflowService, envTrans),
    createFlow(workflowService, envAudio),
    createFlow(workflowService, envTrack),

    // Environment to Scripts
    createFlow(envMain, step1),
    createFlow(envMain, step2),
    createFlow(envMain, step6),
    createFlow(envTrans, step3),
    createFlow(envAudio, step4),
    createFlow(envTrack, step5),

    // Scripts to Data
    createFlow(step1, projects),
    createFlow(step2, projects),
    createFlow(step3, projects),
    createFlow(step4, projects),
    createFlow(step5, projects),
    createFlow(step6, output),

    // Cache and Performance
    createFlow(cacheService, cacheDir),
    createFlow(performanceService, system),

    // External connections
    createFlow(webhookService, webhookEndpoint),
    createFlow(step2, gpu),
    createFlow(step3, gpu),
    createFlow(step5, gpu),
    createFlow(monitoringService, system)
];

// Add all connections to graph
if (!graph) {
    console.error('❌ Graph not initialized - cannot add connections');
    throw new Error('Graph object is undefined');
}

console.log('🔗 Adding architecture connections to graph...');
graph.addCells(connections);

ensureProperLayering();

// Auto-scale content to fit
const graphBBox = graph.getBBox();

function transformToFitContent() {
    // Recalculate bounding box for the new layout
    const currentBBox = graph.getBBox();
    paper.transformToFitContent({
        padding: 80,                  // Increased padding for better spacing
        contentArea: currentBBox,     // Use current bounding box
        verticalAlign: "top",
        horizontalAlign: "left",
        scaleGrid: 0.05,             // Finer scale grid for better precision
        minScale: 0.05,              // Lower minimum scale to accommodate larger layout
        maxScale: 1.5                // Reduced max scale for better readability
    });
}

// Initial scaling and resize handler
window.addEventListener("resize", () => transformToFitContent());
setTimeout(() => transformToFitContent(), 100);

// Setup interactive event handlers
setupEventHandlers();

console.log('✅ Architecture diagram initialized successfully');
}

// Setup all paper event handlers
function setupEventHandlers() {
    if (!paper) {
        console.error('❌ Paper not initialized - cannot setup event handlers');
        throw new Error('Paper object is undefined');
    }

    console.log('🎮 Setting up interactive event handlers...');

    // Interactive Features
    const { mask: MaskHighlighter, stroke: StrokeHighlighter } = highlighters;

    // Mouse enter/leave highlighting
    paper.on("cell:mouseenter", (cellView, evt) => {
        let selector, padding;
        if (cellView.model.isLink()) {
            if (StrokeHighlighter.get(cellView, "selection")) return;
            selector = { label: 0, selector: "labelBody" };
            padding = unit / 2;
        } else {
            selector = "body";
            padding = unit;
        }
        const frame = MaskHighlighter.add(cellView, selector, "frame", {
            padding,
            layer: dia.Paper.Layers.FRONT,
            attrs: {
                "stroke-width": 2,
                "stroke-linejoin": "round"
            }
        });
        frame.el.classList.add("jj-frame");
    });

    paper.on("cell:mouseleave", (cellView) => {
        MaskHighlighter.removeAll(paper, "frame");
    });

    // Node selection and dragging
    let selectedElement = null;

    paper.on("element:pointerdown", (elementView, evt) => {
        // Clear previous selection
        if (selectedElement) {
            StrokeHighlighter.removeAll(paper, "selection");
        }

        // Select new element
        selectedElement = elementView;
        const strokeHighlighter = StrokeHighlighter.add(
            elementView,
            "body",
            "selection",
            {
                layer: dia.Paper.Layers.BACK
            }
        );
        strokeHighlighter.el.classList.add("jj-flow-selection");

        // Update status
        const attrs = elementView.model.get('attrs');
        const elementText = (attrs && attrs.label && attrs.label.text) || 'Unknown';
        updateStatus(`Sélectionné: ${elementText.replace(/\n/g, ' ')}`);
    });

    paper.on("element:pointermove", (elementView, evt, x, y) => {
        if (selectedElement === elementView) {
            const attrs = elementView.model.get('attrs');
            const elementText = (attrs && attrs.label && attrs.label.text) || 'Unknown';
            updateStatus(`Déplacement: ${elementText.replace(/\n/g, ' ')} - Connexions en cours de re-routage...`);
        }
    });

    paper.on("element:pointerup", (elementView, evt) => {
        if (selectedElement === elementView) {
            const attrs = elementView.model.get('attrs');
            const elementText = (attrs && attrs.label && attrs.label.text) || 'Unknown';
            updateStatus(`Déplacé: ${elementText.replace(/\n/g, ' ')} - Connexions mises à jour`);

            // Force re-routing of all connected links to avoid overlaps
            setTimeout(() => {
                forceConnectionReRouting(elementView.model);
            }, 100);
        }
    });

paper.on("blank:pointerdown", () => {
    if (selectedElement) {
        deselectElement();
    }
});

function deselectElement() {
    if (selectedElement) {
        StrokeHighlighter.removeAll(paper, "selection");
        selectedElement = null;
        updateStatus("Sélection effacée");
    }
}

    // Link interaction
    paper.on("link:pointerclick", (cellView) => {
        paper.removeTools();
        dia.HighlighterView.removeAll(paper);

        const snapAnchor = function (coords, endView) {
            const bbox = endView.model.getBBox();
            const point = bbox.pointNearestToPoint(coords);
            const center = bbox.center();
            const snapRadius = 15;
            if (Math.abs(point.x - center.x) < snapRadius) {
                point.x = center.x;
            }
            if (Math.abs(point.y - center.y) < snapRadius) {
                point.y = center.y;
            }
            return point;
        };

        const toolsView = new dia.ToolsView({
            tools: [
                new linkTools.TargetAnchor({
                    snap: snapAnchor,
                    resetAnchor: cellView.model.prop(["target", "anchor"])
                }),
                new linkTools.SourceAnchor({
                    snap: snapAnchor,
                    resetAnchor: cellView.model.prop(["source", "anchor"])
                })
            ]
        });

        cellView.addTools(toolsView);

        const strokeHighlighter = StrokeHighlighter.add(
            cellView,
            "root",
            "selection",
            {
                layer: dia.Paper.Layers.BACK
            }
        );
        strokeHighlighter.el.classList.add("jj-flow-selection");
    });

    console.log('✅ Event handlers setup complete');
}

// Function to force re-routing of connections when nodes are moved
function forceConnectionReRouting(element) {
    if (!graph || !paper) {
        console.error('❌ Graph or Paper not initialized - cannot re-route connections');
        return;
    }

    const connectedLinks = graph.getConnectedLinks(element);

    connectedLinks.forEach(link => {
        // Temporarily remove and re-add the link to force re-routing
        const linkView = paper.findViewByModel(link);
        if (linkView) {
            // Force the link to recalculate its path
            linkView.update();

            // Apply enhanced routing optimized for improved layout
            link.set('router', {
                name: 'manhattan',
                args: {
                    padding: 55,              // Optimized padding for spacious architecture
                    step: 16,                 // Balanced steps for clean re-routing
                    maximumLoops: 6000,       // Sufficient precision for good paths
                    maxAllowedDirectionChange: 35, // Flexible direction changes
                    perpendicular: true,
                    excludeEnds: ['source', 'target'],
                    startDirections: ['top', 'right', 'bottom', 'left'],
                    endDirections: ['top', 'right', 'bottom', 'left']
                }
            });

            // Ensure connection stays behind nodes
            link.set('z', 1);
            linkView.update();
        }
    });

    // Ensure the moved element stays in front
    element.set('z', 100);
}

// Function to ensure proper layering of architecture diagram elements
function ensureProperLayering() {
    if (!graph) {
        console.error('❌ Graph not initialized - cannot ensure proper layering');
        return;
    }

    // Get all elements and links
    const elements = graph.getElements();
    const links = graph.getLinks();

    // Set all links to low z-index (background)
    links.forEach(link => {
        link.set('z', 1);
    });

    // Set all elements to higher z-index (foreground) with component-specific layering
    elements.forEach(element => {
        const attrs = element.get('attrs');
        const bodyClass = (attrs && attrs.body && attrs.body.class) || '';

        // Different z-index for different component types
        if (bodyClass.includes('frontend')) {
            element.set('z', 20);
        } else if (bodyClass.includes('service')) {
            element.set('z', 15);
        } else {
            element.set('z', 10);
        }
    });

    console.log(`🎨 Architecture layering enforced: ${links.length} connections behind ${elements.length} components`);
}

// Theme switcher
document.querySelector(".theme-switch").addEventListener(
    "click",
    () => {
        document.body.classList.toggle("light-theme");
    },
    false
);

/* DUPLICATE CODE REMOVED - Event handlers now in setupEventHandlers() function
// Interactive Features
const { mask: MaskHighlighter, stroke: StrokeHighlighter } = highlighters;

// Mouse enter/leave highlighting
paper.on("cell:mouseenter", (cellView, evt) => {
    let selector, padding;
    if (cellView.model.isLink()) {
        if (StrokeHighlighter.get(cellView, "selection")) return;
        selector = { label: 0, selector: "labelBody" };
        padding = unit / 2;
    } else {
        selector = "body";
        padding = unit;
    }
    const frame = MaskHighlighter.add(cellView, selector, "frame", {
        padding,
        layer: dia.Paper.Layers.FRONT,
        attrs: {
            "stroke-width": 2,
            "stroke-linejoin": "round"
        }
    });
    frame.el.classList.add("jj-frame");
});

paper.on("cell:mouseleave", (cellView) => {
    MaskHighlighter.removeAll(paper, "frame");
});

// Node selection and dragging
let selectedElement = null;

paper.on("element:pointerdown", (elementView, evt) => {
    // Clear previous selection
    if (selectedElement) {
        StrokeHighlighter.removeAll(paper, "selection");
    }

    // Select new element
    selectedElement = elementView;
    const strokeHighlighter = StrokeHighlighter.add(
        elementView,
        "body",
        "selection",
        {
            layer: dia.Paper.Layers.BACK
        }
    );
    strokeHighlighter.el.classList.add("jj-flow-selection");

    // Update status
    const attrs = elementView.model.get('attrs');
    const elementText = (attrs && attrs.label && attrs.label.text) || 'Unknown';
    updateStatus(`Sélectionné: ${elementText.replace(/\n/g, ' ')}`);
});

paper.on("element:pointermove", (elementView, evt, x, y) => {
    if (selectedElement === elementView) {
        const attrs = elementView.model.get('attrs');
        const elementText = (attrs && attrs.label && attrs.label.text) || 'Unknown';
        updateStatus(`Déplacement: ${elementText.replace(/\n/g, ' ')} - Connexions en cours de re-routage...`);
    }
});

paper.on("element:pointerup", (elementView, evt) => {
    if (selectedElement === elementView) {
        const attrs = elementView.model.get('attrs');
        const elementText = (attrs && attrs.label && attrs.label.text) || 'Unknown';
        updateStatus(`Déplacé: ${elementText.replace(/\n/g, ' ')} - Connexions mises à jour`);

        // Force re-routing of all connected links to avoid overlaps
        setTimeout(() => {
            forceConnectionReRouting(elementView.model);
        }, 100);
    }
});

// Function to force re-routing of connections when nodes are moved
function forceConnectionReRouting(element) {
    const connectedLinks = graph.getConnectedLinks(element);

    connectedLinks.forEach(link => {
        // Temporarily remove and re-add the link to force re-routing
        const linkView = paper.findViewByModel(link);
        if (linkView) {
            // Force the link to recalculate its path
            linkView.update();

            // Apply enhanced routing optimized for improved layout
            link.set('router', {
                name: 'manhattan',
                args: {
                    padding: 55,              // Optimized padding for spacious architecture
                    step: 16,                 // Balanced steps for clean re-routing
                    maximumLoops: 6000,       // Sufficient precision for good paths
                    maxAllowedDirectionChange: 35, // Flexible direction changes
                    perpendicular: true,
                    excludeEnds: ['source', 'target'],
                    startDirections: ['top', 'right', 'bottom', 'left'],
                    endDirections: ['top', 'right', 'bottom', 'left']
                }
            });

            // Ensure connection stays behind nodes
            link.set('z', 1);
        }
    });

    // Ensure the moved element stays in front
    element.set('z', 100);
}

paper.on("blank:pointerdown", () => {
    if (selectedElement) {
        StrokeHighlighter.removeAll(paper, "selection");
        selectedElement = null;
        updateStatus("Sélection effacée");
    }
});

// Link interaction
paper.on("link:pointerclick", (cellView) => {
    paper.removeTools();
    dia.HighlighterView.removeAll(paper);

    const snapAnchor = function (coords, endView) {
        const bbox = endView.model.getBBox();
        const point = bbox.pointNearestToPoint(coords);
        const center = bbox.center();
        const snapRadius = 15;
        if (Math.abs(point.x - center.x) < snapRadius) {
            point.x = center.x;
        }
        if (Math.abs(point.y - center.y) < snapRadius) {
            point.y = center.y;
        }
        return point;
    };

    const toolsView = new dia.ToolsView({
        tools: [
            new linkTools.TargetAnchor({
                snap: snapAnchor,
                resetAnchor: cellView.model.prop(["target", "anchor"])
            }),
            new linkTools.SourceAnchor({
                snap: snapAnchor,
                resetAnchor: cellView.model.prop(["source", "anchor"])
            })
        ]
    });
    toolsView.el.classList.add("jj-flow-tools");
    cellView.addTools(toolsView);

    const strokeHighlighter = StrokeHighlighter.add(
        cellView,
        "root",
        "selection",
        {
            layer: dia.Paper.Layers.BACK
        }
    );
    strokeHighlighter.el.classList.add("jj-flow-selection");
});
END DUPLICATE CODE REMOVAL */

// Utility Functions
function updateStatus(message) {
    const statusElement = document.getElementById('status');
    if (statusElement) {
        statusElement.textContent = message;
    }
}

function debugConnections() {
    console.log("🔍 Analyse de l'architecture...");
    const links = graph.getLinks();
    const elements = graph.getElements();
    let connectionDetails = [];

    // Group elements by type
    const elementsByType = {
        frontend: [],
        flask: [],
        service: [],
        config: [],
        processing: [],
        data: [],
        external: []
    };

    elements.forEach(element => {
        const attrs = element.get('attrs');
        const bodyClass = (attrs && attrs.body && attrs.body.class) || '';
        const text = (attrs && attrs.label && attrs.label.text) || 'Unknown';

        if (bodyClass.includes('frontend')) elementsByType.frontend.push(text);
        else if (bodyClass.includes('flask')) elementsByType.flask.push(text);
        else if (bodyClass.includes('service')) elementsByType.service.push(text);
        else if (bodyClass.includes('config')) elementsByType.config.push(text);
        else if (bodyClass.includes('processing')) elementsByType.processing.push(text);
        else if (bodyClass.includes('data')) elementsByType.data.push(text);
        else if (bodyClass.includes('external')) elementsByType.external.push(text);
    });

    links.forEach((link, index) => {
        const linkView = paper.findViewByModel(link);
        if (linkView) {
            const sourceId = link.get('source').id;
            const targetId = link.get('target').id;
            const sourceElement = graph.getCell(sourceId);
            const targetElement = graph.getCell(targetId);

            if (sourceElement && targetElement) {
                const sourceAttrs = sourceElement.get('attrs');
                const targetAttrs = targetElement.get('attrs');
                const sourceText = (sourceAttrs && sourceAttrs.label && sourceAttrs.label.text) || 'Unknown';
                const targetText = (targetAttrs && targetAttrs.label && targetAttrs.label.text) || 'Unknown';

                const connectionInfo = `${sourceText.replace(/\n/g, ' ')} → ${targetText.replace(/\n/g, ' ')}`;
                connectionDetails.push(connectionInfo);
                console.log(`Connexion ${index + 1}: ${connectionInfo}`);
            }
        }
    });

    console.log(`📊 Résumé Architecture:`);
    console.log(`  🎨 Frontend: ${elementsByType.frontend.length} composants`);
    console.log(`  🌐 Flask: ${elementsByType.flask.length} composants`);
    console.log(`  ⚙️ Services: ${elementsByType.service.length} composants`);
    console.log(`  🔧 Configuration: ${elementsByType.config.length} composants`);
    console.log(`  🔄 Processing: ${elementsByType.processing.length} composants`);
    console.log(`  💾 Données: ${elementsByType.data.length} composants`);
    console.log(`  🌍 Externe: ${elementsByType.external.length} composants`);
    console.log(`  🔗 Connexions: ${links.length} liens`);

    updateStatusWithAutoHide(`🔍 Debug terminé: ${elements.length} composants, ${links.length} connexions - Voir console F12`);
}

function selectNode(searchText) {
    const elements = graph.getElements();
    const found = elements.find(element => {
        const attrs = element.get('attrs');
        const text = (attrs && attrs.label && attrs.label.text) || '';
        return text.toLowerCase().includes(searchText.toLowerCase());
    });

    if (found) {
        const elementView = paper.findViewByModel(found);
        if (elementView) {
            // Clear previous selection
            if (selectedElement) {
                StrokeHighlighter.removeAll(paper, "selection");
            }

            // Select found element
            selectedElement = elementView;
            const strokeHighlighter = StrokeHighlighter.add(
                elementView,
                "body",
                "selection",
                {
                    layer: dia.Paper.Layers.BACK
                }
            );
            strokeHighlighter.el.classList.add("jj-flow-selection");

            // Center on element with smooth animation
            const bbox = found.getBBox();
            const center = bbox.center();

            // Get current viewport
            const currentScale = paper.scale();
            const paperSize = paper.getComputedSize();

            // Calculate new position to center the element
            const newX = (paperSize.width / 2) - (center.x * currentScale.sx);
            const newY = (paperSize.height / 2) - (center.y * currentScale.sy);

            // Animate to center the selected element
            paper.translate(newX, newY);

            updateStatusWithAutoHide(`✅ Composant sélectionné: ${searchText.replace(/\n/g, ' ')}`);
        }
    } else {
        updateStatus(`❌ Composant non trouvé: ${searchText}`);
    }
}

function clearSelection() {
    if (selectedElement) {
        StrokeHighlighter.removeAll(paper, "selection");
        selectedElement = null;
    }
    paper.removeTools();
    dia.HighlighterView.removeAll(paper);
    updateStatusWithAutoHide("✅ Sélections effacées");
}

function resetDiagram() {
    clearSelection();
    transformToFitContent();
    updateStatusWithAutoHide("✅ Architecture réinitialisée - Vue centrée");
}

// Panel Management Functions
function showControlsPanel() {
    const panel = document.getElementById('controls-panel');
    const toggleBtn = document.getElementById('toggle-controls');
    if (panel && toggleBtn) {
        panel.classList.add('visible');
        toggleBtn.classList.add('active');
        updateStatus("Panneau de contrôles affiché");
    }
}

function hideControlsPanel() {
    const panel = document.getElementById('controls-panel');
    const toggleBtn = document.getElementById('toggle-controls');
    if (panel && toggleBtn) {
        panel.classList.remove('visible');
        toggleBtn.classList.remove('active');
        updateStatus("Panneau de contrôles masqué");
    }
}

function toggleControlsPanel() {
    const panel = document.getElementById('controls-panel');
    if (panel) {
        if (panel.classList.contains('visible')) {
            hideControlsPanel();
        } else {
            showControlsPanel();
        }
    }
}

function showInfoPanel() {
    const panel = document.getElementById('info-panel');
    const toggleBtn = document.getElementById('toggle-info');
    if (panel && toggleBtn) {
        panel.classList.add('visible');
        toggleBtn.classList.add('active');
        updateStatus("Guide d'architecture affiché");
    }
}

function hideInfoPanel() {
    const panel = document.getElementById('info-panel');
    const toggleBtn = document.getElementById('toggle-info');
    if (panel && toggleBtn) {
        panel.classList.remove('visible');
        toggleBtn.classList.remove('active');
        updateStatus("Guide d'architecture masqué");
    }
}

function toggleInfoPanel() {
    const panel = document.getElementById('info-panel');
    if (panel) {
        if (panel.classList.contains('visible')) {
            hideInfoPanel();
        } else {
            showInfoPanel();
        }
    }
}


document.addEventListener('keydown', function(event) {
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }

    switch(event.key.toLowerCase()) {
        case 'c':
            event.preventDefault();
            toggleControlsPanel();
            break;
        case 'i':
            event.preventDefault();
            toggleInfoPanel();
            break;
        case 'r':
            event.preventDefault();
            resetDiagram();
            break;
        case 'escape':
            event.preventDefault();
            clearSelection();
            break;
        case 'd':
            if (event.ctrlKey || event.metaKey) {
                event.preventDefault();
                debugConnections();
            }
            break;
        case 'o':
            event.preventDefault();
            optimizeAllConnections();
            break;
        case '?':
        case '/':
            event.preventDefault();
            showInfoPanel();
            break;
        case 'f':
            event.preventDefault();
            selectNode('Interface Utilisateur');
            break;
        case 's':
            event.preventDefault();
            selectNode('WorkflowService');
            break;
        case 'w':
            event.preventDefault();
            selectNode('Flask');
            break;
    }
});

// Enhanced status update with auto-hide for panels
function updateStatusWithAutoHide(message, hideAfter = 3000) {
    updateStatus(message);

    // Auto-hide panels after successful actions (except for error messages)
    if (!message.includes('Erreur') && !message.includes('non trouvé')) {
        setTimeout(() => {
            const controlsPanel = document.getElementById('controls-panel');
            const infoPanel = document.getElementById('info-panel');

            // Only auto-hide if both panels are visible (user might want to keep one open)
            if (controlsPanel && infoPanel &&
                controlsPanel.classList.contains('visible') &&
                infoPanel.classList.contains('visible')) {
                hideControlsPanel();
            }
        }, hideAfter);
    }
}

// Global function to optimize all connections
function optimizeAllConnections() {
    console.log("🔧 Optimisation de toutes les connexions d'architecture...");
    const links = graph.getLinks();
    const elements = graph.getElements();
    let optimizedCount = 0;

    links.forEach(link => {
        const linkView = paper.findViewByModel(link);
        if (linkView) {
            // Apply maximum routing optimization for improved architecture layout
            link.set('router', {
                name: 'manhattan',
                args: {
                    padding: 60,              // Optimized padding for spacious layout
                    step: 15,                 // Balanced steps for clean paths
                    maximumLoops: 8000,       // Sufficient loops for good routing
                    maxAllowedDirectionChange: 30, // Balanced direction changes
                    perpendicular: true,
                    excludeEnds: ['source', 'target'],
                    startDirections: ['top', 'right', 'bottom', 'left'],
                    endDirections: ['top', 'right', 'bottom', 'left']
                }
            });
            // Ensure connection stays behind nodes
            link.set('z', 1);
            linkView.update();
            optimizedCount++;
        }
    });

    // Ensure all elements stay in front
    elements.forEach(element => {
        element.set('z', 100);
    });

    console.log(`✅ ${optimizedCount} connexions d'architecture optimisées avec layering correct`);
    updateStatusWithAutoHide(`✅ Architecture optimisée (${optimizedCount} connexions)`);
}

// Enhanced Zoom and Pan Controls for Lightbox Integration
let currentZoom = 1;
let isPanMode = false;
let panStart = null;
let originalTransform = null;

// Zoom functions
function zoomIn() {
    currentZoom = Math.min(currentZoom * 1.2, 3); // Max zoom 3x
    applyZoom();
    updateStatus(`🔍 Zoom: ${Math.round(currentZoom * 100)}%`);
}

function zoomOut() {
    currentZoom = Math.max(currentZoom / 1.2, 0.1); // Min zoom 10%
    applyZoom();
    updateStatus(`🔍 Zoom: ${Math.round(currentZoom * 100)}%`);
}

function resetZoom() {
    currentZoom = 1;
    applyZoom();
    // Also reset to fit content
    transformToFitContent();
    updateStatus("🔄 Vue réinitialisée");
}

function applyZoom() {
    if (paper) {
        const currentScale = paper.scale();
        const newScale = { sx: currentZoom, sy: currentZoom };
        paper.scale(newScale.sx, newScale.sy);
    }
}

// Pan mode functions
function togglePanMode() {
    isPanMode = !isPanMode;
    const panButton = document.getElementById('pan-toggle');
    if (panButton) {
        panButton.textContent = isPanMode ? '✋ Pan: ON' : '👆 Pan: OFF';
        panButton.style.background = isPanMode ? '#28a745' : '#6c757d';
    }

    // Change cursor
    const canvas = document.getElementById('canvas');
    if (canvas) {
        canvas.style.cursor = isPanMode ? 'grab' : 'default';
    }

    updateStatus(isPanMode ? "🤚 Mode panoramique activé - Cliquez et glissez pour déplacer" : "👆 Mode panoramique désactivé");
}

// Pan functionality
function setupPanControls() {
    const canvas = document.getElementById('canvas');
    if (!canvas) return;

    canvas.addEventListener('mousedown', (e) => {
        if (isPanMode || e.shiftKey) {
            panStart = { x: e.clientX, y: e.clientY };
            originalTransform = paper.translate();
            canvas.style.cursor = 'grabbing';
            e.preventDefault();
        }
    });

    canvas.addEventListener('mousemove', (e) => {
        if (panStart && (isPanMode || e.shiftKey)) {
            const dx = e.clientX - panStart.x;
            const dy = e.clientY - panStart.y;

            paper.translate(
                originalTransform.tx + dx,
                originalTransform.ty + dy
            );
            e.preventDefault();
        }
    });

    canvas.addEventListener('mouseup', (e) => {
        if (panStart) {
            panStart = null;
            originalTransform = null;
            canvas.style.cursor = isPanMode ? 'grab' : 'default';
        }
    });

    // Spacebar for temporary pan mode
    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && !e.repeat) {
            if (!isPanMode) {
                canvas.style.cursor = 'grab';
                updateStatus("🤚 Mode panoramique temporaire - Maintenez Espace + glissez");
            }
            e.preventDefault();
        }
    });

    document.addEventListener('keyup', (e) => {
        if (e.code === 'Space') {
            if (!isPanMode) {
                canvas.style.cursor = 'default';
                updateStatus("👆 Mode panoramique temporaire désactivé");
            }
        }
    });
}

// Add zoom and pan controls to the interface
function addZoomPanControls() {
    const controlsPanel = document.querySelector('.controls-panel');
    if (!controlsPanel) return;

    const zoomPanControls = document.createElement('div');
    zoomPanControls.className = 'zoom-pan-controls';
    zoomPanControls.innerHTML = `
        <div class="control-group">
            <h4>🔍 Zoom & Pan</h4>
            <div class="button-group">
                <button id="zoom-in" class="control-btn" title="Zoom avant">🔍+</button>
                <button id="zoom-out" class="control-btn" title="Zoom arrière">🔍-</button>
                <button id="zoom-reset" class="control-btn" title="Réinitialiser la vue">🔄</button>
                <button id="pan-toggle" class="control-btn" title="Activer/désactiver le mode panoramique">👆 Pan: OFF</button>
            </div>
            <div class="pan-instructions">
                <small>💡 Maintenez Espace + glissez pour panoramique temporaire</small>
            </div>
        </div>
    `;

    controlsPanel.appendChild(zoomPanControls);

    // Add event listeners
    document.getElementById('zoom-in').addEventListener('click', zoomIn);
    document.getElementById('zoom-out').addEventListener('click', zoomOut);
    document.getElementById('zoom-reset').addEventListener('click', resetZoom);
    document.getElementById('pan-toggle').addEventListener('click', togglePanMode);

    // Setup pan controls
    setupPanControls();
}

// Make functions globally available
window.debugConnections = debugConnections;
window.selectNode = selectNode;
window.clearSelection = clearSelection;
window.resetDiagram = resetDiagram;
window.optimizeAllConnections = optimizeAllConnections;
window.forceConnectionReRouting = forceConnectionReRouting;
window.ensureProperLayering = ensureProperLayering;
window.showControlsPanel = showControlsPanel;
window.hideControlsPanel = hideControlsPanel;
window.toggleControlsPanel = toggleControlsPanel;
window.showInfoPanel = showInfoPanel;
window.hideInfoPanel = hideInfoPanel;
window.toggleInfoPanel = toggleInfoPanel;
// Zoom and pan functions
window.zoomIn = zoomIn;
window.zoomOut = zoomOut;
window.resetZoom = resetZoom;
window.togglePanMode = togglePanMode;

// Enhanced initialization function
function enhanceInitialization() {
    console.log('🚀 Enhancing architecture diagram...');

    // Add zoom and pan controls
    addZoomPanControls();

    // Setup toggle button event listeners
    setupToggleButtons();

    // Initial status
    updateStatus("Architecture chargée - Utilisez les boutons 🎮 et 📋 ou les raccourcis clavier");

    console.log('✅ Architecture diagram enhanced');
}

// Setup toggle button event listeners
function setupToggleButtons() {
    console.log('🔧 Setting up toggle buttons...');

    const toggleControlsBtn = document.getElementById('toggle-controls');
    const toggleInfoBtn = document.getElementById('toggle-info');

    if (toggleControlsBtn) {
        toggleControlsBtn.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('🎮 Controls toggle clicked');
            toggleControlsPanel();
        });
        console.log('✅ Controls toggle button setup');
    } else {
        console.error('❌ Controls toggle button not found');
    }

    if (toggleInfoBtn) {
        toggleInfoBtn.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('📋 Info toggle clicked');
            toggleInfoPanel();
        });
        console.log('✅ Info toggle button setup');
    } else {
        console.error('❌ Info toggle button not found');
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initializeDiagram(); // Original diagram creation
        enhanceInitialization(); // Add enhanced features
    });
} else {
    // DOM is already ready
    initializeDiagram(); // Original diagram creation
    enhanceInitialization(); // Add enhanced features
}

// End of script - ensure proper closure
console.log('✅ Architecture complete interactive script loaded successfully');
