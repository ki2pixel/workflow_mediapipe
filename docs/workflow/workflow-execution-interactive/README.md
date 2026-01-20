# Interactive Workflow Execution Diagram

## Overview

This directory contains an interactive JointJS implementation of the workflow execution diagram, replacing the static Mermaid diagram with a fully interactive, drag-and-drop enabled visualization.

## Features

### 🎮 Interactive Functionality
- **Node Selection**: Click any node to select and highlight it
- **Drag & Drop**: Move selected nodes around the canvas
- **Automatic Re-routing**: Connections automatically adjust when nodes are moved
- **Clean Edge Routing**: Enhanced Manhattan routing avoids node overlaps
- **Theme Switching**: Toggle between dark and light themes
- **Panel Management**: Show/hide control and instruction panels for cleaner interface
- **Keyboard Shortcuts**: Quick access to all functions via keyboard
- **Smart Auto-hide**: Panels automatically hide after successful actions

### 🔧 Technical Implementation
- **Enhanced Manhattan Routing**: Boundary connection points with perpendicular anchors
- **Rounded Connectors**: Smooth connection lines with 8px radius
- **Boundary Connection Points**: Connections attach to node edges, not centers
- **Optimized Performance**: Async rendering with sorting optimization
- **Responsive Design**: Auto-scaling to fit content with zoom capabilities

### 🎨 Visual Design
- **Color-Coded Nodes**: Different colors for different node types:
  - **Blue**: Standard workflow steps
  - **Orange**: Decision points
  - **Red**: Start nodes and errors
  - **Green**: Success states
  - **Purple**: Monitoring components
  - **Teal**: External integrations
  - **Dark Teal**: Final completion
- **Professional Styling**: Consistent with project design patterns
- **Accessibility**: High contrast colors in both themes

## File Structure

```
workflow-execution-interactive/
├── index.html          # Main HTML structure with controls
├── script.js           # JointJS implementation with interactive features
├── style.css           # Comprehensive styling with theme support
└── README.md           # This documentation
```

## Usage

### Basic Interaction
1. **Open the diagram**: Navigate to `index.html` in a web browser
2. **Show panels**: Click the 🎮 or 📋 toggle buttons to show control/instruction panels
3. **Select nodes**: Click any node to highlight it
4. **Move nodes**: Drag selected nodes to reposition them
5. **Clear selection**: Click on empty space or press `Escape`
6. **Switch themes**: Use the toggle in the top-right corner

### Panel Management
- **Toggle Buttons**: Use 🎮 (controls) and 📋 (instructions) buttons to show/hide panels
- **Close Buttons**: Click the × button in panel headers to hide them
- **Auto-hide**: Panels automatically hide after successful actions
- **Clean Interface**: Panels are hidden by default for a clutter-free experience

### Control Panel Functions
- **🔍 Debug Connexions**: Analyze all connections in browser console
- **📍 Sélectionner Début**: Automatically select the start node
- **📍 Sélectionner Fin**: Automatically select the completion node
- **❌ Effacer Sélection**: Clear all selections
- **🔄 Réinitialiser**: Reset view and clear selections

### Keyboard Shortcuts
- **`C`**: Toggle controls panel
- **`I`**: Toggle instructions panel
- **`R`**: Reset diagram view
- **`Escape`**: Clear selection
- **`Ctrl+D`**: Debug connections
- **`?` or `/`**: Show instructions panel

### Console Commands
Open browser developer tools and use these commands:
```javascript
debugConnections()           // Analyze all connections
selectNode('text')          // Select node containing specified text
clearSelection()            // Clear current selection
resetDiagram()              // Reset view and clear selection
showControlsPanel()         // Show controls panel
hideControlsPanel()         // Hide controls panel
toggleControlsPanel()       // Toggle controls panel
showInfoPanel()             // Show instructions panel
hideInfoPanel()             // Hide instructions panel
toggleInfoPanel()           // Toggle instructions panel
```

## Workflow Structure

The diagram represents the complete workflow execution process:

### Main Workflow Steps
1. **STEP1**: Archive extraction with validation
2. **STEP2**: Video conversion to 25 FPS
3. **STEP3**: Scene detection using TransNetV2
4. **STEP4**: Audio analysis with spectrograms
5. **STEP5**: Video tracking with MediaPipe
6. **STEP6**: Finalization and cleanup

### Supporting Systems
- **Monitoring & State**: Real-time system monitoring
- **Error Handling**: Automatic retry with exponential backoff
- **External Integrations**: GPU acceleration, Airtable API, CSV monitoring

## Technical Specifications

### Routing Configuration
```javascript
defaultRouter: { 
    name: 'manhattan', 
    args: { 
        padding: 35,
        step: 25,
        maximumLoops: 2000,
        maxAllowedDirectionChange: 90,
        perpendicular: true,
        excludeEnds: ['source', 'target'],
        startDirections: ['top', 'right', 'bottom', 'left'],
        endDirections: ['top', 'right', 'bottom', 'left']
    } 
}
```

### Connection Points
```javascript
defaultConnectionPoint: {
    name: 'boundary',
    args: { sticky: true, stroke: true }
}
```

### Interactive Settings
```javascript
interactive: {
    elementMove: true,        // ✅ Enable node dragging
    vertexAdd: false,         // ❌ Prevent vertex manipulation
    vertexMove: false,        // ❌ Prevent vertex manipulation  
    vertexRemove: false,      // ❌ Prevent vertex manipulation
    arrowheadMove: false,     // ❌ Prevent arrow manipulation
    linkMove: false,          // ❌ Prevent link dragging
    addLinkFromMagnet: false  // ❌ Prevent new link creation
}
```

## Browser Compatibility

- **Chrome/Chromium**: Full support
- **Firefox**: Full support
- **Safari**: Full support
- **Edge**: Full support

## Performance

- **Async Rendering**: Non-blocking diagram rendering
- **Optimized Sorting**: Efficient layer management
- **Responsive Scaling**: Automatic content fitting
- **Memory Efficient**: Proper event cleanup and management

## Development

To modify the diagram:
1. Edit node positions in `script.js`
2. Adjust styling in `style.css`
3. Add new interactive features in the event handlers
4. Test with the debug functions

## Integration

This interactive diagram follows the established project patterns:
- Consistent with other JointJS diagrams in the project
- Uses the same routing improvements and interactive functionality
- Maintains the project's color scheme and design language
- Compatible with the existing documentation portal structure
