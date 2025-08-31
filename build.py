#!/usr/bin/env python3
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
        # Configuration for file paths
        self.rides_file = Path('./rides.txt')
        self.routes_dir = Path('./routes')
        self.dist_dir = Path('./dist')
        self.templates_dir = Path('./templates') 
        self.routes: List[Dict[str, Any]] = []

    def build(self):
        """Main build process orchestrator."""
        print("🚴 Building Loudoun Velo Routes Site...\n")
        try:
            self._ensure_directory_exists(self.dist_dir)
            self._load_routes()
            self._process_routes()
            self._generate_html()
            self._copy_assets()
            print("\n✅ Build completed successfully!")
            print(f"📁 Output is in the '{self.dist_dir}' directory.")
            print(f"🌐 Processed {len(self.routes)} routes.")
        except Exception as error:
            print(f"❌ Build failed: {error}")
            exit(1)

    def _ensure_directory_exists(self, directory: Path):
        """Creates a directory if it doesn't exist."""
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created directory: {directory}")

    def _load_routes(self):
        """Loads routes from either rides.txt or cached JSON files."""
        print("📖 Loading route definitions...")
        if self.rides_file.exists():
            self._load_routes_from_file()
        else:
            print("  ⚠️ rides.txt not found, checking for existing route JSON files...")
            self._load_routes_from_json()

        if not self.routes:
            print("  ⚠️ No routes found. Creating a sample rides.txt file.")
            self._create_sample_rides_file()
            self._load_routes_from_file()

    def _load_routes_from_file(self):
        """Parses rides.txt, fetches data from RideWithGPS, and caches it."""
        try:
            with open(self.rides_file, 'r', encoding='utf-8') as file:
                lines = [line.strip() for line in file if line.strip() and not line.strip().startswith('#')]
        except FileNotFoundError:
            return

        routes_to_process = []
        for line in lines:
            if 'ridewithgps.com' not in line:
                continue
            parts = [part.strip() for part in line.split(',')]
            url = parts[0]
            specified_type = parts[1].lower() if len(parts) > 1 else None
            if specified_type and specified_type not in ['road', 'gravel']:
                print(f"  ⚠️ Invalid route type '{specified_type}' for {url}. Skipping.")
                continue
            routes_to_process.append({'url': url, 'specified_type': specified_type})

        print(f"  Found {len(routes_to_process)} RideWithGPS URLs to process.")
        for i, route_info in enumerate(routes_to_process):
            url = route_info['url']
            specified_type = route_info['specified_type']
            print(f"\n  ({i+1}/{len(routes_to_process)}) Processing: {url}")
            
            try:
                route_match = re.search(r'/routes/(\d+)', url)
                if not route_match:
                    print("    ⚠️ Invalid URL format, skipping.")
                    continue
                
                route_id = route_match.group(1)
                cache_file = self.routes_dir / f'route-{route_id}.json'

                if cache_file.exists():
                    print("    - Found cached data.")
                    with open(cache_file, 'r') as f:
                        route_data = json.load(f)
                else:
                    print("    - Fetching data from RideWithGPS...")
                    fetched_data = self._fetch_from_rwgps_json(route_id)
                    if not fetched_data:
                        print("    ⚠️ Fetch returned no data, skipping.")
                        continue
                    
                    route_data = {
                        'id': f'route-{route_id}',
                        'title': fetched_data['title'],
                        'description': fetched_data.get('description', 'A scenic route from RideWithGPS.'),
                        'rwgpsUrl': url,
                        'type': specified_type or fetched_data.get('type', 'road'),
                        'distance': fetched_data.get('distance'),
                        'elevation': fetched_data.get('elevation'),
                        'image': fetched_data.get('mapImageLarge', fetched_data.get('mapImage')),
                    }
                    self._ensure_directory_exists(self.routes_dir)
                    with open(cache_file, 'w') as f:
                        json.dump(route_data, f, indent=2)
                    print("    - Data fetched and cached.")

                if specified_type and route_data.get('type') != specified_type:
                    route_data['type'] = specified_type
                    print(f"    - Overriding type to '{specified_type}'.")

                self.routes.append(route_data)
                print(f"    ✓ Added: {route_data['title']}")

            except Exception as error:
                print(f"    ❌ Error processing {url}: {error}")

    def _load_routes_from_json(self):
        """Loads route data directly from JSON files in the routes directory."""
        if not self.routes_dir.exists():
            return
        json_files = list(self.routes_dir.glob('*.json'))
        print(f"  Found {len(json_files)} cached route files.")
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    route_data = json.load(f)
                if route_data.get('title') and route_data.get('rwgpsUrl'):
                    self.routes.append(route_data)
                else:
                    print(f"  ⚠️ Skipping invalid cache file: {json_file}")
            except Exception as error:
                print(f"  ⚠️ Error loading {json_file}: {error}")

    def _process_routes(self):
        """Ensures all routes have placeholder data for distance/elevation if missing."""
        print("\n🔄 Processing routes for data consistency...")
        for route in self.routes:
            route['distance'] = route.get('distance', 0)
            route['elevation'] = route.get('elevation', 0)

    def _fetch_from_rwgps_json(self, route_id: str) -> Optional[Dict[str, Any]]:
        """Fetches and processes JSON data for a single route from RideWithGPS."""
        api_url = f"https://ridewithgps.com/routes/{route_id}.json"
        headers = {'User-Agent': 'LoudounVelo-SiteBuilder/1.0', 'Accept': 'application/json'}
        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                if response.status != 200:
                    print(f"    - Received HTTP {response.status} from API. Skipping.")
                    return None
                data = json.loads(response.read().decode('utf-8'))
                
                details = data.get('route', data)

                title = details.get('name')
                if not title:
                    print(f"    ⚠️ Could not find 'name' in route data for ID {route_id}. Using fallback title.")
                    title = f'Route {route_id}'

                distance_m = details.get('distance', 0)
                elevation_m_gain = details.get('elevation_gain', 0)
                
                distance_km = round(distance_m / 1000, 1) if distance_m else 0
                elevation_m = round(elevation_m_gain) if elevation_m_gain else 0

                return {
                    'title': title,
                    'description': details.get('description', 'A scenic route from RideWithGPS.'),
                    'type': 'road', # Default type
                    'distance': distance_km,
                    'elevation': elevation_m,
                    'mapImage': f'https://ridewithgps.com/routes/{route_id}/thumb.png',
                    'mapImageLarge': f'https://ridewithgps.com/routes/{route_id}/full.png'
                }
        except urllib.error.URLError as e:
            print(f"    - URL Error fetching {api_url}: {e.reason}")
            return None
        except Exception as e:
            print(f"    - Unexpected error fetching {api_url}: {e}")
            return None

    def _generate_html(self):
        """Generates the final HTML file from the template and route data."""
        print("\n🎨 Generating HTML file...")
        template_path = self.templates_dir / 'index.template.html'
        if not template_path.exists():
            print(f"  ❌ CRITICAL: Template not found at {template_path}. Aborting.")
            exit(1)
            
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        if '{{ROUTES_DATA}}' not in template:
            print(f"  ❌ CRITICAL: '{{ROUTES_DATA}}' placeholder not found in {template_path}. Cannot inject route data.")
            exit(1)

        self.routes.sort(key=lambda x: x.get('distance') or 0)
        
        routes_json = json.dumps(self.routes, indent=2)
        
        html = template.replace('{{ROUTES_DATA}}', routes_json)
        html = html.replace('{{SITE_TITLE}}', 'Loudoun Velo - Local Bike Routes')
        
        with open(self.dist_dir / 'index.html', 'w', encoding='utf-8') as f:
            f.write(html)
            
        print(f"  ✓ Generated index.html, injecting data for {len(self.routes)} routes.")

    def _copy_assets(self):
        """Copies necessary static assets to the dist directory."""
        print("\n📋 Copying assets...")
        with open(self.dist_dir / 'CNAME', 'w') as f:
            f.write('loudounvelo.com')
        (self.dist_dir / '.nojekyll').touch()
        print("  ✓ CNAME and .nojekyll files created.")

    def _create_sample_rides_file(self):
        """Creates a sample rides.txt to get the user started."""
        sample_content = (
            "# Welcome to Loudoun Velo Routes!\n"
            "# Add your RideWithGPS route URLs below.\n"
            "# You can optionally specify a type (road or gravel) after a comma.\n\n"
            "https://ridewithgps.com/routes/42639454, road\n"
            "https://ridewithgps.com/routes/51848673, road\n"
        )
        with open(self.rides_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)


if __name__ == '__main__':
    builder = BikeRoutesBuilder()
    builder.build()