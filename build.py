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
        self.rides_file = Path('./rides.txt')
        self.routes_dir = Path('./routes')
        self.dist_dir = Path('./dist')
        self.templates_dir = Path('./templates')
        self.routes: List[Dict[str, Any]] = []

    def build(self):
        print("🚴 Building Loudoun Velo Routes Site...\n")
        try:
            self._ensure_directory_exists(self.dist_dir)
            self._load_routes()
            self._process_routes()
            self._generate_files()
            self._copy_assets()
            print("\n✅ Build completed successfully!")
            print(f"📁 Output is in the '{self.dist_dir}' directory.")
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
            print("  - rides.txt not found. Aborting.")
            exit(1)

        with open(self.rides_file, 'r', encoding='utf-8') as file:
            lines = [line.strip() for line in file.readlines() if line.strip() and not line.strip().startswith('#')]
        
        routes_to_process = []
        for line in lines:
            if 'ridewithgps.com' in line:
                parts = [part.strip() for part in line.split(',')]
                url = parts[0]
                specified_type = parts[1].lower() if len(parts) > 1 else None
                if specified_type and specified_type not in ['road', 'gravel']:
                    print(f"    - ⚠️ Invalid route type '{specified_type}' for {url}, defaulting to 'road'.")
                    specified_type = 'road'
                routes_to_process.append({'url': url, 'type': specified_type})
        
        print(f"  Found {len(routes_to_process)} RideWithGPS URLs to process.")

        for i, route_info in enumerate(routes_to_process):
            url = route_info['url']
            specified_type = route_info['type']
            print(f"  ({i+1}/{len(routes_to_process)}) Processing: {url}")
            if specified_type:
                 print(f"    - Type specified as: {specified_type}")
            try:
                route_match = re.search(r'/routes/(\d+)', url)
                if not route_match:
                    print("    - ⚠️ Invalid URL format, skipping.")
                    continue
                
                route_id = route_match.group(1)
                route_data = self._fetch_from_rwgps_json(route_id, specified_type)
                if route_data:
                    self.routes.append(route_data)
                    print(f"    ✓ Added: {route_data['title']}")
                else:
                    print(f"    - ⚠️ Failed to process route {route_id}.")

            except urllib.error.HTTPError as e:
                print(f"    - ❌ HTTP Error {e.code}: Failed to fetch {url}")
            except Exception as e:
                print(f"    - ❌ An unexpected error occurred: {e}")

    def _fetch_from_rwgps_json(self, route_id: str, specified_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        api_url = f"https://ridewithgps.com/routes/{route_id}.json"
        print("    - Fetching data from RideWithGPS...")
        headers = {'User-Agent': 'LoudounVelo-SiteBuilder/1.0', 'Accept': 'application/json'}
        req = urllib.request.Request(api_url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status != 200:
                print(f"      - ⚠️ HTTP Status {response.status}")
                return None
            data = json.loads(response.read().decode('utf-8'))

        route_data = data.get('route', data)
        if not route_data:
            print(f"      - ⚠️ No 'route' object found in JSON for route {route_id}")
            return None

        title = route_data.get('name')
        if not title:
            print(f"      - ⚠️ Title not found for route {route_id}")
            return None

        distance_meters = route_data.get('distance', 0)
        elevation_meters = route_data.get('elevation_gain', 0)
        
        profile = []
        track_points = route_data.get('track_points', [])
        if track_points:
            # 'd' is distance in meters, 'e' is elevation in meters.
            profile = [[p['d'] / 1000, p['e']] for p in track_points if 'd' in p and 'e' in p]
            if len(profile) > 200:
                step = max(1, len(profile) // 200)
                profile = profile[::step]
        else:
             print(f"      - ⚠️ No track points found for profile for route {route_id}")


        return {
            'id': f'route-{route_id}',
            'title': title,
            'description': route_data.get('description', 'A route from RideWithGPS.'),
            'rwgpsUrl': f'https://ridewithgps.com/routes/{route_id}',
            'type': specified_type or 'road', 
            'distance': round(distance_meters / 1000, 1) if distance_meters else 0, # km
            'elevation': round(elevation_meters) if elevation_meters else 0, # meters
            'image': f'https://ridewithgps.com/routes/{route_id}/full.png',
            'profile': profile
        }

    def _process_routes(self):
        print("\n🔄 Processing routes for data consistency...")
        self.routes.sort(key=lambda x: x.get('distance', 0))

    def _generate_files(self):
        print("\n🎨 Generating HTML file...")
        template_path = self.templates_dir / 'index.template.html'
        
        if not template_path.exists():
            print(f"  ⚠️ Template not found at {template_path}. Aborting.")
            exit(1)
            
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        if '{{ROUTES_DATA}}' not in template:
             print(f"  ⚠️ {{ROUTES_DATA}} placeholder not found in template. Aborting.")
             exit(1)
        
        routes_json = json.dumps(self.routes, indent=2)

        html = template.replace('{{SITE_TITLE}}', 'Loudoun Velo - Local Bike Routes')
        html = html.replace('{{ROUTES_DATA}}', routes_json)

        with open(self.dist_dir / 'index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("  ✓ Generated index.html with embedded data.")


    def _copy_assets(self):
        print("\n📋 Copying assets...")
        with open(self.dist_dir / 'CNAME', 'w') as f:
            f.write('loudounvelo.com')
        (self.dist_dir / '.nojekyll').touch()
        print("  ✓ CNAME and .nojekyll files created.")

def main():
    builder = BikeRoutesBuilder()
    builder.build()

if __name__ == '__main__':
    main()