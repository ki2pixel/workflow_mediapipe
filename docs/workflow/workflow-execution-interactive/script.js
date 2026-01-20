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
    fontSize: 13,
    lineHeight: 16
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
            padding: 60,
            step: 15,
            maximumLoops: 5000,
            maxAllowedDirectionChange: 45,
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
            offset: 10,
            extrapolate: true,
            insideout: false
        }
    }
});
        console.log('✅ Paper created successfully');
    } catch (error) {
        console.error('❌ Failed to create paper:', error);
        throw new Error('Paper initialization failed: ' + error.message);
    }

paperContainer.appendChild(paper.el);

function createStart(x, y, text) {
    return new shapes.standard.Rectangle({
        position: { x: x + 10, y: y + 5 },
        size: { width: 120, height: 60 },
        z: 100,
        attrs: {
            body: {
                class: "jj-start-body",
                rx: 30,
                ry: 30
            },
            label: {
                class: "jj-start-text",
                ...fontAttributes,
                fontSize: fontAttributes.fontSize * 1.2,
                fontWeight: "bold",
                text,
                textWrap: {
                    width: -spacing * 2,
                    height: -spacing * 2
                }
            }
        }
    });
}

function createStep(x, y, text, nodeClass = "step") {
    return new shapes.standard.Path({
        position: { x, y },
        size: { width: 140, height: 70 },
        z: 100,
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

function createDecision(x, y, text) {
    return new shapes.standard.Path({
        position: { x: x - 40, y: y - 15 },
        size: { width: 180, height: 90 },
        z: 100,
        attrs: {
            body: {
                class: "jj-decision-body",
                d: "M 0 calc(0.5 * h) calc(0.5 * w) 0 calc(w) calc(0.5 * h) calc(0.5 * w) calc(h) Z"
            },
            label: {
                ...fontAttributes,
                class: "jj-decision-text",
                text,
                textWrap: {
                    width: -spacing * 3,
                    height: -spacing * 2
                }
            }
        }
    });
}

function createSuccess(x, y, text) {
    return createStep(x, y, text, "success");
}

function createError(x, y, text) {
    return createStep(x, y, text, "error");
}

function createMonitoring(x, y, text) {
    return createStep(x, y, text, "monitoring");
}

function createExternal(x, y, text) {
    return createStep(x, y, text, "external");
}

function createFinal(x, y, text) {
    return new shapes.standard.Rectangle({
        position: { x: x + 10, y: y + 5 },
        size: { width: 160, height: 80 },
        z: 100,
        attrs: {
            body: {
                class: "jj-final-body",
                rx: 20,
                ry: 20
            },
            label: {
                class: "jj-final-text",
                ...fontAttributes,
                fontSize: fontAttributes.fontSize * 1.3,
                fontWeight: "bold",
                text,
                textWrap: {
                    width: -spacing * 2,
                    height: -spacing * 2
                }
            }
        }
    });
}

function createFlow(source, target, labelText = "", sourceAnchor = null, targetAnchor = null) {
    if (!sourceAnchor || !targetAnchor) {
        const sourceBBox = source.getBBox();
        const targetBBox = target.getBBox();

        const dx = targetBBox.center().x - sourceBBox.center().x;
        const dy = targetBBox.center().y - sourceBBox.center().y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (Math.abs(dx) > Math.abs(dy)) {
            if (distance > 200) {
                sourceAnchor = sourceAnchor || (dx > 0 ? "right" : "left");
                targetAnchor = targetAnchor || (dx > 0 ? "left" : "right");
            } else {
                if (Math.abs(dy) > 50) {
                    sourceAnchor = sourceAnchor || (dy > 0 ? "bottom" : "top");
                    targetAnchor = targetAnchor || (dy > 0 ? "top" : "bottom");
                } else {
                    sourceAnchor = sourceAnchor || (dx > 0 ? "right" : "left");
                    targetAnchor = targetAnchor || (dx > 0 ? "left" : "right");
                }
            }
        } else {
            if (distance > 200) {
                sourceAnchor = sourceAnchor || (dy > 0 ? "bottom" : "top");
                targetAnchor = targetAnchor || (dy > 0 ? "top" : "bottom");
            } else {
                if (Math.abs(dx) > 50) {
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
        z: 1,
        router: {
            name: 'manhattan',
            args: {
                padding: 70,
                step: 12,
                maximumLoops: 8000,
                maxAllowedDirectionChange: 30,
                perpendicular: true,
                excludeEnds: ['source', 'target'],
                startDirections: ['top', 'right', 'bottom', 'left'],
                endDirections: ['top', 'right', 'bottom', 'left']
            }
        },
        connector: {
            name: 'rounded',
            args: {
                radius: 12,
                raw: true
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

    if (labelText) {
        link.labels([{ attrs: { labelText: { text: labelText } } }]);
    }

    return link;
}

const start = createStart(50, 50, "Démarrage\nWorkflow");
const initCheck = createDecision(250, 50, "Vérification\nPrérequis");
const errorInit = createError(450, 50, "Erreur\nInitialisation");

const step1Start = createStep(50, 200, "STEP1:\nExtraction Archives");
const step1Validate = createStep(250, 200, "Validation Archives\nZIP/RAR/TAR");
const step1Extract = createStep(450, 200, "Extraction Sécurisée\nSanitisation Paths");
const step1Organize = createStep(650, 200, "Organisation\nprojets_extraits/");
const step1Complete = createDecision(850, 200, "Extraction\nRéussie?");
const step1Success = createSuccess(1050, 200, "✓ Archives\nExtraites");
const step1Error = createError(850, 350, "✗ Erreur\nExtraction");

const step2Start = createStep(50, 500, "STEP2:\nConversion Vidéo");
const step2Scan = createStep(250, 500, "Scan Vidéos\nAnalyse FPS");
const step2Filter = createDecision(450, 500, "FPS ≠ 25.0?");
const step2Convert = createStep(650, 500, "Conversion GPU\nFFmpeg NVENC");
const step2Skip = createStep(650, 650, "Pas de\nConversion");
const step2Validate = createStep(850, 500, "Validation\nIntégrité");
const step2Complete = createDecision(1050, 500, "Conversion\nRéussie?");
const step2Success = createSuccess(1250, 500, "✓ Vidéos\n25 FPS");
const step2Error = createError(1050, 650, "✗ Erreur\nConversion");

const step3Start = createStep(50, 800, "STEP3:\nDétection Scènes");
const step3Load = createStep(250, 800, "Chargement\nTransNetV2");
const step3Process = createStep(450, 800, "Analyse Vidéo\nDétection Transitions");
const step3Export = createStep(650, 800, "Export CSV\nTimecodes + Frames");
const step3Complete = createDecision(850, 800, "Détection\nRéussie?");
const step3Success = createSuccess(1050, 800, "✓ Scènes\nDétectées");
const step3Error = createError(850, 950, "✗ Erreur\nDétection");

const step4Start = createStep(50, 1100, "STEP4:\nAnalyse Audio");
const step4Extract = createStep(250, 1100, "Extraction Audio\nFFmpeg");
const step4Analyze = createStep(450, 1100, "Analyse Spectrale\nSpectrogrammes");
const step4Features = createStep(650, 1100, "Extraction Features\nMFCC, Chroma");
const step4Json = createStep(850, 1100, "Export JSON\nMétadonnées Audio");
const step4Complete = createDecision(1050, 1100, "Analyse\nRéussie?");
const step4Success = createSuccess(1250, 1100, "✓ Audio\nAnalysé");
const step4Error = createError(1050, 1250, "✗ Erreur\nAudio");

const step5Start = createStep(50, 1400, "STEP5:\nSuivi Vidéo");
const step5Mode = createDecision(250, 1400, "Mode\nTraitement");
const step5Cpu = createStep(150, 1550, "Multiprocessing\n15 Workers");
const step5Gpu = createStep(350, 1550, "GPU Séquentiel\n1 Worker");
const step5Mediapipe = createStep(450, 1400, "MediaPipe\nDétection Faciale");
const step5Track = createStep(650, 1400, "Tracking Objets\nCoordonnées");
const step5JsonOut = createStep(850, 1400, "Export JSON\nDonnées Tracking");
const step5Complete = createDecision(1050, 1400, "Tracking\nRéussi?");
const step5Success = createSuccess(1250, 1400, "✓ Tracking\nTerminé");
const step5Error = createError(1050, 1550, "✗ Erreur\nTracking");

const step6Start = createStep(50, 1700, "STEP6:\nFinalisation");
const step6Validate = createStep(250, 1700, "Validation\nIntégrité Complète");
const step6Organize = createStep(450, 1700, "Organisation\nStructure Finale");
const step6Copy = createStep(650, 1700, "Copie Destination\nArchives Finales");
const step6Verify = createStep(850, 1700, "Vérification\nIntégrité Copie");
const step6Cleanup = createStep(1050, 1700, "Nettoyage\nFichiers Temporaires");
const step6Complete = createDecision(1250, 1700, "Finalisation\nRéussie?");
const step6Success = createSuccess(1450, 1700, "✓ Workflow\nTerminé");
const step6Error = createError(1250, 1850, "✗ Erreur\nFinalisation");

const workflowComplete = createFinal(1650, 1700, "🎉 Workflow Complet\nDonnées Prêtes");

const frontend = createMonitoring(1500, 50, "Interface Web");
const polling = createMonitoring(1700, 50, "PollingManager\nSurveillance Continue");
const apiStatus = createMonitoring(1900, 50, "API Status\nTemps Réel");
const appState = createMonitoring(2100, 50, "AppState\nÉtat Centralisé");
const uiUpdate = createMonitoring(2300, 50, "Mise à Jour UI\nDOMBatcher");

const cacheSystem = createMonitoring(1500, 200, "CacheService\nTTL Intelligent");
const perfTrack = createMonitoring(1700, 200, "PerformanceService\nMétriques");
const monitoring = createMonitoring(1900, 200, "MonitoringService\nRessources Système");

const errorHandler = createMonitoring(1500, 350, "ErrorHandler\nRecovery Automatique");
const retryLogic = createDecision(1700, 350, "Retry\nPossible?");
const backoff = createMonitoring(1900, 350, "Exponential\nBackoff");
const finalError = createError(1700, 500, "Erreur Finale\nNotification Utilisateur");

const csvMonitor = createExternal(1500, 650, "CSVService\nMonitoring Auto");
const airtableApi = createExternal(1700, 650, "AirtableService\nAPI Externe");
const gpuAccel = createExternal(1500, 800, "Accélération GPU\nNVIDIA CUDA");
const systemRes = createExternal(1700, 800, "Ressources Système\nCPU/RAM/Disque");

if (!graph) {
    console.error('❌ Graph not initialized - cannot add cells');
    throw new Error('Graph object is undefined');
}

console.log('📊 Adding nodes to graph...');
graph.addCells([
    start, initCheck, errorInit,

    step1Start, step1Validate, step1Extract, step1Organize, step1Complete, step1Success, step1Error,

    step2Start, step2Scan, step2Filter, step2Convert, step2Skip, step2Validate, step2Complete, step2Success, step2Error,

    step3Start, step3Load, step3Process, step3Export, step3Complete, step3Success, step3Error,

    step4Start, step4Extract, step4Analyze, step4Features, step4Json, step4Complete, step4Success, step4Error,

    step5Start, step5Mode, step5Cpu, step5Gpu, step5Mediapipe, step5Track, step5JsonOut, step5Complete, step5Success, step5Error,

    step6Start, step6Validate, step6Organize, step6Copy, step6Verify, step6Cleanup, step6Complete, step6Success, step6Error,

    workflowComplete,

    frontend, polling, apiStatus, appState, uiUpdate, cacheSystem, perfTrack, monitoring,

    errorHandler, retryLogic, backoff, finalError,

    csvMonitor, airtableApi, gpuAccel, systemRes
]);

const connections = [
    createFlow(start, initCheck),
    createFlow(initCheck, step1Start, "✓ OK"),
    createFlow(initCheck, errorInit, "✗ Erreur"),

    createFlow(step1Start, step1Validate),
    createFlow(step1Validate, step1Extract),
    createFlow(step1Extract, step1Organize),
    createFlow(step1Organize, step1Complete),
    createFlow(step1Complete, step1Success, "✓"),
    createFlow(step1Complete, step1Error, "✗"),

    createFlow(step1Success, step2Start),

    createFlow(step2Start, step2Scan),
    createFlow(step2Scan, step2Filter),
    createFlow(step2Filter, step2Convert, "Oui"),
    createFlow(step2Filter, step2Skip, "Non"),
    createFlow(step2Convert, step2Validate),
    createFlow(step2Skip, step2Complete),
    createFlow(step2Validate, step2Complete),
    createFlow(step2Complete, step2Success, "✓"),
    createFlow(step2Complete, step2Error, "✗"),

    createFlow(step2Success, step3Start),

    createFlow(step3Start, step3Load),
    createFlow(step3Load, step3Process),
    createFlow(step3Process, step3Export),
    createFlow(step3Export, step3Complete),
    createFlow(step3Complete, step3Success, "✓"),
    createFlow(step3Complete, step3Error, "✗"),

    createFlow(step3Success, step4Start),

    createFlow(step4Start, step4Extract),
    createFlow(step4Extract, step4Analyze),
    createFlow(step4Analyze, step4Features),
    createFlow(step4Features, step4Json),
    createFlow(step4Json, step4Complete),
    createFlow(step4Complete, step4Success, "✓"),
    createFlow(step4Complete, step4Error, "✗"),

    createFlow(step4Success, step5Start),

    createFlow(step5Start, step5Mode),
    createFlow(step5Mode, step5Cpu, "CPU"),
    createFlow(step5Mode, step5Gpu, "GPU"),
    createFlow(step5Cpu, step5Mediapipe),
    createFlow(step5Gpu, step5Mediapipe),
    createFlow(step5Mediapipe, step5Track),
    createFlow(step5Track, step5JsonOut),
    createFlow(step5JsonOut, step5Complete),
    createFlow(step5Complete, step5Success, "✓"),
    createFlow(step5Complete, step5Error, "✗"),

    createFlow(step5Success, step6Start),

    createFlow(step6Start, step6Validate),
    createFlow(step6Validate, step6Organize),
    createFlow(step6Organize, step6Copy),
    createFlow(step6Copy, step6Verify),
    createFlow(step6Verify, step6Cleanup),
    createFlow(step6Cleanup, step6Complete),
    createFlow(step6Complete, step6Success, "✓"),
    createFlow(step6Complete, step6Error, "✗"),

    createFlow(step6Success, workflowComplete),

    createFlow(frontend, polling),
    createFlow(polling, apiStatus),
    createFlow(apiStatus, appState),
    createFlow(appState, uiUpdate),
    createFlow(cacheSystem, perfTrack),
    createFlow(perfTrack, monitoring),

    createFlow(step1Error, errorHandler),
    createFlow(step2Error, errorHandler),
    createFlow(step3Error, errorHandler),
    createFlow(step4Error, errorHandler),
    createFlow(step5Error, errorHandler),
    createFlow(step6Error, errorHandler),
    createFlow(errorInit, errorHandler),
    createFlow(errorHandler, retryLogic),
    createFlow(retryLogic, backoff, "Oui"),
    createFlow(retryLogic, finalError, "Non"),
    createFlow(backoff, step1Start),

    createFlow(csvMonitor, airtableApi),
    createFlow(gpuAccel, step2Convert),
    createFlow(gpuAccel, step3Process),
    createFlow(gpuAccel, step5Gpu),
    createFlow(systemRes, monitoring)
];

if (!graph) {
    console.error('❌ Graph not initialized - cannot add connections');
    throw new Error('Graph object is undefined');
}

console.log('🔗 Adding connections to graph...');
graph.addCells(connections);

ensureProperLayering();

const graphBBox = graph.getBBox();

function transformToFitContent() {
    paper.transformToFitContent({
        padding: 50,
        contentArea: graphBBox,
        verticalAlign: "top",
        horizontalAlign: "left",
        scaleGrid: 0.1,
        minScale: 0.1,
        maxScale: 2
    });
}

window.addEventListener("resize", () => transformToFitContent());
setTimeout(() => transformToFitContent(), 100);

setupEventHandlers();

console.log('✅ Diagram initialized successfully');
}

function setupEventHandlers() {
    if (!paper) {
        console.error('❌ Paper not initialized - cannot setup event handlers');
        throw new Error('Paper object is undefined');
    }

    console.log('🎮 Setting up interactive event handlers...');

    const { mask: MaskHighlighter, stroke: StrokeHighlighter } = highlighters;

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

            // Apply enhanced routing to the specific link
            link.set('router', {
                name: 'manhattan',
                args: {
                    padding: 80,              // Extra large padding after movement
                    step: 10,                 // Very precise steps
                    maximumLoops: 10000,      // Maximum precision
                    maxAllowedDirectionChange: 25, // Very strict direction changes
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

// Function to ensure proper layering of diagram elements
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

    // Set all elements to higher z-index (foreground)
    elements.forEach(element => {
        element.set('z', 10);
    });

    console.log(`🎨 Layering enforced: ${links.length} connections behind ${elements.length} nodes`);
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
// Utility Functions
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

            // Apply enhanced routing to the specific link
            link.set('router', {
                name: 'manhattan',
                args: {
                    padding: 80,              // Extra large padding after movement
                    step: 10,                 // Very precise steps
                    maximumLoops: 10000,      // Maximum precision
                    maxAllowedDirectionChange: 25, // Very strict direction changes
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
    console.log("🔍 Analyse des connexions...");
    const links = graph.getLinks();
    const elements = graph.getElements();
    let overlapCount = 0;
    let connectionDetails = [];

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

    console.log(`📊 Résumé: ${links.length} connexions analysées, ${overlapCount} chevauchements détectés`);
    console.log(`📋 Éléments: ${elements.length} nœuds dans le diagramme`);
    console.log(`🔗 Détails des connexions:`, connectionDetails);

    updateStatusWithAutoHide(`🔍 Debug terminé: ${links.length} connexions, ${elements.length} nœuds - Voir console F12`);
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

            updateStatusWithAutoHide(`✅ Nœud sélectionné: ${searchText.replace(/\n/g, ' ')}`);
        }
    } else {
        updateStatus(`❌ Nœud non trouvé: ${searchText}`);
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
    updateStatusWithAutoHide("✅ Diagramme réinitialisé - Vue centrée");
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
        updateStatus("Panneau d'instructions affiché");
    }
}

function hideInfoPanel() {
    const panel = document.getElementById('info-panel');
    const toggleBtn = document.getElementById('toggle-info');
    if (panel && toggleBtn) {
        panel.classList.remove('visible');
        toggleBtn.classList.remove('active');
        updateStatus("Panneau d'instructions masqué");
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
    console.log("🔧 Optimisation de toutes les connexions...");
    const links = graph.getLinks();
    const elements = graph.getElements();
    let optimizedCount = 0;

    links.forEach(link => {
        const linkView = paper.findViewByModel(link);
        if (linkView) {
            // Apply maximum routing optimization
            link.set('router', {
                name: 'manhattan',
                args: {
                    padding: 90,              // Maximum padding
                    step: 8,                  // Finest steps
                    maximumLoops: 15000,      // Maximum loops for best path
                    maxAllowedDirectionChange: 20, // Strictest direction changes
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

    console.log(`✅ ${optimizedCount} connexions optimisées avec layering correct`);
    updateStatusWithAutoHide(`✅ Toutes les connexions optimisées (${optimizedCount} liens)`);
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
    console.log('🚀 Enhancing workflow execution diagram...');

    // Add zoom and pan controls
    addZoomPanControls();

    // Setup toggle button event listeners
    setupToggleButtons();

    // Initial status
    updateStatus("Diagramme chargé - Utilisez les boutons 🎮 et 📋 ou les raccourcis clavier");

    console.log('✅ Workflow execution diagram enhanced');
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
console.log('✅ Workflow execution interactive script loaded successfully');
