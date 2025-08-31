#!/usr/bin/env python3
import os
import json
import re
import urllib.request
import urllib.error
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

class BikeRoutesBuilder:
    def __init__(self):
        self.rides_file = Path('./rides.txt')
        self.routes_dir = Path('./routes')
        self.dist_dir = Path('./dist')
        self.templates_dir = Path('./templates')
        self.template_path = self.templates_dir / 'index.template.html'
        self.routes: List[Dict[str, Any]] = []

    def build(self):
        print("🚴 Building Loudoun Velo Routes Site...\n")
        try:
            self._ensure_directory_exists(self.dist_dir)
            self._load_routes()
            self._process_routes()
            self._generate_html()
            self._copy_assets()
            print("\n✅ Build completed successfully!")
            print(f"📁 Output is in the 'dist' directory.")
            print(f"🌐 Processed {len(self.routes)} routes.")
        except Exception as error:
            print(f"❌ Build failed: {error}")
            exit(1)

    def _ensure_directory_exists(self, directory: Path):
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created directory: {directory}")

    def _load_routes(self):
        print("📖 Loading route definitions...")
        if not self.rides_file.exists():
            print("  ⚠️ rides.txt not found. Please create it with RideWithGPS URLs.")
            return

        with open(self.rides_file, 'r', encoding='utf-8') as file:
            lines = [line.strip() for line in file if line.strip() and not line.strip().startswith('#')]
        
        print(f"  Found {len(lines)} RideWithGPS URLs to process.")
        for i, line in enumerate(lines):
            parts = [part.strip() for part in line.split(',')]
            url = parts[0]
            specified_type = parts[1].lower() if len(parts) > 1 else 'road'
            
            print(f"\n  ({i+1}/{len(lines)}) Processing: {url}")
            
            route_match = re.search(r'/routes/(\d+)', url)
            if not route_match:
                print("    - ⚠️ Invalid URL format, skipping.")
                continue
                
            route_id = route_match.group(1)
            cache_file = self.routes_dir / f'route-{route_id}.json'
            
            route_data = self._fetch_from_rwgps_json(route_id)
            if route_data:
                route_data['type'] = specified_type
                route_data['rwgpsUrl'] = url
                self.routes.append(route_data)
                print(f"    ✓ Added: {route_data['title']}")
            else:
                print(f"    - ❌ Failed to fetch or parse data for route {route_id}")


    def _process_routes(self):
        print("\n🔄 Processing routes for data consistency...")
        # This can be expanded later if needed
        for route in self.routes:
            if 'distance' not in route:
                route['distance'] = 0
            if 'elevation' not in route:
                route['elevation'] = 0
            if 'profile' not in route:
                route['profile'] = []

    def _fetch_from_rwgps_json(self, route_id: str) -> Dict[str, Any] | None:
        api_url = f"https://ridewithgps.com/routes/{route_id}.json"
        headers = {'User-Agent': 'LoudounVelo-SiteBuilder/1.0', 'Accept': 'application/json'}
        
        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    print(f"    - ⚠️ HTTP Error {response.status}")
                    return None
                
                data = json.loads(response.read().decode('utf-8'))
                
                # The API response can have the main object nested under 'route' or be flat
                route_info = data.get('route', data)

                if not route_info or 'name' not in route_info:
                    print("    - ⚠️ Could not find route name in JSON response.")
                    return None

                distance_m = route_info.get('distance', 0)
                elevation_m = route_info.get('elevation_gain', 0)

                profile = []
                if 'track_points' in route_info:
                    profile = [[pt.get('d', 0) / 1000, pt.get('e', 0)] for pt in route_info['track_points']]
                
                # Downsample profile to a reasonable number of points for charting
                if len(profile) > 250:
                    step = len(profile) // 250
                    profile = profile[::step]

                return {
                    'id': f'route-{route_id}',
                    'title': route_info.get('name', f'Route {route_id}'),
                    'distance': round(distance_m / 1000, 1) if distance_m else 0, # km
                    'elevation': round(elevation_m) if elevation_m else 0, # meters
                    'image': f'https://ridewithgps.com/routes/{route_id}/full.png',
                    'profile': profile
                }

        except urllib.error.URLError as e:
            print(f"    - ❌ Network error fetching route: {e}")
            return None
        except json.JSONDecodeError:
            print("    - ❌ Error decoding JSON from API.")
            return None
        except Exception as e:
            print(f"    - ❌ An unexpected error occurred: {e}")
            return None

    def _generate_html(self):
        print("\n🎨 Generating HTML file...")
        if not self.template_path.exists():
            print(f"  ⚠️ Template not found at {self.template_path}. Aborting.")
            exit(1)

        with open(self.template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        if '{{ROUTES_DATA}}' not in template:
            print("  ⚠️ '{{ROUTES_DATA}}' placeholder not found in the template. Aborting.")
            exit(1)

        # Sort routes by distance (shortest to longest) before injecting into template
        self.routes.sort(key=lambda x: x.get('distance', 0) or 0)

        routes_json = json.dumps(self.routes, indent=2)
        html = template.replace('{{ROUTES_DATA}}', routes_json)
        html = html.replace('{{SITE_TITLE}}', 'Loudoun Velo Routes')

        with open(self.dist_dir / 'index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print("  ✓ Generated index.html")

    def _copy_assets(self):
        print("\n📋 Copying assets...")
        with open(self.dist_dir / 'CNAME', 'w') as f:
            f.write('loudounvelo.com')
        (self.dist_dir / '.nojekyll').touch()
        print("  ✓ CNAME and .nojekyll files created.")

if __name__ == '__main__':
    builder = BikeRoutesBuilder()
    builder.build()