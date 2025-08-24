<script>
        const routesData = {{ROUTES_DATA}};
        let filteredRoutes = [...routesData];
        let useMetric = false; // Default to imperial (miles/feet)
        let isDark = false; // Default to light theme

        // Unit conversion functions
        function kmToMiles(km) {
            return Math.round(km * 0.621371 * 10) / 10;
        }

        function milesToKm(miles) {
            return Math.round(miles * 1.60934 * 10) / 10;
        }

        function metersToFeet(meters) {
            return Math.round(meters * 3.28084);
        }

        function feetToMeters(feet) {
            return Math.round(feet * 0.3048);
        }

        function formatDistance(distance) {
            if (!distance) return '?';
            if (useMetric) {
                return distance.toFixed(1);
            } else {
                return kmToMiles(distance).toFixed(1);
            }
        }

        function formatElevation(elevation) {
            if (!elevation) return '?';
            if (useMetric) {
                return elevation.toString();
            } else {
                return metersToFeet(elevation).toString();
            }
        }

        function getDistanceUnit() {
            return useMetric ? 'km' : 'mi';
        }

        function getElevationUnit() {
            return useMetric ? 'm' : 'ft';
        }

        function updateUnitLabels() {
            document.getElementById('distance-unit').textContent = getDistanceUnit();
            document.getElementById('elevation-unit').textContent = getElevationUnit();
            
            const unitToggle = document.getElementById('unit-toggle');
            unitToggle.textContent = useMetric ? 'Km/M' : 'Mi/Ft';
            
            // Update filter placeholders and max values
            const distanceFilter = document.getElementById('distance-filter');
            const elevationFilter = document.getElementById('elevation-filter');
            
            if (useMetric) {
                distanceFilter.max = 200;
                distanceFilter.step = 5;
                distanceFilter.placeholder = 'Any distance';
                elevationFilter.max = 3000;
                elevationFilter.step = 100;
                elevationFilter.placeholder = 'Any elevation';
            } else {
                distanceFilter.max = 125; // ~200km in miles
                distanceFilter.step = 3;
                distanceFilter.placeholder = 'Any distance';
                elevationFilter.max = 10000; // ~3000m in feet
                elevationFilter.step = 250;
                elevationFilter.placeholder = 'Any elevation';
            }
        }

        function toggleTheme() {
            isDark = !isDark;
            document.body.classList.toggle('dark', isDark);
            
            const themeToggle = document.getElementById('theme-toggle');
            themeToggle.textContent = isDark ? '☀️ Light' : '🌙 Dark';
            
            // Save theme preference
            localStorage.setItem('loudounvelo-theme', isDark ? 'dark' : 'light');
        }

        function toggleUnits() {
            useMetric = !useMetric;
            
            // Convert existing filter values
            const distanceFilter = document.getElementById('distance-filter');
            const elevationFilter = document.getElementById('elevation-filter');
            
            if (distanceFilter.value) {
                const currentValue = parseFloat(distanceFilter.value);
                distanceFilter.value = useMetric ? milesToKm(currentValue) : kmToMiles(currentValue);
            }
            
            if (elevationFilter.value) {
                const currentValue = parseFloat(elevationFilter.value);
                elevationFilter.value = useMetric ? feetToMeters(currentValue) : metersToFeet(currentValue);
            }
            
            updateUnitLabels();
            renderRoutes();
            
            // Save unit preference
            localStorage.setItem('loudounvelo-units', useMetric ? 'metric' : 'imperial');
        }

        function renderRoutes() {
            const grid = document.getElementById('routes-grid');
            const summary = document.getElementById('results-summary');
            
            summary.textContent = \`Showing \${filteredRoutes.length} of \${routesData.length} routes\`;

            if (filteredRoutes.length === 0) {
                grid.innerHTML = '<div class="no-results">No routes found matching your criteria</div>';
                return;
            }

            const routesHTML = filteredRoutes.map(route => \`
                <div class="route-card">
                    <div class="route-image">
                        \${route.image ? 
                            \`<img src="\${route.image}" alt="\${route.title} route map" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\"placeholder\\">Route Preview</div>'">\` : 
                            \`<div class="placeholder">Route Preview</div>\`
                        }
                    </div>
                    <div class="route-content">
                        <div class="route-type \${route.type}">\${route.type}</div>
                        <h3 class="route-title">\${route.title}</h3>
                        <div class="route-stats">
                            <div class="stat">
                                <span class="stat-value">\${formatDistance(route.distance)}</span>
                                <span class="stat-label">\${getDistanceUnit()}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-value">\${formatElevation(route.elevation)}</span>
                                <span class="stat-label">\${getElevationUnit()}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-value">\${route.estimatedTime || '?'}</span>
                                <span class="stat-label">est. time (min)</span>
                            </div>
                        </div>
                        <div class="route-description">\${route.description}</div>
                        <a href="\${route.rwgpsUrl}" target="_blank" class="route-link">
                            View on RideWithGPS
                        </a>
                    </div>
                </div>
            \`).join('');

            grid.innerHTML = routesHTML;
        }

        function applyFilters() {
            const maxDistanceInput = parseFloat(document.getElementById('distance-filter').value);
            const maxElevationInput = parseFloat(document.getElementById('elevation-filter').value);
            const selectedType = document.getElementById('type-filter').value;

            // Convert input values to metric for filtering (data is stored in metric)
            let maxDistance = Infinity;
            let maxElevation = Infinity;
            
            if (maxDistanceInput) {
                maxDistance = useMetric ? maxDistanceInput : milesToKm(maxDistanceInput);
            }
            
            if (maxElevationInput) {
                maxElevation = useMetric ? maxElevationInput : feetToMeters(maxElevationInput);
            }

            filteredRoutes = routesData.filter(route => {
                const distanceMatch = !route.distance || route.distance <= maxDistance;
                const elevationMatch = !route.elevation || route.elevation <= maxElevation;
                const typeMatch = !selectedType || route.type === selectedType;

                return distanceMatch && elevationMatch && typeMatch;
            });

            renderRoutes();
        }

        // Load saved preferences
        function loadPreferences() {
            const savedTheme = localStorage.getItem('loudounvelo-theme');
            const savedUnits = localStorage.getItem('loudounvelo-units');
            
            if (savedTheme === 'dark') {
                isDark = true;
                document.body.classList.add('dark');
                document.getElementById('theme-toggle').textContent = '☀️ Light';
            }
            
            if (savedUnits === 'metric') {
                useMetric = true;
            }
            
            updateUnitLabels();
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            loadPreferences();
            renderRoutes();
            
            // Set up event listeners
            ['distance-filter', 'elevation-filter', 'type-filter'].forEach(id => {
                const element = document.getElementById(id);
                element.addEventListener('input', applyFilters);
                element.addEventListener('change', applyFilters);
            });
            
            // Control buttons
            document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
            document.getElementById('unit-toggle').addEventListener('click', toggleUnits);
        });
    const fs = require('fs');
const path = require('path');
const https = require('https');
const { URL } = require('url');

class BikeRoutesBuilder {
    constructor() {
        this.ridesFile = './rides.txt';
        this.routesDir = './routes';
        this.distDir = './dist';
        this.templatesDir = './templates';
        this.routes = [];
    }

    async build() {
        console.log('🚴 Building Loudoun Velo Routes Site...\n');

        try {
            // Create dist directory
            this.ensureDirectoryExists(this.distDir);

            // Load and process routes
            await this.loadRoutes();
            await this.processRoutes();

            // Generate the HTML
            await this.generateHTML();

            // Copy assets
            this.copyAssets();

            console.log('✅ Build completed successfully!');
            console.log(`📁 Output: ${this.distDir}`);
            console.log(`🌐 Routes processed: ${this.routes.length}`);

        } catch (error) {
            console.error('❌ Build failed:', error.message);
            process.exit(1);
        }
    }

    ensureDirectoryExists(dir) {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
            console.log(`📁 Created directory: ${dir}`);
        }
    }

    async loadRoutes() {
        console.log('📖 Loading routes from rides.txt...');

        // Check if rides.txt exists
        if (fs.existsSync(this.ridesFile)) {
            await this.loadRoutesFromFile();
        } else {
            console.log(`⚠️  rides.txt not found, checking routes directory...`);
            await this.loadRoutesFromJSON();
        }

        if (this.routes.length === 0) {
            console.log('Creating sample rides.txt file...');
            this.createSampleRidesFile();
            await this.loadRoutesFromFile();
        }
    }

    async loadRoutesFromFile() {
        const ridesContent = fs.readFileSync(this.ridesFile, 'utf8');
        const lines = ridesContent
            .split('\n')
            .map(line => line.trim())
            .filter(line => line && !line.startsWith('#'));

        // Parse lines - can be either:
        // URL only: https://ridewithgps.com/routes/123456
        // URL with type: https://ridewithgps.com/routes/123456, road
        // URL with type: https://ridewithgps.com/routes/123456, gravel
        const routes = [];
        for (const line of lines) {
            if (!line.includes('ridewithgps.com')) continue;
            
            const parts = line.split(',').map(p => p.trim());
            const url = parts[0];
            const specifiedType = parts[1]?.toLowerCase();
            
            // Validate route type if specified
            let routeType = null;
            if (specifiedType) {
                if (['road', 'gravel'].includes(specifiedType)) {
                    routeType = specifiedType;
                } else {
                    console.log(`  ⚠️  Invalid route type "${specifiedType}" for ${url}. Use "road" or "gravel"`);
                    continue;
                }
            }
            
            routes.push({ url, specifiedType: routeType });
        }

        console.log(`Found ${routes.length} RideWithGPS URLs`);

        for (let i = 0; i < routes.length; i++) {
            const { url, specifiedType } = routes[i];
            console.log(`\nProcessing route ${i + 1}/${routes.length}: ${url}${specifiedType ? ` (${specifiedType})` : ''}`);

            try {
                // Extract route ID for generating a filename
                const routeMatch = url.match(/\/routes\/(\d+)/);
                if (!routeMatch) {
                    console.log(`  ⚠️  Invalid URL format, skipping`);
                    continue;
                }

                const routeId = routeMatch[1];
                
                // Check if we already have this route data cached
                const cacheFile = path.join(this.routesDir, `route-${routeId}.json`);
                let routeData;

                if (fs.existsSync(cacheFile)) {
                    // Load from cache
                    console.log(`  📄 Loading from cache...`);
                    routeData = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
                    routeData.rwgpsUrl = url; // Ensure URL is up to date
                    
                    // Override type if specified in rides.txt
                    if (specifiedType) {
                        routeData.type = specifiedType;
                        console.log(`  🏷️  Route type overridden to: ${specifiedType}`);
                    }
                } else {
                    // Fetch fresh data
                    console.log(`  🌐 Fetching fresh data from RideWithGPS...`);
                    const fetchedData = await this.fetchRideWithGPSData(url);
                    
                    if (!fetchedData || !fetchedData.title) {
                        console.log(`  ⚠️  Could not fetch route data, skipping`);
                        continue;
                    }

                    routeData = {
                        id: `route-${routeId}`,
                        title: fetchedData.title,
                        description: fetchedData.description || `Route from RideWithGPS`,
                        rwgpsUrl: url,
                        type: specifiedType || fetchedData.type || 'road', // Use specified type first
                        distance: fetchedData.distance,
                        elevation: fetchedData.elevation,
                        image: fetchedData.mapImage
                    };

                    // Cache the data
                    this.ensureDirectoryExists(this.routesDir);
                    fs.writeFileSync(cacheFile, JSON.stringify(routeData, null, 2));
                    console.log(`  💾 Cached route data to ${cacheFile}`);
                }

                this.routes.push(routeData);
                console.log(`  ✓ Added: ${routeData.title} (${routeData.distance || '?'}km, ${routeData.elevation || '?'}m, ${routeData.type})`);

            } catch (error) {
                console.log(`  ❌ Error processing ${url}: ${error.message}`);
            }
        }
    }

    async loadRoutesFromJSON() {
        if (!fs.existsSync(this.routesDir)) {
            return;
        }

        const files = fs.readdirSync(this.routesDir)
            .filter(file => file.endsWith('.json'));

        console.log(`Found ${files.length} route JSON files`);

        for (const file of files) {
            try {
                const filePath = path.join(this.routesDir, file);
                const routeData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
                
                // Validate required fields
                if (!routeData.title || !routeData.rwgpsUrl) {
                    console.log(`⚠️  Skipping ${file}: missing required fields (title, rwgpsUrl)`);
                    continue;
                }

                // Set defaults
                routeData.id = routeData.id || this.generateId(routeData.title);
                routeData.type = routeData.type || 'road';
                routeData.description = routeData.description || 'No description available';

                this.routes.push(routeData);
                console.log(`✓ Loaded: ${routeData.title}`);

            } catch (error) {
                console.log(`⚠️  Error loading ${file}: ${error.message}`);
            }
        }
    }

    async processRoutes() {
        console.log('\n🔄 Processing routes for missing data...');

        for (let i = 0; i < this.routes.length; i++) {
            const route = this.routes[i];
            console.log(`Processing: ${route.title}`);

            // If distance, elevation, or image is missing, try to fetch from RideWithGPS
            if (!route.distance || !route.elevation || !route.image) {
                console.log(`  🌐 Fetching data from RideWithGPS...`);
                try {
                    const routeData = await this.fetchRideWithGPSData(route.rwgpsUrl);
                    if (routeData) {
                        route.distance = route.distance || routeData.distance;
                        route.elevation = route.elevation || routeData.elevation;
                        route.image = route.image || routeData.mapImage;
                        route.mapImageLarge = routeData.mapImageLarge; // Store large version for potential future use
                        
                        console.log(`  ✓ Fetched: ${route.distance || '?'}km, ${route.elevation || '?'}m elevation`);
                        if (routeData.mapImage) {
                            console.log(`  ✓ Map image: ${routeData.mapImage}`);
                        }
                    }
                } catch (error) {
                    console.log(`  ⚠️  Could not fetch data: ${error.message}`);
                }
            }

            // Set defaults if still missing
            route.distance = route.distance || 0;
            route.elevation = route.elevation || 0;

            // Add estimated time (rough calculation: 25km/h average)
            route.estimatedTime = Math.round(route.distance / 25 * 60);
        }
    }

    async fetchRideWithGPSData(url) {
        return new Promise((resolve, reject) => {
            // Extract route ID from URL
            const match = url.match(/\/routes\/(\d+)/);
            if (!match) {
                reject(new Error('Invalid RideWithGPS URL format'));
                return;
            }

            const routeId = match[1];
            
            // First try to get data from the HTML page (more reliable)
            this.fetchFromHTML(url, routeId)
                .then(resolve)
                .catch(() => {
                    // Fallback to JSON API
                    console.log(`    🔄 HTML parsing failed, trying JSON API...`);
                    this.fetchFromJSON(routeId)
                        .then(resolve)
                        .catch(reject);
                });
        });
    }

    async fetchFromHTML(url, routeId) {
        return new Promise((resolve, reject) => {
            const options = {
                headers: {
                    'User-Agent': 'Mozilla/5.0 (compatible; LoudounVelo-SiteBuilder/1.0)',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                },
                timeout: 15000
            };

            https.get(url, options, (res) => {
                let data = '';

                res.on('data', (chunk) => {
                    data += chunk;
                });

                res.on('end', () => {
                    try {
                        if (res.statusCode === 200) {
                            const routeData = this.parseRideWithGPSHTML(data, routeId);
                            if (routeData) {
                                resolve(routeData);
                            } else {
                                reject(new Error('Could not parse route data from HTML'));
                            }
                        } else {
                            reject(new Error(`HTTP ${res.statusCode}`));
                        }
                    } catch (error) {
                        reject(error);
                    }
                });
            }).on('error', (error) => {
                reject(error);
            });
        });
    }

    async fetchFromJSON(routeId) {
        return new Promise((resolve, reject) => {
            const apiUrl = `https://ridewithgps.com/routes/${routeId}.json`;

            const options = {
                headers: {
                    'User-Agent': 'LoudounVelo-SiteBuilder/1.0',
                    'Accept': 'application/json'
                },
                timeout: 10000
            };

            https.get(apiUrl, options, (res) => {
                let data = '';

                res.on('data', (chunk) => {
                    data += chunk;
                });

                res.on('end', () => {
                    try {
                        if (res.statusCode === 200) {
                            const routeData = JSON.parse(data);
                            const route = routeData.route;
                            
                            resolve({
                                title: route?.name || `Route ${routeId}`,
                                description: route?.description || `Route from RideWithGPS`,
                                type: 'road', // Default, could be improved with better detection
                                distance: route?.distance ? Math.round(route.distance / 1000 * 10) / 10 : null,
                                elevation: route?.elevation_gain ? Math.round(route.elevation_gain) : null,
                                mapImage: `https://ridewithgps.com/routes/${routeId}/thumb.png`,
                                mapImageLarge: `https://ridewithgps.com/routes/${routeId}/full.png`
                            });
                        } else {
                            reject(new Error(`HTTP ${res.statusCode}`));
                        }
                    } catch (error) {
                        reject(error);
                    }
                });
            }).on('error', (error) => {
                reject(error);
            });
        });
    }

    parseRideWithGPSHTML(html, routeId) {
        try {
            // Extract title
            let title = null;
            const titleMatches = [
                /<title>([^<]+?)\s*\|\s*Ride with GPS<\/title>/i,
                /<h1[^>]*>([^<]+)<\/h1>/i,
                /"name"[\s]*:[\s]*"([^"]+)"/i,
                /class="route-title"[^>]*>([^<]+)</i
            ];

            for (const regex of titleMatches) {
                const match = html.match(regex);
                if (match && match[1].trim()) {
                    title = match[1].trim();
                    // Clean up common suffixes
                    title = title.replace(/\s*\|\s*Ride with GPS$/i, '');
                    break;
                }
            }

            // Extract description
            let description = null;
            const descMatches = [
                /<meta name="description" content="([^"]+)"/i,
                /"description"[\s]*:[\s]*"([^"]+)"/i,
                /class="description"[^>]*>([^<]+)</i
            ];

            for (const regex of descMatches) {
                const match = html.match(regex);
                if (match && match[1].trim()) {
                    description = match[1].trim();
                    break;
                }
            }

            // Try to determine road type from description or tags
            let type = 'road';
            const content = html.toLowerCase();
            if (content.includes('gravel') || content.includes('dirt') || content.includes('unpaved')) {
                type = 'gravel';
            } else if (content.includes('mixed') || (content.includes('gravel') && content.includes('road'))) {
                type = 'mixed';
            }

            // Extract distance (look for various patterns)
            let distance = null;
            const distanceMatches = [
                /distance["\s]*:[\s]*([0-9.]+)/i,
                /([0-9.]+)[\s]*km/i,
                /([0-9.]+)[\s]*miles/i,
                /"distance"[\s]*:[\s]*([0-9.]+)/i,
                /data-distance="([0-9.]+)"/i
            ];

            for (const regex of distanceMatches) {
                const match = html.match(regex);
                if (match) {
                    distance = parseFloat(match[1]);
                    // Convert miles to km if needed
                    if (regex.source.includes('miles')) {
                        distance = distance * 1.60934;
                    }
                    // If distance is in meters, convert to km
                    if (distance > 500) {
                        distance = distance / 1000;
                    }
                    break;
                }
            }

            // Extract elevation gain
            let elevation = null;
            const elevationMatches = [
                /elevation[_\s]*gain["\s]*:[\s]*([0-9.]+)/i,
                /([0-9.]+)[\s]*m[\s]*elevation/i,
                /([0-9,]+)[\s]*ft[\s]*elevation/i,
                /"elevation_gain"[\s]*:[\s]*([0-9.]+)/i,
                /data-elevation-gain="([0-9.]+)"/i
            ];

            for (const regex of elevationMatches) {
                const match = html.match(regex);
                if (match) {
                    elevation = parseFloat(match[1].replace(',', ''));
                    // Convert feet to meters if needed
                    if (regex.source.includes('ft')) {
                        elevation = elevation * 0.3048;
                    }
                    break;
                }
            }

            // Get map image URLs
            const mapImage = `https://ridewithgps.com/routes/${routeId}/thumb.png`;
            const mapImageLarge = `https://ridewithgps.com/routes/${routeId}/full.png`;

            return {
                title: title,
                description: description,
                type: type,
                distance: distance ? Math.round(distance * 10) / 10 : null,
                elevation: elevation ? Math.round(elevation) : null,
                mapImage: mapImage,
                mapImageLarge: mapImageLarge
            };

        } catch (error) {
            console.log(`    ⚠️  HTML parsing error: ${error.message}`);
            return null;
        }
    }

    async generateHTML() {
        console.log('\n🎨 Generating HTML...');

        const templatePath = path.join(this.templatesDir, 'index.template.html');
        let template;

        if (fs.existsSync(templatePath)) {
            template = fs.readFileSync(templatePath, 'utf8');
            console.log('✓ Using custom template');
        } else {
            template = this.getDefaultTemplate();
            console.log('✓ Using default template');
        }

        // Sort routes by distance
        this.routes.sort((a, b) => a.distance - b.distance);

        // Generate routes JSON for the frontend
        const routesJson = JSON.stringify(this.routes, null, 2);

        // Replace placeholders in template
        const html = template
            .replace('{{ROUTES_DATA}}', routesJson)
            .replace('{{SITE_TITLE}}', 'Loudoun Velo - Local Bike Routes')
            .replace('{{ROUTE_COUNT}}', this.routes.length)
            .replace('{{BUILD_DATE}}', new Date().toISOString());

        // Write to dist
        fs.writeFileSync(path.join(this.distDir, 'index.html'), html);
        fs.writeFileSync(path.join(this.distDir, 'routes.json'), routesJson);

        console.log('✓ Generated index.html');
        console.log('✓ Generated routes.json');
    }

    copyAssets() {
        console.log('\n📋 Copying assets...');

        // Copy images if they exist
        const imagesDir = './images';
        if (fs.existsSync(imagesDir)) {
            const distImagesDir = path.join(this.distDir, 'images');
            this.ensureDirectoryExists(distImagesDir);
            this.copyDirectory(imagesDir, distImagesDir);
            console.log('✓ Copied images');
        }

        // Create CNAME file for custom domain
        fs.writeFileSync(path.join(this.distDir, 'CNAME'), 'loudounvelo.com');
        console.log('✓ Created CNAME file');

        // Create .nojekyll to prevent GitHub Pages from processing as Jekyll site
        fs.writeFileSync(path.join(this.distDir, '.nojekyll'), '');
        console.log('✓ Created .nojekyll file');
    }

    copyDirectory(src, dest) {
        const items = fs.readdirSync(src);
        for (const item of items) {
            const srcPath = path.join(src, item);
            const destPath = path.join(dest, item);
            
            if (fs.lstatSync(srcPath).isDirectory()) {
                this.ensureDirectoryExists(destPath);
                this.copyDirectory(srcPath, destPath);
            } else {
                fs.copyFileSync(srcPath, destPath);
            }
        }
    }

    generateId(title) {
        return title.toLowerCase()
            .replace(/[^a-z0-9\s]/g, '')
            .replace(/\s+/g, '-')
            .trim();
    }

    createSampleRidesFile() {
        const sampleRides = `# Loudoun Velo Bike Routes
# Add RideWithGPS URLs below, one per line
# Format: URL, route_type
# Route types: road, gravel
# Lines starting with # are comments and will be ignored
# 
# Example routes (replace with your actual routes):
# https://ridewithgps.com/routes/12345, road
# https://ridewithgps.com/routes/23456, gravel
# https://ridewithgps.com/routes/34567, road

# To add a new route:
# 1. Create or find the route on RideWithGPS
# 2. Copy the URL (like: https://ridewithgps.com/routes/123456)
# 3. Add it as a new line with route type: URL, road  OR  URL, gravel
# 4. Create a pull request or commit the changes
# 5. The build system will automatically extract:
#    - Route title and description
#    - Distance and elevation data  
#    - Map thumbnail image
#    - Use your specified route type

`;

        fs.writeFileSync(this.ridesFile, sampleRides);
        console.log('✓ Created sample rides.txt file');
        console.log('  Add RideWithGPS URLs with route types: URL, road  OR  URL, gravel');
    }

    createSampleRoute() {
        // Keep this for backwards compatibility
        this.createSampleRidesFile();
    }

    getDefaultTemplate() {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{SITE_TITLE}}</title>
    <meta name="description" content="Discover the best bike routes in Loudoun County, Virginia. Filter by distance, elevation, and road type.">
    <meta name="keywords" content="bike routes, cycling, Loudoun County, Virginia, cycling club">
    <link rel="canonical" href="https://loudounvelo.com">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            transition: all 0.3s ease;
        }

        body.dark {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }

        body.dark .container {
            background: rgba(45, 55, 72, 0.95);
            color: #e2e8f0;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
            position: relative;
        }

        .controls {
            position: absolute;
            top: 0;
            right: 0;
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .control-btn {
            padding: 8px 16px;
            border: 2px solid rgba(102, 126, 234, 0.3);
            border-radius: 20px;
            background: white;
            color: #667eea;
            font-size: 0.9rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .control-btn:hover {
            background: #667eea;
            color: white;
            transform: scale(1.05);
        }

        .control-btn.active {
            background: #667eea;
            color: white;
        }

        body.dark .control-btn {
            background: rgba(45, 55, 72, 0.8);
            color: #e2e8f0;
            border-color: rgba(226, 232, 240, 0.3);
        }

        body.dark .control-btn:hover,
        body.dark .control-btn.active {
            background: #4a5568;
            color: #e2e8f0;
        }

        h1 {
            color: #2c3e50;
            font-size: 2.5rem;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }

        body.dark h1 {
            background: linear-gradient(45deg, #a78bfa, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .subtitle {
            color: #666;
            font-size: 1.1rem;
            margin-bottom: 5px;
        }

        body.dark .subtitle {
            color: #a0aec0;
        }

        .build-info {
            color: #999;
            font-size: 0.9rem;
        }

        body.dark .build-info {
            color: #718096;
        }

        .filters {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(102, 126, 234, 0.1);
            border-radius: 15px;
            border: 2px solid rgba(102, 126, 234, 0.2);
            transition: all 0.3s ease;
        }

        body.dark .filters {
            background: rgba(160, 174, 192, 0.1);
            border-color: rgba(160, 174, 192, 0.2);
        }

        .filter-group {
            display: flex;
            flex-direction: column;
        }

        .filter-group label {
            font-weight: bold;
            margin-bottom: 8px;
            color: #2c3e50;
            font-size: 0.9rem;
        }

        body.dark .filter-group label {
            color: #e2e8f0;
        }

        .filter-group select, .filter-group input {
            padding: 12px;
            border: 2px solid rgba(102, 126, 234, 0.3);
            border-radius: 10px;
            background: white;
            color: #2c3e50;
            font-size: 1rem;
            transition: all 0.3s ease;
        }

        body.dark .filter-group select, 
        body.dark .filter-group input {
            background: #4a5568;
            color: #e2e8f0;
            border-color: rgba(160, 174, 192, 0.3);
        }

        .filter-group select:focus, .filter-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        body.dark .filter-group select:focus, 
        body.dark .filter-group input:focus {
            border-color: #a78bfa;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
        }

        .results-summary {
            text-align: center;
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(102, 126, 234, 0.1);
            border-radius: 10px;
            color: #2c3e50;
            font-weight: bold;
            transition: all 0.3s ease;
        }

        body.dark .results-summary {
            background: rgba(160, 174, 192, 0.1);
            color: #e2e8f0;
        }

        .routes-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
            margin-top: 30px;
        }

        .route-card {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            border: 2px solid transparent;
            position: relative;
        }

        body.dark .route-card {
            background: #2d3748;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        }

        .route-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
            border-color: rgba(102, 126, 234, 0.3);
        }

        body.dark .route-card:hover {
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            border-color: rgba(167, 139, 250, 0.3);
        }

        .route-image {
            width: 100%;
            height: 200px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.2rem;
            position: relative;
            overflow: hidden;
        }

        .route-image img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }

        .route-image:hover img {
            transform: scale(1.05);
        }

        .route-image .placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            position: relative;
        }

        .route-image::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="M20,20 Q50,10 80,20 Q90,50 80,80 Q50,90 20,80 Q10,50 20,20" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="2"/><circle cx="30" cy="30" r="3" fill="rgba(255,255,255,0.3)"/><circle cx="70" cy="40" r="2" fill="rgba(255,255,255,0.3)"/><circle cx="60" cy="70" r="2.5" fill="rgba(255,255,255,0.3)"/></svg>') center/cover;
            opacity: 0.3;
        }

        .route-content {
            padding: 20px;
        }

        .route-title {
            font-size: 1.3rem;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        body.dark .route-title {
            color: #e2e8f0;
        }

        .route-title::before {
            content: '🚴';
            font-size: 1.2rem;
        }

        .route-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin: 15px 0;
        }

        .stat {
            text-align: center;
            padding: 10px;
            background: rgba(102, 126, 234, 0.1);
            border-radius: 10px;
            border: 1px solid rgba(102, 126, 234, 0.2);
            transition: all 0.3s ease;
        }

        body.dark .stat {
            background: rgba(160, 174, 192, 0.1);
            border-color: rgba(160, 174, 192, 0.2);
        }

        .stat-value {
            font-weight: bold;
            font-size: 1.1rem;
            color: #667eea;
            display: block;
        }

        body.dark .stat-value {
            color: #a78bfa;
        }

        .stat-label {
            font-size: 0.8rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        body.dark .stat-label {
            color: #a0aec0;
        }

        .route-type {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }

        .route-type.road {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
        }

        .route-type.gravel {
            background: linear-gradient(45deg, #FF9800, #F57C00);
            color: white;
        }

        .route-type.mixed {
            background: linear-gradient(45deg, #9C27B0, #7B1FA2);
            color: white;
        }

        .route-description {
            color: #666;
            margin: 10px 0;
            font-size: 0.9rem;
            line-height: 1.4;
        }

        .route-link {
            display: inline-block;
            width: 100%;
            text-align: center;
            padding: 12px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            text-decoration: none;
            border-radius: 10px;
            font-weight: bold;
            transition: all 0.3s ease;
            margin-top: 10px;
        }

        .route-link:hover {
            transform: scale(1.02);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        }

        .no-results {
            text-align: center;
            padding: 60px 20px;
            color: #666;
            font-size: 1.2rem;
            grid-column: 1 / -1;
        }

        .no-results::before {
            content: '🔍';
            font-size: 3rem;
            display: block;
            margin-bottom: 20px;
        }

        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid rgba(102, 126, 234, 0.1);
            color: #666;
        }

        @media (max-width: 768px) {
            .container {
                padding: 15px;
                margin: 10px;
            }

            .filters {
                grid-template-columns: 1fr;
                gap: 15px;
            }

            .routes-grid {
                grid-template-columns: 1fr;
                gap: 20px;
            }

            h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="controls">
                <button class="control-btn" id="theme-toggle">🌙 Dark</button>
                <button class="control-btn active" id="unit-toggle">Mi/Ft</button>
            </div>
            <h1>🚴 Loudoun Velo</h1>
            <div class="subtitle">Local Bike Routes</div>
            <div class="build-info">{{ROUTE_COUNT}} routes • Built: {{BUILD_DATE}}</div>
        </div>
        
        <div class="filters">
            <div class="filter-group">
                <label for="distance-filter">Max Distance (<span id="distance-unit">mi</span>)</label>
                <input type="number" id="distance-filter" placeholder="Any distance" min="0" max="200" step="5">
            </div>
            
            <div class="filter-group">
                <label for="elevation-filter">Max Elevation (<span id="elevation-unit">ft</span>)</label>
                <input type="number" id="elevation-filter" placeholder="Any elevation" min="0" max="10000" step="100">
            </div>
            
            <div class="filter-group">
                <label for="type-filter">Road Type</label>
                <select id="type-filter">
                    <option value="">All Types</option>
                    <option value="road">Road</option>
                    <option value="gravel">Gravel</option>
                </select>
            </div>
        </div>

        <div class="results-summary" id="results-summary"></div>

        <div id="routes-container">
            <div class="routes-grid" id="routes-grid"></div>
        </div>

        <div class="footer">
            <p>Built with ❤️ for the Loudoun cycling community</p>
        </div>
    </div>

    <script>
        const routesData = {{ROUTES_DATA}};
        let filteredRoutes = [...routesData];

        function renderRoutes() {
            const grid = document.getElementById('routes-grid');
            const summary = document.getElementById('results-summary');
            
            summary.textContent = \`Showing \${filteredRoutes.length} of \${routesData.length} routes\`;

            if (filteredRoutes.length === 0) {
                grid.innerHTML = '<div class="no-results">No routes found matching your criteria</div>';
                return;
            }

            const routesHTML = filteredRoutes.map(route => \`
                <div class="route-card">
                    <div class="route-image">
                        \${route.image ? 
                            \`<img src="\${route.image}" alt="\${route.title} route map" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\"placeholder\\">Route Preview</div>'">\` : 
                            \`<div class="placeholder">Route Preview</div>\`
                        }
                    </div>
                    <div class="route-content">
                        <div class="route-type \${route.type}">\${route.type}</div>
                        <h3 class="route-title">\${route.title}</h3>
                        <div class="route-stats">
                            <div class="stat">
                                <span class="stat-value">\${route.distance ? route.distance.toFixed(1) : '?'}</span>
                                <span class="stat-label">km</span>
                            </div>
                            <div class="stat">
                                <span class="stat-value">\${route.elevation || '?'}</span>
                                <span class="stat-label">elevation (m)</span>
                            </div>
                            <div class="stat">
                                <span class="stat-value">\${route.estimatedTime || '?'}</span>
                                <span class="stat-label">est. time (min)</span>
                            </div>
                        </div>
                        <div class="route-description">\${route.description}</div>
                        <a href="\${route.rwgpsUrl}" target="_blank" class="route-link">
                            View on RideWithGPS
                        </a>
                    </div>
                </div>
            \`).join('');

            grid.innerHTML = routesHTML;
        }

        function applyFilters() {
            const maxDistance = parseFloat(document.getElementById('distance-filter').value) || Infinity;
            const maxElevation = parseFloat(document.getElementById('elevation-filter').value) || Infinity;
            const selectedType = document.getElementById('type-filter').value;

            filteredRoutes = routesData.filter(route => {
                const distanceMatch = !route.distance || route.distance <= maxDistance;
                const elevationMatch = !route.elevation || route.elevation <= maxElevation;
                const typeMatch = !selectedType || route.type === selectedType;

                return distanceMatch && elevationMatch && typeMatch;
            });

            renderRoutes();
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            renderRoutes();
            
            ['distance-filter', 'elevation-filter', 'type-filter'].forEach(id => {
                const element = document.getElementById(id);
                element.addEventListener('input', applyFilters);
                element.addEventListener('change', applyFilters);
            });
        });
    </script>
</body>
</html>`;
    }
}

// Run the build
if (require.main === module) {
    const builder = new BikeRoutesBuilder();
    builder.build();
}

module.exports = BikeRoutesBuilder;