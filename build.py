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
        
        urls_to_process = [line.split(',')[0].strip() for line in lines if 'ridewithgps.com' in line]
        print(f"  Found {len(urls_to_process)} RideWithGPS URLs to process.")

        for i, url in enumerate(urls_to_process):
            print(f"  ({i+1}/{len(urls_to_process)}) Processing: {url}")
            try:
                route_match = re.search(r'/routes/(\d+)', url)
                if not route_match:
                    print("    - ⚠️ Invalid URL format, skipping.")
                    continue
                
                route_id = route_match.group(1)
                route_data = self._fetch_from_rwgps_json(route_id)
                if route_data:
                    self.routes.append(route_data)
                    print(f"    ✓ Added: {route_data['title']}")
                else:
                    print(f"    - ⚠️ Failed to process route {route_id}.")

            except urllib.error.HTTPError as e:
                print(f"    - ❌ HTTP Error {e.code}: Failed to fetch {url}")
            except Exception as e:
                print(f"    - ❌ An unexpected error occurred: {e}")

    def _fetch_from_rwgps_json(self, route_id: str) -> Optional[Dict[str, Any]]:
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
        
        # Use the direct image URL for the elevation profile as you discovered.
        profile_image_url = f"https://ridewithgps.com/routes/{route_id}/elevation_profile.png?width=600&height=120&unit_type=metric"


        return {
            'id': f'route-{route_id}',
            'title': title,
            'description': route_data.get('description', 'A route from RideWithGPS.'),
            'rwgpsUrl': f'https://ridewithgps.com/routes/{route_id}',
            'type': 'road', 
            'distance': round(distance_meters / 1000, 1) if distance_meters else 0, # km
            'elevation': round(elevation_meters) if elevation_meters else 0, # meters
            'image': f'https://ridewithgps.com/routes/{route_id}/full.png',
            'profileImage': profile_image_url
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

        if '{{SITE_TITLE}}' not in template:
             print(f"  ⚠️ {{SITE_TITLE}} placeholder not found in template. Aborting.")
             exit(1)

        html = template.replace('{{SITE_TITLE}}', 'Loudoun Velo - Local Bike Routes')

        with open(self.dist_dir / 'index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("  ✓ Generated index.html")

        routes_json = json.dumps(self.routes, indent=2)
        with open(self.dist_dir / 'routes.json', 'w', encoding='utf-8') as f:
            f.write(routes_json)
        print("  ✓ Generated routes.json")

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
