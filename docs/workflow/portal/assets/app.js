// Enhanced Documentation App with Direct Navigation
class EnhancedApp {
    constructor() {
        this.diagramNavigation = null;
    }

    init() {
        console.log('🚀 Initializing enhanced app with direct navigation...');
        this.diagramNavigation = new DiagramNavigation();
        this.setupSearchUI();
    }

    setupSearchUI() {
        const sidebar = document.getElementById('sidebar');
        
        // Only setup search UI if sidebar exists
        if (!sidebar) {
            console.log('Sidebar not found, skipping search UI setup');
            return;
        }
        
        const searchContainer = document.createElement('div');
        searchContainer.className = 'search-container';
        searchContainer.innerHTML = `
            <input type="text" class="search-input" placeholder="Rechercher dans la documentation..." id="search-input">
            <div class="search-results" id="search-results"></div>
        `;
        
        sidebar.insertBefore(searchContainer, sidebar.firstChild);
        
        // Setup search functionality
        this.setupSearch();
    }

    setupSearch() {
        const searchInput = document.getElementById('search-input');
        const searchResults = document.getElementById('search-results');
        
        if (!searchInput || !searchResults) return;
        
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            
            if (query.length < 2) {
                searchResults.innerHTML = '';
                searchResults.style.display = 'none';
                return;
            }
            
            // Simple search implementation
            const results = this.performSearch(query);
            this.displaySearchResults(results, searchResults);
        });
    }

    performSearch(query) {
        // Simple search in page content
        const results = [];
        const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
        
        headings.forEach(heading => {
            if (heading.textContent.toLowerCase().includes(query)) {
                results.push({
                    title: heading.textContent,
                    element: heading
                });
            }
        });
        
        return results.slice(0, 5); // Limit to 5 results
    }

    displaySearchResults(results, container) {
        if (results.length === 0) {
            container.innerHTML = '<div class="search-no-results">Aucun résultat trouvé</div>';
        } else {
            container.innerHTML = results.map(result => 
                `<div class="search-result" onclick="document.getElementById('${result.element.id}')?.scrollIntoView({behavior: 'smooth'})">
                    ${result.title}
                </div>`
            ).join('');
        }
        container.style.display = 'block';
    }
}

// Simple Diagram Navigation
class DiagramNavigation {
    constructor() {
        console.log('🏗️ Creating DiagramNavigation...');
        this.setupComplete = false; // Flag to prevent duplicate setups
        this.init();
    }

    init() {
        console.log('🔧 Initializing DiagramNavigation...');
        this.setupClickableDiagrams();
    }

    setupClickableDiagrams() {
        console.log('🔧 Setting up clickable diagrams for direct navigation...');

        // Check if setup is already complete
        if (this.setupComplete) {
            console.log('⚠️ Setup already complete, skipping to prevent duplicate event listeners');
            return;
        }

        // Find all clickable diagram images
        let clickableImages = document.querySelectorAll('.clickable-diagram-image');
        console.log(`🖼️ Found ${clickableImages.length} clickable diagram images`);

        // If no images found, try to find them by alt text
        if (clickableImages.length === 0) {
            console.warn('⚠️ No .clickable-diagram-image elements found! Checking by alt text...');
            const potentialDiagrams = document.querySelectorAll('img[alt*="Architecture"], img[alt*="Workflow"], img[alt*="Flux"]');
            console.log(`🔍 Found ${potentialDiagrams.length} potential diagram images by alt text`);

            potentialDiagrams.forEach((img, i) => {
                console.log(`📝 Adding classes to potential diagram ${i + 1}: ${img.alt}`);
                img.classList.add('clickable-diagram-image');

                if (img.alt.includes('Architecture')) {
                    img.classList.add('architecture-diagram');
                } else if (img.alt.includes('Workflow') || img.alt.includes('Flux')) {
                    img.classList.add('workflow-execution-diagram');
                }
            });

            // Re-query after adding classes
            clickableImages = document.querySelectorAll('.clickable-diagram-image');
            console.log(`🔄 After adding classes, found ${clickableImages.length} clickable diagram images`);
        }

        // Remove any existing event listeners to prevent duplicates
        clickableImages.forEach((img, index) => {
            // Remove existing click handlers by cloning the element
            if (img.hasAttribute('data-navigation-setup')) {
                console.log(`🧹 Removing existing listeners from image ${index + 1}`);
                const newImg = img.cloneNode(true);
                img.parentNode.replaceChild(newImg, img);
                clickableImages[index] = newImg; // Update reference
            }
        });
        
        clickableImages.forEach((img, index) => {
            console.log(`🔍 Processing clickable image ${index + 1}:`, img);
            
            // Determine which interactive diagram to open
            const interactiveUrl = this.getInteractiveDiagramUrl(img);
            console.log(`  - Interactive URL: ${interactiveUrl || 'none'}`);
            
            if (interactiveUrl) {
                // Add click handler for direct navigation
                const clickHandler = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log(`🎯 Opening interactive diagram in new tab: ${interactiveUrl}`);
                    window.open(interactiveUrl, '_blank');
                };

                img.addEventListener('click', clickHandler);
                img.style.cursor = 'pointer';
                img.title = 'Cliquer pour ouvrir le diagramme interactif dans un nouvel onglet';

                // Mark this image as having navigation setup to prevent duplicates
                img.setAttribute('data-navigation-setup', 'true');

                console.log(`✅ Navigation setup for image ${index + 1}`);
            }
        });

