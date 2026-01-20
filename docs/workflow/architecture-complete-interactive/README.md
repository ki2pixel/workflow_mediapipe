# Interactive Architecture Complete Diagram

## Overview

This directory contains an interactive JointJS implementation of the complete system architecture diagram, replacing the static Mermaid diagram with a fully interactive, drag-and-drop enabled visualization that shows the entire system structure from frontend to backend.

## Features

### 🎮 Interactive Functionality
- **Component Selection**: Click any component to select and highlight it
- **Drag & Drop**: Move selected components around the canvas
- **Automatic Re-routing**: Connections automatically adjust when components are moved
- **Clean Edge Routing**: Enhanced Manhattan routing avoids component overlaps
- **Theme Switching**: Toggle between dark and light themes
- **Panel Management**: Show/hide control and instruction panels for cleaner interface
- **Keyboard Shortcuts**: Quick access to all functions via keyboard
- **Smart Auto-hide**: Panels automatically hide after successful actions

### 🔧 Technical Implementation
- **Enhanced Manhattan Routing**: Optimized for spacious layout with balanced padding and steps
- **Rounded Connectors**: Smooth connection lines with 12px radius for better visibility
- **Boundary Connection Points**: Connections attach to component edges with improved spacing
- **Optimized Performance**: Async rendering with sorting optimization and efficient routing
- **Responsive Design**: Enhanced auto-scaling with finer precision for larger layouts
- **Visual Layer Labels**: Clear hierarchy indicators for each architecture layer
- **Improved Spacing**: Increased node spacing and better organization for enhanced readability

### 🎨 Enhanced Visual Design - Hierarchical Architecture Layers
The diagram features an improved layout with enhanced spacing and visual hierarchy:

- **🎨 COUCHE 1: Interface Utilisateur (Blue)**: User interface components and state management
  - Organized in logical groups: Main UI, State Management, Utilities, Styling
- **🌐 COUCHE 2: Application Web (Orange)**: Web application layer and routing
  - Centrally positioned showing Flask app with API and workflow routes
- **⚙️ COUCHE 3: Services Métier (Purple)**: Business logic and core services
  - Grouped into Core Services and Data/Performance Services
- **🔧 COUCHE 4: Configuration (Green)**: System configuration and security
  - Positioned alongside services for logical flow
- **🔄 COUCHE 5: Traitement (Yellow)**: Workflow processing environments and scripts
  - Organized in two rows: Environments and Workflow Scripts
- **💾 COUCHE 6: Données (Pink)**: Data storage and cache systems
  - Vertically arranged to show data flow progression
- **🌍 COUCHE 7: Externe (Light Green)**: External integrations and system resources
  - Positioned at the far right to emphasize external nature

## File Structure

```
architecture-complete-interactive/
├── index.html          # Main HTML structure with controls
├── script.js           # JointJS implementation with interactive features
├── style.css           # Comprehensive styling with theme support
└── README.md           # This documentation
```

## Usage

### Basic Interaction
1. **Open the diagram**: Navigate to `index.html` in a web browser
2. **Show panels**: Click the 🎮 or 📋 toggle buttons to show control/instruction panels
3. **Select components**: Click any component to highlight it
4. **Move components**: Drag selected components to reposition them
5. **Clear selection**: Click on empty space or press `Escape`
6. **Switch themes**: Use the toggle in the top-right corner

### Panel Management
- **Toggle Buttons**: Use 🎮 (controls) and 📋 (instructions) buttons to show/hide panels
- **Close Buttons**: Click the × button in panel headers to hide them
- **Auto-hide**: Panels automatically hide after successful actions
- **Clean Interface**: Panels are hidden by default for a clutter-free experience

### Control Panel Functions
- **🔍 Debug Connexions**: Analyze all connections and components in browser console
- **📱 Sélectionner Frontend**: Automatically select the main UI component
- **⚙️ Sélectionner Service**: Automatically select the WorkflowService
- **🌐 Sélectionner Flask**: Automatically select the Flask application
- **❌ Effacer Sélection**: Clear all selections
- **🔄 Réinitialiser**: Reset view and clear selections

### Keyboard Shortcuts
- **`C`**: Toggle controls panel
- **`I`**: Toggle instructions panel
- **`R`**: Reset diagram view
- **`Escape`**: Clear selection
- **`Ctrl+D`**: Debug connections
- **`?` or `/`**: Show instructions panel
- **`F`**: Select Frontend (Interface Utilisateur)
- **`S`**: Select Service (WorkflowService)
- **`W`**: Select Web (Flask Application)

### Console Commands
Open browser developer tools and use these commands:
```javascript
debugConnections()           // Analyze all connections and architecture layers
selectNode('text')          // Select component containing specified text
clearSelection()            // Clear current selection
resetDiagram()              // Reset view and clear selection
showControlsPanel()         // Show controls panel
hideControlsPanel()         // Hide controls panel
toggleControlsPanel()       // Toggle controls panel
showInfoPanel()             // Show instructions panel
hideInfoPanel()             // Hide instructions panel
toggleInfoPanel()           // Toggle instructions panel
```

## Architecture Structure

The diagram represents the complete system architecture with clear layer separation:

### Frontend Layer (Blue)
- **Interface Utilisateur Web**: Main user interface
- **AppState.js**: Centralized state management
- **DOMBatcher.js**: DOM optimization utilities
- **PerformanceOptimizer.js**: Debouncing and throttling
- **PollingManager.js**: Polling management
- **ErrorHandler.js**: Error handling
- **CSS Modulaire**: Modular CSS architecture

### Flask Application Layer (Orange)
- **app_new.py**: Main Flask application
- **api_routes.py**: 12 system endpoints
- **workflow_routes.py**: 18 workflow endpoints

### Service Layer (Purple)
- **WorkflowService**: Workflow and sequence management
- **MonitoringService**: System monitoring
- **CacheService**: Intelligent TTL caching
- **PerformanceService**: Metrics and profiling
- **AirtableService**: Airtable API integration
- **CSVService**: Download monitoring

### Configuration & Security (Green)
- **config/settings.py**: Centralized configuration
- **config/security.py**: Security and tokens

### Processing Layer (Yellow)
- **Python Environments**: Specialized environments for different steps
- **Workflow Scripts**: Step 1-6 processing scripts

### Data Storage (Pink)
- **projets_extraits/**: Working data
- **Cache système**: Temporary files
- **Destination finale**: Processed archives

### External Systems (Light Green)
- **Airtable API**: External monitoring
- **GPU NVIDIA**: Hardware acceleration
- **Ressources Système**: CPU, RAM, Disk

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
    elementMove: true,        // ✅ Enable component dragging
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
1. Edit component positions and types in `script.js`
2. Adjust layer colors in `style.css`
3. Add new interactive features in the event handlers
4. Test with the debug functions

## Integration

This interactive diagram follows the established project patterns:
- Consistent with other JointJS diagrams in the project
- Uses the same routing improvements and interactive functionality
- Maintains the project's color scheme and design language
- Compatible with the existing documentation portal structure
- Demonstrates the complete system architecture with clear layer separation
