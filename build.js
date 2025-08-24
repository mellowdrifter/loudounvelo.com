const fs = require('fs');
const path = require('path');
const https = require('https');
const { URL } = require('url');

class BikeRoutesBuilder {
    constructor() {
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
        console.log('📖 Loading route files...');

        if (!fs.existsSync(this.routesDir)) {
            console.log(`⚠️  Routes directory not found: ${this.routesDir}`);
            console.log('Creating sample route...');
            this.createSampleRoute();
        }

        const files = fs.readdirSync(this.routesDir)
            .filter(file => file.endsWith('.json'));

        console.log(`Found ${files.length} route files`);

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

            // If distance or elevation is missing, try to fetch from RideWithGPS
            if (!route.distance || !route.elevation) {
                console.log(`  🌐 Fetching data from RideWithGPS...`);
                try {
                    const routeData = await this.fetchRideWithGPSData(route.rwgpsUrl);
                    if (routeData) {
                        route.distance = route.distance || routeData.distance;
                        route.elevation = route.elevation || routeData.elevation;
                        console.log(`  ✓ Fetched: ${route.distance}km, ${route.elevation}m elevation`);
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
                            resolve({
                                distance: Math.round(routeData.route?.distance / 1000 * 10) / 10, // Convert to km
                                elevation: Math.round(routeData.route?.elevation_gain || 0)
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

    createSampleRoute() {
        this.ensureDirectoryExists(this.routesDir);
        
        const sampleRoute = {
            title: "Loudoun County Classic",
            description: "A beautiful ride through Loudoun County's scenic countryside",
            rwgpsUrl: "https://ridewithgps.com/routes/12345",
            type: "road",
            distance: 35.5,
            elevation: 650,
            image: "images/loudoun-classic.jpg"
        };

        fs.writeFileSync(
            path.join(this.routesDir, 'sample-route.json'),
            JSON.stringify(sampleRoute, null, 2)
        );

        console.log('✓ Created sample route file');
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
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
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

        .subtitle {
            color: #666;
            font-size: 1.1rem;
            margin-bottom: 5px;
        }

        .build-info {
            color: #999;
            font-size: 0.9rem;
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

        .filter-group select, .filter-group input {
            padding: 12px;
            border: 2px solid rgba(102, 126, 234, 0.3);
            border-radius: 10px;
            background: white;
            color: #2c3e50;
            font-size: 1rem;
            transition: all 0.3s ease;
        }

        .filter-group select:focus, .filter-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .results-summary {
            text-align: center;
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(102, 126, 234, 0.1);
            border-radius: 10px;
            color: #2c3e50;
            font-weight: bold;
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

        .route-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
            border-color: rgba(102, 126, 234, 0.3);
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
        }

        .stat-value {
            font-weight: bold;
            font-size: 1.1rem;
            color: #667eea;
            display: block;
        }

        .stat-label {
            font-size: 0.8rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
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
            <h1>🚴 Loudoun Velo</h1>
            <div class="subtitle">Local Bike Routes</div>
            <div class="build-info">{{ROUTE_COUNT}} routes • Built: {{BUILD_DATE}}</div>
        </div>
        
        <div class="filters">
            <div class="filter-group">
                <label for="distance-filter">Max Distance (km)</label>
                <input type="number" id="distance-filter" placeholder="Any distance" min="0" max="200" step="5">
            </div>
            
            <div class="filter-group">
                <label for="elevation-filter">Max Elevation (m)</label>
                <input type="number" id="elevation-filter" placeholder="Any elevation" min="0" max="3000" step="100">
            </div>
            
            <div class="filter-group">
                <label for="type-filter">Road Type</label>
                <select id="type-filter">
                    <option value="">All Types</option>
                    <option value="road">Road</option>
                    <option value="gravel">Gravel</option>
                    <option value="mixed">Mixed</option>
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
                        \${route.image ? \`<img src="\${route.image}" alt="\${route.title}" loading="lazy">\` : 'Route Preview'}
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