const fs = require('fs');
const path = require('path');
const https = require('https');

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

        const routes = [];
        for (const line of lines) {
            if (!line.includes('ridewithgps.com')) continue;
            
            const parts = line.split(',').map(p => p.trim());
            const url = parts[0];
            const specifiedType = parts[1]?.toLowerCase();
            
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
                const routeMatch = url.match(/\/routes\/(\d+)/);
                if (!routeMatch) {
                    console.log(`  ⚠️  Invalid URL format, skipping`);
                    continue;
                }

                const routeId = routeMatch[1];
                const cacheFile = path.join(this.routesDir, `route-${routeId}.json`);
                let routeData;

                if (fs.existsSync(cacheFile)) {
                    console.log(`  📄 Loading from cache...`);
                    routeData = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
                    routeData.rwgpsUrl = url;
                    
                    if (specifiedType) {
                        routeData.type = specifiedType;
                        console.log(`  🏷️  Route type overridden to: ${specifiedType}`);
                    }
                } else {
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
                        type: specifiedType || fetchedData.type || 'road',
                        distance: fetchedData.distance,
                        elevation: fetchedData.elevation,
                        image: fetchedData.mapImage
                    };

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
                
                if (!routeData.title || !routeData.rwgpsUrl) {
                    console.log(`⚠️  Skipping ${file}: missing required fields (title, rwgpsUrl)`);
                    continue;
                }

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

            if (!route.distance || !route.elevation || !route.image) {
                console.log(`  🌐 Fetching data from RideWithGPS...`);
                try {
                    const routeData = await this.fetchRideWithGPSData(route.rwgpsUrl);
                    if (routeData) {
                        route.distance = route.distance || routeData.distance;
                        route.elevation = route.elevation || routeData.elevation;
                        route.image = route.image || routeData.mapImage;
                        route.mapImageLarge = routeData.mapImageLarge;
                        
                        console.log(`  ✓ Fetched: ${route.distance || '?'}km, ${route.elevation || '?'}m elevation`);
                        if (routeData.mapImage) {
                            console.log(`  ✓ Map image: ${routeData.mapImage}`);
                        }
                    }
                } catch (error) {
                    console.log(`  ⚠️  Could not fetch data: ${error.message}`);
                }
            }

            route.distance = route.distance || 0;
            route.elevation = route.elevation || 0;
            route.estimatedTime = Math.round(route.distance / 25 * 60);
        }
    }

    async fetchRideWithGPSData(url) {
        return new Promise((resolve, reject) => {
            const match = url.match(/\/routes\/(\d+)/);
            if (!match) {
                reject(new Error('Invalid RideWithGPS URL format'));
                return;
            }

            const routeId = match[1];
            
            this.fetchFromHTML(url, routeId)
                .then(resolve)
                .catch(() => {
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
                res.on('data', (chunk) => { data += chunk; });
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
                res.on('data', (chunk) => { data += chunk; });
                res.on('end', () => {
                    try {
                        if (res.statusCode === 200) {
                            const routeData = JSON.parse(data);
                            const route = routeData.route;
                            
                            resolve({
                                title: route?.name || `Route ${routeId}`,
                                description: route?.description || `Route from RideWithGPS`,
                                type: 'road',
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
                    title = match[1].trim().replace(/\s*\|\s*Ride with GPS$/i, '');
                    break;
                }
            }

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

            let type = 'road';
            const content = html.toLowerCase();
            if (content.includes('gravel') || content.includes('dirt') || content.includes('unpaved')) {
                type = 'gravel';
            } else if (content.includes('mixed') || (content.includes('gravel') && content.includes('road'))) {
                type = 'mixed';
            }

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
                    if (regex.source.includes('miles')) {
                        distance = distance * 1.60934;
                    }
                    if (distance > 500) {
                        distance = distance / 1000;
                    }
                    break;
                }
            }

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
                    if (regex.source.includes('ft')) {
                        elevation = elevation * 0.3048;
                    }
                    break;
                }
            }

            return {
                title: title,
                description: description,
                type: type,
                distance: distance ? Math.round(distance * 10) / 10 : null,
                elevation: elevation ? Math.round(elevation) : null,
                mapImage: `https://ridewithgps.com/routes/${routeId}/thumb.png`,
                mapImageLarge: `https://ridewithgps.com/routes/${routeId}/full.png`
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
            console.log('⚠️  No template found. Please create templates/index.template.html');
            console.log('   You can find the template file in the next artifact.');
            process.exit(1);
        }

        this.routes.sort((a, b) => a.distance - b.distance);
        const routesJson = JSON.stringify(this.routes, null, 2);

        const html = template
            .replace('{{ROUTES_DATA}}', routesJson)
            .replace('{{SITE_TITLE}}', 'Loudoun Velo - Local Bike Routes')
            .replace('{{ROUTE_COUNT}}', this.routes.length)
            .replace('{{BUILD_DATE}}', new Date().toISOString());

        fs.writeFileSync(path.join(this.distDir, 'index.html'), html);
        fs.writeFileSync(path.join(this.distDir, 'routes.json'), routesJson);

        console.log('✓ Generated index.html');
        console.log('✓ Generated routes.json');
    }

    copyAssets() {
        console.log('\n📋 Copying assets...');

        const imagesDir = './images';
        if (fs.existsSync(imagesDir)) {
            const distImagesDir = path.join(this.distDir, 'images');
            this.ensureDirectoryExists(distImagesDir);
            this.copyDirectory(imagesDir, distImagesDir);
            console.log('✓ Copied images');
        }

        fs.writeFileSync(path.join(this.distDir, 'CNAME'), 'loudounvelo.com');
        console.log('✓ Created CNAME file');

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
}

// Run the build
if (require.main === module) {
    const builder = new BikeRoutesBuilder();
    builder.build();
}

module.exports = BikeRoutesBuilder;