#!/usr/bin/env python3
"""
Loudoun Velo Routes Site Builder
Builds a static website from RideWithGPS route URLs
"""

import os
import json
import re
import urllib.request
import urllib.error
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any


class BikeRoutesBuilder:
    def __init__(self):
        self.rides_file = Path('./rides.txt')
        self.routes_dir = Path('./routes')
        self.dist_dir = Path('./dist')
        self.templates_dir = Path('./templates')
        self.routes: List[Dict[str, Any]] = []

    def build(self):
        """Main build process"""
        print("🚴 Building Loudoun Velo Routes Site...\n")
        
        try:
            # Create dist directory
            self._ensure_directory_exists(self.dist_dir)
            
            # Load and process routes
            self._load_routes()
            self._process_routes()
            
            # Generate the HTML
            self._generate_html()
            
            # Copy assets
            self._copy_assets()
            
            print("✅ Build completed successfully!")
            print(f"📁 Output: {self.dist_dir}")
            print(f"🌐 Routes processed: {len(self.routes)}")
            
        except Exception as error:
            print(f"❌ Build failed: {error}")
            exit(1)

    def _ensure_directory_exists(self, directory: Path):
        """Create directory if it doesn't exist"""
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created directory: {directory}")

    def _load_routes(self):
        """Load routes from rides.txt or existing JSON files"""
        print("📖 Loading routes from rides.txt...")
        
        if self.rides_file.exists():
            self._load_routes_from_file()
        else:
            print("⚠️  rides.txt not found, checking routes directory...")
            self._load_routes_from_json()
        
        if not self.routes:
            print("Creating sample rides.txt file...")
            self._create_sample_rides_file()
            self._load_routes_from_file()

    def _load_routes_from_file(self):
        """Load routes from rides.txt file"""
        try:
            with open(self.rides_file, 'r', encoding='utf-8') as file:
                lines = [
                    line.strip() 
                    for line in file.readlines() 
                    if line.strip() and not line.strip().startswith('#')
                ]
        except FileNotFoundError:
            return

        # Parse lines
        routes_to_process = []
        for line in lines:
            if 'ridewithgps.com' not in line:
                continue
            
            parts = [part.strip() for part in line.split(',')]
            url = parts[0]
            specified_type = parts[1].lower() if len(parts) > 1 else None
            
            # Validate route type if specified
            route_type = None
            if specified_type:
                if specified_type in ['road', 'gravel']:
                    route_type = specified_type
                else:
                    print(f"  ⚠️  Invalid route type '{specified_type}' for {url}. Use 'road' or 'gravel'")
                    continue
            
            routes_to_process.append({'url': url, 'specified_type': route_type})

        print(f"Found {len(routes_to_process)} RideWithGPS URLs")

        # Process each route
        for i, route_info in enumerate(routes_to_process):
            url = route_info['url']
            specified_type = route_info['specified_type']
            
            print(f"\nProcessing route {i + 1}/{len(routes_to_process)}: {url}")
            if specified_type:
                print(f"  Route type: {specified_type}")

            try:
                # Extract route ID
                route_match = re.search(r'/routes/(\d+)', url)
                if not route_match:
                    print("  ⚠️  Invalid URL format, skipping")
                    continue

                route_id = route_match.group(1)
                cache_file = self.routes_dir / f'route-{route_id}.json'
                
                # Check cache first
                if cache_file.exists():
                    print("  📄 Loading from cache...")
                    with open(cache_file, 'r') as f:
                        route_data = json.load(f)
                    
                    route_data['rwgpsUrl'] = url  # Ensure URL is up to date
                    
                    # Override type if specified
                    if specified_type:
                        route_data['type'] = specified_type
                        print(f"  🏷️  Route type overridden to: {specified_type}")
                else:
                    # Fetch fresh data
                    print("  🌐 Fetching fresh data from RideWithGPS...")
                    fetched_data = self._fetch_ridewithgps_data(url)
                    
                    if not fetched_data or not fetched_data.get('title'):
                        print("  ⚠️  Could not fetch route data, skipping")
                        continue

                    route_data = {
                        'id': f'route-{route_id}',
                        'title': fetched_data['title'],
                        'description': fetched_data.get('description', 'Route from RideWithGPS'),
                        'rwgpsUrl': url,
                        'type': specified_type or fetched_data.get('type', 'road'),
                        'distance': fetched_data.get('distance'),
                        'elevation': fetched_data.get('elevation'),
                        'image': fetched_data.get('mapImage')
                    }

                    # Cache the data
                    self._ensure_directory_exists(self.routes_dir)
                    with open(cache_file, 'w') as f:
                        json.dump(route_data, f, indent=2)
                    print(f"  💾 Cached route data to {cache_file}")

                self.routes.append(route_data)
                distance_str = f"{route_data.get('distance', '?')}km"
                elevation_str = f"{route_data.get('elevation', '?')}m"
                print(f"  ✓ Added: {route_data['title']} ({distance_str}, {elevation_str}, {route_data['type']})")

            except Exception as error:
                print(f"  ❌ Error processing {url}: {error}")

    def _load_routes_from_json(self):
        """Load existing route JSON files"""
        if not self.routes_dir.exists():
            return

        json_files = list(self.routes_dir.glob('*.json'))
        print(f"Found {len(json_files)} route JSON files")

        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    route_data = json.load(f)
                
                # Validate required fields
                if not route_data.get('title') or not route_data.get('rwgpsUrl'):
                    print(f"⚠️  Skipping {json_file}: missing required fields (title, rwgpsUrl)")
                    continue

                # Set defaults
                route_data['id'] = route_data.get('id') or self._generate_id(route_data['title'])
                route_data['type'] = route_data.get('type', 'road')
                route_data['description'] = route_data.get('description', 'No description available')

                self.routes.append(route_data)
                print(f"✓ Loaded: {route_data['title']}")

            except Exception as error:
                print(f"⚠️  Error loading {json_file}: {error}")

    def _process_routes(self):
        """Process routes to fill in missing data"""
        print("\n🔄 Processing routes for missing data...")

        for route in self.routes:
            print(f"Processing: {route['title']}")

            # If distance, elevation, or image is missing, try to fetch from RideWithGPS
            if not route.get('distance') or not route.get('elevation') or not route.get('image'):
                print("  🌐 Fetching data from RideWithGPS...")
                try:
                    route_data = self._fetch_ridewithgps_data(route['rwgpsUrl'])
                    if route_data:
                        route['distance'] = route.get('distance') or route_data.get('distance')
                        route['elevation'] = route.get('elevation') or route_data.get('elevation')
                        route['image'] = route.get('image') or route_data.get('mapImage')
                        route['mapImageLarge'] = route_data.get('mapImageLarge')
                        
                        distance_str = f"{route.get('distance', '?')}km"
                        elevation_str = f"{route.get('elevation', '?')}m"
                        print(f"  ✓ Fetched: {distance_str}, {elevation_str} elevation")
                        
                        if route_data.get('mapImage'):
                            print(f"  ✓ Map image: {route_data['mapImage']}")
                except Exception as error:
                    print(f"  ⚠️  Could not fetch data: {error}")

            # Set defaults if still missing
            route['distance'] = route.get('distance', 0)
            route['elevation'] = route.get('elevation', 0)

            # Add estimated time (rough calculation: 25km/h average)
            if route['distance']:
                route['estimatedTime'] = round(route['distance'] / 25 * 60)
            else:
                route['estimatedTime'] = 0

    def _fetch_ridewithgps_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch route data from RideWithGPS"""
        # Extract route ID
        route_match = re.search(r'/routes/(\d+)', url)
        if not route_match:
            raise ValueError('Invalid RideWithGPS URL format')

        route_id = route_match.group(1)

        # Try HTML parsing first, then JSON API
        try:
            return self._fetch_from_html(url, route_id)
        except Exception:
            print("    🔄 HTML parsing failed, trying JSON API...")
            return self._fetch_from_json(route_id)

    def _fetch_from_html(self, url: str, route_id: str) -> Dict[str, Any]:
        """Fetch and parse route data from HTML page"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; LoudounVelo-SiteBuilder/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        req = urllib.request.Request(url, headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                
                html = response.read().decode('utf-8')
                return self._parse_ridewithgps_html(html, route_id)
        except urllib.error.URLError as e:
            raise Exception(f"Network error: {e}")

    def _fetch_from_json(self, route_id: str) -> Dict[str, Any]:
        """Fetch route data from JSON API"""
        api_url = f"https://ridewithgps.com/routes/{route_id}.json"
        headers = {
            'User-Agent': 'LoudounVelo-SiteBuilder/1.0',
            'Accept': 'application/json'
        }
        
        req = urllib.request.Request(api_url, headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                
                data = json.loads(response.read().decode('utf-8'))
                route = data.get('route', {})
                
                distance = None
                if route.get('distance'):
                    distance = round(route['distance'] / 1000, 1)  # Convert meters to km
                
                elevation = None
                if route.get('elevation_gain'):
                    elevation = round(route['elevation_gain'])
                
                return {
                    'title': route.get('name', f'Route {route_id}'),
                    'description': route.get('description', 'Route from RideWithGPS'),
                    'type': 'road',  # Default type
                    'distance': distance,
                    'elevation': elevation,
                    'mapImage': f'https://ridewithgps.com/routes/{route_id}/thumb.png',
                    'mapImageLarge': f'https://ridewithgps.com/routes/{route_id}/full.png'
                }
        except urllib.error.URLError as e:
            raise Exception(f"Network error: {e}")

    def _parse_ridewithgps_html(self, html: str, route_id: str) -> Dict[str, Any]:
        """Parse route data from HTML content"""
        try:
            # Extract title
            title = None
            title_patterns = [
                r'<title>([^<]+?)\s*\|\s*Ride with GPS</title>',
                r'<h1[^>]*>([^<]+)</h1>',
                r'"name"[\s]*:[\s]*"([^"]+)"',
                r'class="route-title"[^>]*>([^<]+)'
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match and match.group(1).strip():
                    title = match.group(1).strip()
                    title = re.sub(r'\s*\|\s*Ride with GPS$', '', title, flags=re.IGNORECASE)
                    break

            # Extract description
            description = None
            desc_patterns = [
                r'<meta name="description" content="([^"]+)"',
                r'"description"[\s]*:[\s]*"([^"]+)"',
                r'class="description"[^>]*>([^<]+)'
            ]
            
            for pattern in desc_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match and match.group(1).strip():
                    description = match.group(1).strip()
                    break

            # Determine route type
            route_type = 'road'
            content_lower = html.lower()
            if any(word in content_lower for word in ['gravel', 'dirt', 'unpaved']):
                route_type = 'gravel'
            elif 'mixed' in content_lower or ('gravel' in content_lower and 'road' in content_lower):
                route_type = 'mixed'

            # Extract distance
            distance = None
            distance_patterns = [
                r'distance["\s]*:[\s]*([0-9.]+)',
                r'([0-9.]+)[\s]*km',
                r'([0-9.]+)[\s]*miles',
                r'"distance"[\s]*:[\s]*([0-9.]+)',
                r'data-distance="([0-9.]+)"'
            ]
            
            for pattern in distance_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    distance = float(match.group(1))
                    # Convert miles to km if needed
                    if 'miles' in pattern:
                        distance = distance * 1.60934
                    # If distance is in meters, convert to km
                    if distance > 500:
                        distance = distance / 1000
                    distance = round(distance, 1)
                    break

            # Extract elevation gain
            elevation = None
            elevation_patterns = [
                r'elevation[_\s]*gain["\s]*:[\s]*([0-9.]+)',
                r'([0-9.]+)[\s]*m[\s]*elevation',
                r'([0-9,]+)[\s]*ft[\s]*elevation',
                r'"elevation_gain"[\s]*:[\s]*([0-9.]+)',
                r'data-elevation-gain="([0-9.]+)"'
            ]
            
            for pattern in elevation_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    elevation = float(match.group(1).replace(',', ''))
                    # Convert feet to meters if needed
                    if 'ft' in pattern:
                        elevation = elevation * 0.3048
                    elevation = round(elevation)
                    break

            return {
                'title': title,
                'description': description,
                'type': route_type,
                'distance': distance,
                'elevation': elevation,
                'mapImage': f'https://ridewithgps.com/routes/{route_id}/thumb.png',
                'mapImageLarge': f'https://ridewithgps.com/routes/{route_id}/full.png'
            }

        except Exception as error:
            print(f"    ⚠️  HTML parsing error: {error}")
            return {}

    def _generate_html(self):
        """Generate the HTML file"""
        print("\n🎨 Generating HTML...")

        template_path = self.templates_dir / 'index.template.html'
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            print("✓ Using custom template")
        else:
            print("⚠️  No template found. Please create templates/index.template.html")
            print("   You can find the template file in the HTML template artifact.")
            exit(1)

        # Sort routes by distance
        self.routes.sort(key=lambda x: x.get('distance', 0))

        # Generate routes JSON for the frontend
        routes_json = json.dumps(self.routes, indent=2)

        # Replace placeholders in template
        html = template.replace('{{ROUTES_DATA}}', routes_json)
        html = html.replace('{{SITE_TITLE}}', 'Loudoun Velo - Local Bike Routes')
        html = html.replace('{{ROUTE_COUNT}}', str(len(self.routes)))
        html = html.replace('{{BUILD_DATE}}', datetime.now().isoformat())

        # Write files
        with open(self.dist_dir / 'index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        with open(self.dist_dir / 'routes.json', 'w', encoding='utf-8') as f:
            f.write(routes_json)

        print("✓ Generated index.html")
        print("✓ Generated routes.json")

    def _copy_assets(self):
        """Copy additional assets"""
        print("\n📋 Copying assets...")

        # Copy images if they exist
        images_dir = Path('./images')
        if images_dir.exists():
            dist_images_dir = self.dist_dir / 'images'
            if dist_images_dir.exists():
                shutil.rmtree(dist_images_dir)
            shutil.copytree(images_dir, dist_images_dir)
            print("✓ Copied images")

        # Create CNAME file for custom domain
        with open(self.dist_dir / 'CNAME', 'w') as f:
            f.write('loudounvelo.com')
        print("✓ Created CNAME file")

        # Create .nojekyll to prevent GitHub Pages from processing as Jekyll site
        (self.dist_dir / '.nojekyll').touch()
        print("✓ Created .nojekyll file")

    def _generate_id(self, title: str) -> str:
        """Generate a URL-friendly ID from title"""
        return re.sub(r'[^a-z0-9\s]', '', title.lower()).replace(' ', '-').strip()

    def _create_sample_rides_file(self):
        """Create a sample rides.txt file"""
        sample_rides = """# Loudoun Velo Bike Routes
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

"""
        
        with open(self.rides_file, 'w', encoding='utf-8') as f:
            f.write(sample_rides)
        
        print("✓ Created sample rides.txt file")
        print("  Add RideWithGPS URLs with route types: URL, road  OR  URL, gravel")


def main():
    """Main entry point"""
    builder = BikeRoutesBuilder()
    builder.build()


if __name__ == '__main__':
    main()