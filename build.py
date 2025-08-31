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
                lines = file.readlines()
                
            lines = [
                line.strip() 
                for line in lines 
                if line.strip() and not line.strip().startswith('#')
            ]
        except FileNotFoundError:
            return

        routes_to_process = []
        for line in lines:
            if 'ridewithgps.com' not in line:
                continue
            
            parts = [part.strip() for part in line.split(',')]
            url = parts[0]
            specified_type = parts[1].lower() if len(parts) > 1 else None
            
            route_type = None
            if specified_type:
                if specified_type in ['road', 'gravel']:
                    route_type = specified_type
                else:
                    print(f"  ⚠️  Invalid route type '{specified_type}' for {url}. Use 'road' or 'gravel'")
                    continue
            
            routes_to_process.append({'url': url, 'specified_type': route_type})

        print(f"Found {len(routes_to_process)} RideWithGPS URLs")

        for i, route_info in enumerate(routes_to_process):
            url = route_info['url']
            specified_type = route_info['specified_type']
            
            print(f"\nProcessing route {i + 1}/{len(routes_to_process)}: {url}")
            if specified_type:
                print(f"  Route type: {specified_type}")

            try:
                route_match = re.search(r'/routes/(\d+)', url)
                if not route_match:
                    print("  ⚠️  Invalid URL format, skipping")
                    continue

                route_id = route_match.group(1)
                cache_file = self.routes_dir / f'route-{route_id}.json'
                
                if cache_file.exists():
                    print("  📄 Loading from cache...")
                    with open(cache_file, 'r') as f:
                        route_data = json.load(f)
                    
                    route_data['rwgpsUrl'] = url
                    
                    if specified_type:
                        route_data['type'] = specified_type
                        print(f"  🏷️  Route type overridden to: {specified_type}")
                else:
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
                        'distance': fetched_data.get('distance') or 0,
                        'elevation': fetched_data.get('elevation') or 0,
                        'image': fetched_data.get('mapImage')
                    }

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
        if not self.routes_dir.exists():
            return

        json_files = list(self.routes_dir.glob('*.json'))
        print(f"Found {len(json_files)} route JSON files")

        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    route_data = json.load(f)
                
                if not route_data.get('title') or not route_data.get('rwgpsUrl'):
                    print(f"⚠️  Skipping {json_file}: missing required fields")
                    continue

                route_data['id'] = route_data.get('id') or self._generate_id(route_data['title'])
                route_data['type'] = route_data.get('type', 'road')
                route_data['description'] = route_data.get('description', 'No description available')

                self.routes.append(route_data)
                print(f"✓ Loaded: {route_data['title']}")

            except Exception as error:
                print(f"⚠️  Error loading {json_file}: {error}")

    def _process_routes(self):
        print("\n🔄 Processing routes for missing data...")

        for route in self.routes:
            print(f"Processing: {route['title']}")

            if not route.get('distance') or not route.get('elevation') or not route.get('image'):
                print("  🌐 Fetching data from RideWithGPS...")
                try:
                    route_data = self._fetch_ridewithgps_data(route['rwgpsUrl'])
                    if route_data:
                        route['distance'] = route.get('distance') or route_data.get('distance') or 0
                        route['elevation'] = route.get('elevation') or route_data.get('elevation') or 0
                        route['image'] = route.get('image') or route_data.get('mapImage')
                        route['mapImageLarge'] = route_data.get('mapImageLarge')
                        
                        distance_str = f"{route.get('distance', '?')}km"
                        elevation_str = f"{route.get('elevation', '?')}m"
                        print(f"  ✓ Fetched: {distance_str}, {elevation_str} elevation")
                except Exception as error:
                    print(f"  ⚠️  Could not fetch data: {error}")

            route['distance'] = route.get('distance') or 0
            route['elevation'] = route.get('elevation') or 0

            if route['distance']:
                route['estimatedTime'] = round(route['distance'] / 25 * 60)
            else:
                route['estimatedTime'] = 0

    def _fetch_ridewithgps_data(self, url: str) -> Optional[Dict[str, Any]]:
        route_match = re.search(r'/routes/(\d+)', url)
        if not route_match:
            raise ValueError('Invalid RideWithGPS URL format')

        route_id = route_match.group(1)

        try:
            return self._fetch_from_html(url, route_id)
        except Exception:
            print("    🔄 HTML parsing failed, trying JSON API...")
            return self._fetch_from_json(route_id)

    def _fetch_from_json(self, route_id: str) -> Dict[str, Any]:
        api_url = f"https://ridewithgps.com/routes/{route_id}.json"
        headers = {
            'User-Agent': 'LoudounVelo-SiteBuilder/1.0',
            'Accept': 'application/json'
        }
        
        req = urllib.request.Request(api_url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")
            
            data = json.loads(response.read().decode('utf-8'))
            
            distance = None
            if data.get('distance'):
                distance = round(data['distance'] / 1000, 1)
            
            elevation = None
            if data.get('elevation_gain'):
                elevation = round(data['elevation_gain'])
            
            return {
                'title': data.get('name', f'Route {route_id}'),
                'description': data.get('description', 'Route from RideWithGPS'),
                'type': 'road',
                'distance': distance or 0,
                'elevation': elevation or 0,
                'mapImage': f'https://ridewithgps.com/routes/{route_id}/thumb.png',
                'mapImageLarge': f'https://ridewithgps.com/routes/{route_id}/full.png'
            }

    def _fetch_from_html(self, url: str, route_id: str) -> Dict[str, Any]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; LoudounVelo-SiteBuilder/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")
            html = response.read().decode('utf-8')
            return self._parse_ridewithgps_html(html, route_id)

    def _parse_ridewithgps_html(self, html: str, route_id: str) -> Dict[str, Any]:
        return {}  # simplified: JSON API is preferred

    def _generate_html(self):
        print("\n🎨 Generating HTML...")

        template_path = self.templates_dir / 'index.template.html'
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            print("✓ Using custom template")
        else:
            print("⚠️  No template found. Please create templates/index.template.html")
            exit(1)

        # Debug distances
        print("DEBUG distances:", [r.get("distance") for r in self.routes])

        # ✅ Safe sort
        self.routes.sort(key=lambda x: (x.get('distance') or 0))

        routes_json = json.dumps(self.routes, indent=2)

        html = template.replace('{{ROUTES_DATA}}', routes_json)
        html = html.replace('{{SITE_TITLE}}', 'Loudoun Velo - Local Bike Routes')
        html = html.replace('{{ROUTE_COUNT}}', str(len(self.routes)))
        html = html.replace('{{BUILD_DATE}}', datetime.now().isoformat())

        with open(self.dist_dir / 'index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        with open(self.dist_dir / 'routes.json', 'w', encoding='utf-8') as f:
            f.write(routes_json)

        print("✓ Generated index.html")
        print("✓ Generated routes.json")

    def _copy_assets(self):
        print("\n📋 Copying assets...")

        images_dir = Path('./images')
        if images_dir.exists():
            dist_images_dir = self.dist_dir / 'images'
            if dist_images_dir.exists():
                shutil.rmtree(dist_images_dir)
            shutil.copytree(images_dir, dist_images_dir)
            print("✓ Copied images")

        with open(self.dist_dir / 'CNAME', 'w') as f:
            f.write('loudounvelo.com')
        print("✓ Created CNAME file")

        (self.dist_dir / '.nojekyll').touch()
        print("✓ Created .nojekyll file")

    def _generate_id(self, title: str) -> str:
        return re.sub(r'[^a-z0-9\s]', '', title.lower()).replace(' ', '-').strip()

    def _create_sample_rides_file(self):
        sample_rides = """# Loudoun Velo Bike Routes
# Add RideWithGPS URLs below, one per line
# Format: URL, route_type
# Route types: road, gravel
"""
        with open(self.rides_file, 'w', encoding='utf-8') as f:
            f.write(sample_rides)
        print("✓ Created sample rides.txt file")


def main():
    builder = BikeRoutesBuilder()
    builder.build()


if __name__ == '__main__':
    main()