        // Mark setup as complete to prevent duplicate calls
        this.setupComplete = true;
        console.log(`✅ Setup complete: ${clickableImages.length} clickable elements configured for direct navigation`);
    }

    // Helper method to determine which interactive diagram to open
    getInteractiveDiagramUrl(diagramElement) {
        console.log('🔍 Checking for interactive diagram:', diagramElement);
        
        // Check the image source or alt text to determine which interactive diagram to use
        const img = diagramElement.tagName === 'IMG' ? diagramElement : diagramElement.querySelector('img');
        
        // Determine the correct path based on current location
        const currentPath = window.location.pathname;
        let basePath = './';
        
        console.log('📍 Current path:', currentPath);
        
        if (img) {
            const src = img.src || '';
            const alt = img.alt || '';
            
            console.log('🖼️ Image src:', src);
            console.log('🏷️ Image alt:', alt);
            
            // Map static images to consolidated interactive diagrams page
            if (src.includes('Architecture') ||
                alt.includes('Architecture') ||
                img.classList.contains('architecture-diagram')) {
                const url = basePath + 'diagrammes.html#architecture';
                console.log('✅ Matched architecture diagram:', url);
                return url;
            }

            if (src.includes('workflow_execution') ||
                src.includes('Flux') ||
                alt.includes('Flux d\'Exécution') ||
                alt.includes('Workflow Execution') ||
                img.classList.contains('workflow-execution-diagram')) {
                const url = basePath + 'diagrammes.html#workflow';
                console.log('✅ Matched workflow execution diagram:', url);
                return url;
            }
        }
        
        console.log('❌ No interactive diagram match found');
        return null;
    }
}

// Create global app instance
const enhancedApp = new EnhancedApp();

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 DOM ready, initializing enhanced app...');
    enhancedApp.init();
    
    // Setup diagrams with multiple timing attempts
    if (enhancedApp.diagramNavigation) {
        // Additional setup attempts with delays
        [100, 500, 1000].forEach((delay, index) => {
            setTimeout(() => {
                console.log(`📋 Re-setting up diagrams after ${delay}ms (attempt ${index + 2})...`);
                enhancedApp.diagramNavigation.setupClickableDiagrams();
            }, delay);
        });
    }
});

// Also setup when window loads
window.addEventListener('load', () => {
    console.log('🌐 Window loaded, ensuring diagrams are clickable...');
    if (enhancedApp.diagramNavigation) {
        enhancedApp.diagramNavigation.setupClickableDiagrams();
    }
});

// Debug functions for console
window.debugDiagrams = () => {
    console.log('🔍 DIAGRAM DEBUG');
    console.log('================');
    
    const allImages = document.querySelectorAll('img');
    const clickableImages = document.querySelectorAll('.clickable-diagram-image');
    
    console.log(`📊 Statistics:`);
    console.log(`  - Total images: ${allImages.length}`);
    console.log(`  - Clickable images: ${clickableImages.length}`);
    
    console.log(`\n📷 All Images:`);
    allImages.forEach((img, i) => {
        console.log(`  ${i + 1}. ${img.alt || 'No alt text'}`);
        console.log(`     Classes: ${img.className || 'none'}`);
        console.log(`     Clickable: ${img.classList.contains('clickable-diagram-image') ? 'YES' : 'NO'}`);
    });
    
    return { totalImages: allImages.length, clickableImages: clickableImages.length };
};

window.testDiagramClick = () => {
    const firstImage = document.querySelector('.clickable-diagram-image');
    if (firstImage) {
        console.log('🧪 Testing click on first diagram...');
        firstImage.click();
    } else {
        console.log('❌ No clickable diagrams found');
    }
};

window.forceSetupDiagrams = () => {
    console.log('🔧 Forcing diagram setup...');
    if (enhancedApp.diagramNavigation) {
        enhancedApp.diagramNavigation.setupClickableDiagrams();
    }
};
