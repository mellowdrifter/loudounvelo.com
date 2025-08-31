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
        if self.rides_file.exists():
            self._load_routes_from_file()
        else:
            print("⚠️ rides.txt not found, checking routes directory...")
            self._load_routes_from_json()
        if not self.routes:
            print("Creating sample rides.txt file...")
            self._create_sample_rides_file()
            self._load_routes_from_file()

    def _load_routes_from_file(self):
        try:
            with open(self.rides_file, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
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
                print(f"  ⚠️ Invalid route type '{specified_type}' for {url}")
                continue
            routes_to_process.append({'url': url, 'specified_type': specified_type})

        print(f"Found {len(routes_to_process)} RideWithGPS URLs")
        for i, route_info in enumerate(routes_to_process):
            url = route_info['url']
            specified_type = route_info['specified_type']
            print(f"\nProcessing route {i+1}/{len(routes_to_process)}: {url}")
            if specified_type:
                print(f"  Route type: {specified_type}")
            try:
                route_match = re.search(r'/routes/(\d+)', url)
                if not route_match:
                    print("  ⚠️ Invalid URL format, skipping")
                    continue
                route_id = route_match.group(1)
                cache_file = self.routes_dir / f'route-{route_id}.json'
                if cache_file.exists():
                    with open(cache_file, 'r') as f:
                        route_data = json.load(f)
                else:
                    fetched_data = self._fetch_from_json(route_id)
                    if not fetched_data or not fetched_data.get('title'):
                        print("  ⚠️ Could not fetch route data, skipping")
                        continue
                    route_data = {
                        'id': f'route-{route_id}',
                        'title': fetched_data['title'],
                        'description': fetched_data.get('description', 'Route from RideWithGPS'),
                        'rwgpsUrl': url,
                        'type': specified_type or fetched_data.get('type', 'road'),
                        'distance': fetched_data.get('distance'),
                        'elevation': fetched_data.get('elevation'),
                        'image': fetched_data.get('mapImage'),
                        'profile': fetched_data.get('profile', [])
                    }
                    self._ensure_directory_exists(self.routes_dir)
                    with open(cache_file, 'w') as f:
                        json.dump(route_data, f, indent=2)
                if specified_type:
                    route_data['type'] = specified_type
                self.routes.append(route_data)
                print(f"  ✓ Added: {route_data['title']}")
            except Exception as error:
                print(f"  ❌ Error processing {url}: {error}")

    def _load_routes_from_json(self):
        if not self.routes_dir.exists():
            return
        for json_file in self.routes_dir.glob('*.json'):
            try:
                with open(json_file, 'r') as f:
                    route_data = json.load(f)
                if not route_data.get('title') or not route_data.get('rwgpsUrl'):
                    continue
                self.routes.append(route_data)
            except Exception as error:
                print(f"⚠️ Error loading {json_file}: {error}")

    def _process_routes(self):
        print("\n🔄 Processing routes for missing data...")
        for route in self.routes:
            if not route.get('profile'):
                try:
                    route_id = re.search(r'/routes/(\d+)', route['rwgpsUrl']).group(1)
                    fetched_data = self._fetch_from_json(route_id)
                    if fetched_data and fetched_data.get('profile'):
                        route['profile'] = fetched_data['profile']
                except Exception as error:
                    print(f"  ⚠️ Could not fetch profile: {error}")
            route['distance'] = route.get('distance', 0)
            route['elevation'] = route.get('elevation', 0)

    def _fetch_from_json(self, route_id: str) -> Dict[str, Any]:
        api_url = f"https://ridewithgps.com/routes/{route_id}.json"
        headers = {'User-Agent': 'LoudounVelo-SiteBuilder/1.0','Accept': 'application/json'}
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")
            data = json.loads(response.read().decode('utf-8'))
            route = data.get('route', {})
            distance = round(route['distance'] / 1000, 1) if route.get('distance') else None
            elevation = round(route['elevation_gain']) if route.get('elevation_gain') else None

            # build profile
            profile = []
            if 'track' in data and 'points' in data['track']:
                points = data['track']['points']
                dist = 0.0
                last = None
                for pt in points:
                    if 'x' in pt and 'y' in pt:
                        if last:
                            dx = ((pt['x'] - last['x'])**2 + (pt['y'] - last['y'])**2) ** 0.5
                            dist += dx * 111.32
                        profile.append([round(dist, 2), pt.get('elevation', 0)])
                        last = pt
                # downsample
                if len(profile) > 200:
                    step = len(profile)//200
                    profile = profile[::step]

            return {
                'title': route.get('name', f'Route {route_id}'),
                'description': route.get('description', 'Route from RideWithGPS'),
                'type': 'road',
                'distance': distance,
                'elevation': elevation,
                'mapImage': f'https://ridewithgps.com/routes/{route_id}/thumb.png',
                'mapImageLarge': f'https://ridewithgps.com/routes/{route_id}/full.png',
                'profile': profile
            }

    def _generate_html(self):
        print("\n🎨 Generating HTML...")
        template_path = self.templates_dir / 'index.template.html'
        if not template_path.exists():
            print("⚠️ Missing template")
            exit(1)
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        self.routes.sort(key=lambda x: x.get('distance') or 0)
        routes_json = json.dumps(self.routes, indent=2)
        html = template.replace('{{ROUTES_DATA}}', routes_json)
        html = html.replace('{{SITE_TITLE}}', 'Loudoun Velo - Local Bike Routes')
        html = html.replace('{{ROUTE_COUNT}}', str(len(self.routes)))
        html = html.replace('{{BUILD_DATE}}', datetime.now().isoformat())
        with open(self.dist_dir / 'index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        with open(self.dist_dir / 'routes.json', 'w', encoding='utf-8') as f:
            f.write(routes_json)
        print("✓ Generated index.html and routes.json")

    def _copy_assets(self):
        print("\n📋 Copying assets...")
        images_dir = Path('./images')
        if images_dir.exists():
            dist_images_dir = self.dist_dir / 'images'
            if dist_images_dir.exists():
                shutil.rmtree(dist_images_dir)
            shutil.copytree(images_dir, dist_images_dir)
        with open(self.dist_dir / 'CNAME', 'w') as f:
            f.write('loudounvelo.com')
        (self.dist_dir / '.nojekyll').touch()


def main():
    builder = BikeRoutesBuilder()
    builder.build()


if __name__ == '__main__':
    main()
