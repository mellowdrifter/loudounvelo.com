import os
import json
import re
import urllib.request
import urllib.error
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from PIL import Image

class BikeRoutesBuilder:
    def __init__(self):
        self.rides_file = Path('./rides.txt')
        self.routes_dir = Path('./routes')
        self.dist_dir = Path('./dist')
        self.images_dir = Path('./images')
        self.dist_images_dir = self.dist_dir / 'images'
        self.templates_dir = Path('./templates')
        self.routes: List[Dict[str, Any]] = []

    def build(self):
        print("🚴 Building Loudoun Velo Routes Site...\n")
        try:
            self._ensure_directory_exists(self.dist_dir)
            self._ensure_directory_exists(self.dist_images_dir)
            self._load_routes()
            self._process_routes()
            self._generate_html()
            self._copy_assets()
            print("✅ Build completed successfully!")
            print(f"📁 Output: {self.dist_dir}")
            print(f"🌐 Routes processed: {len(self.routes)}")
        except Exception as error:
            print(f"❌ Build failed: {error}")
            exit(1)

    def _ensure_directory_exists(self, directory: Path):
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created directory: {directory}")

    def _load_routes(self):
        print("📖 Loading routes from rides.txt...")
        if not self.rides_file.exists():
            print("⚠️ rides.txt not found. Aborting.")
            exit(1)

        with open(self.rides_file, 'r', encoding='utf-8') as file:
            lines = [line.strip() for line in file if line.strip() and not line.strip().startswith('#')]

        print(f"  Found {len(lines)} RideWithGPS URLs to process.")
        processed_route_ids = set()

        for i, line in enumerate(lines):
            parts = [part.strip() for part in line.split(',')]
            url = parts[0]
            specified_type = parts[1].lower() if len(parts) > 1 else 'road'

            print(f"\n  ({i+1}/{len(lines)}) Processing: {url}")

            try:
                route_match = re.search(r'/routes/(\d+)', url)
                if not route_match:
                    print("    ⚠️ Invalid URL format, skipping.")
                    continue
                
                route_id = route_match.group(1)
                if route_id in processed_route_ids:
                    print(f"    ⚠️ Duplicate route ID {route_id} found, skipping.")
                    continue
                
                processed_route_ids.add(route_id)
                cache_file = self.routes_dir / f'route-{route_id}.json'

                if cache_file.exists():
                    with open(cache_file, 'r') as f:
                        route_data = json.load(f)
                    print("    - Loaded from cache.")
                else:
                    print("    - Fetching data from RideWithGPS...")
                    fetched_data = self._fetch_from_rwgps_json(route_id)
                    if not fetched_data:
                        print("    ❌ Could not fetch valid route data, skipping.")
                        continue
                    
                    route_data = {
                        'id': f'route-{route_id}',
                        'rwgpsUrl': url,
                        **fetched_data
                    }
                    self._ensure_directory_exists(self.routes_dir)
                    with open(cache_file, 'w') as f:
                        json.dump(route_data, f, indent=2)
                    print("    - Data fetched and cached.")

                route_data['type'] = specified_type
                self.routes.append(route_data)
                print(f"    ✓ Added: {route_data.get('title', 'Untitled Route')}")

            except Exception as error:
                print(f"    ❌ Error processing {url}: {error}")

    def _fetch_from_rwgps_json(self, route_id: str) -> Dict[str, Any]:
        api_url = f"https://ridewithgps.com/routes/{route_id}.json"
        headers = {'User-Agent': 'LoudounVelo-SiteBuilder/1.0', 'Accept': 'application/json'}
        req = urllib.request.Request(api_url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")
            data = json.loads(response.read().decode('utf-8'))

        # The API can return the main object inside a 'route' key or at the top level
        route_info = data.get('route', data)

        if not route_info.get('name'):
            return {}

        distance_km = round(route_info.get('distance', 0) / 1000, 1)
        elevation_m = round(route_info.get('elevation_gain', 0))
        
        # Download and convert image
        image_url = f"https://ridewithgps.com/routes/{route_id}/full.png"
        image_path = self.dist_images_dir / f'route-{route_id}.webp'
        
        if not image_path.exists():
            try:
                with urllib.request.urlopen(urllib.request.Request(image_url, headers=headers), timeout=20) as img_response:
                    img_data = img_response.read()
                    with Image.open(urllib.request.urlopen(image_url)) as img:
                        img.save(image_path, 'webp', quality=85)
                print(f"    - Image downloaded and converted to WebP.")
            except Exception as e:
                print(f"    ⚠️ Could not download or convert image: {e}")

        profile = []
        if 'track_points' in route_info:
            profile = [[p['d'] / 1000, p['e']] for p in route_info['track_points']]
        
        return {
            'title': route_info.get('name', f'Route {route_id}'),
            'distance': distance_km,
            'elevation': elevation_m,
            'image': f"images/route-{route_id}.webp",
            'profile': profile
        }

    def _process_routes(self):
        print("\n🔄 Processing routes for data consistency...")
        # Placeholder for any future processing steps
        pass

    def _generate_html(self):
        print("\n🎨 Generating HTML file...")
        template_path = self.templates_dir / 'index.template.html'
        if not template_path.exists():
            print(f"⚠️ Template not found at {template_path}. Aborting.")
            exit(1)
            
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        if '{{ROUTES_DATA}}' not in template:
            print("⚠️ '{{ROUTES_DATA}}' placeholder not found in the template. Aborting.")
            exit(1)

        self.routes.sort(key=lambda x: x.get('distance', 0))
        
        routes_json = json.dumps(self.routes, indent=2)
        html = template.replace('{{ROUTES_DATA}}', routes_json)
        html = html.replace('{{SITE_TITLE}}', 'Loudoun Velo - Local Bike Routes')
        html = html.replace('{{PRELOAD_LINKS}}', '') # Ensure placeholder is removed

        with open(self.dist_dir / 'index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("  ✓ Generated index.html")

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

