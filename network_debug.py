#!/usr/bin/env python3
"""
Network Debug for RideWithGPS Route Fetching
Tests actual network requests to see what's failing
"""

import urllib.request
import urllib.error
import json
import re
from pathlib import Path


def test_route_url(url):
    """Test fetching data from a RideWithGPS URL"""
    print(f"\n🔍 TESTING ROUTE: {url}")
    print("=" * 60)
    
    # Extract route ID
    route_match = re.search(r'/routes/(\d+)', url)
    if not route_match:
        print("❌ Invalid URL format - no route ID found")
        return False
    
    route_id = route_match.group(1)
    print(f"✅ Route ID extracted: {route_id}")
    
    # Test 1: Try HTML page
    print(f"\n🌐 TEST 1: HTML Page Request")
    print(f"URL: {url}")
    
    success = test_html_request(url, route_id)
    
    if not success:
        # Test 2: Try JSON API
        print(f"\n🌐 TEST 2: JSON API Request")
        api_url = f"https://ridewithgps.com/routes/{route_id}.json"
        print(f"URL: {api_url}")
        test_json_request(api_url, route_id)
    
    return success


def test_html_request(url, route_id):
    """Test HTML page request"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; LoudounVelo-SiteBuilder/1.0)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        print("📤 Making request...")
        
        with urllib.request.urlopen(req, timeout=15) as response:
            status = response.status
            content_type = response.headers.get('content-type', '')
            content_length = response.headers.get('content-length', 'unknown')
            
            print(f"✅ Response received!")
            print(f"   Status: {status}")
            print(f"   Content-Type: {content_type}")
            print(f"   Content-Length: {content_length}")
            
            if status != 200:
                print(f"⚠️  Non-200 status code: {status}")
                return False
            
            # Read content
            html = response.read().decode('utf-8')
            print(f"   HTML length: {len(html)} characters")
            
            # Show first 500 characters
            print(f"\n📖 HTML Sample (first 500 chars):")
            print("-" * 40)
            print(html[:500])
            print("-" * 40)
            
            # Try to parse route data
            print(f"\n🔍 PARSING HTML for route data...")
            route_data = parse_html_for_route_data(html, route_id)
            
            if route_data:
                print("✅ Successfully parsed route data:")
                for key, value in route_data.items():
                    print(f"   {key}: {value}")
                return True
            else:
                print("❌ Could not parse route data from HTML")
                
                # Show where we expect to find data
                print(f"\n🔍 Searching for common patterns...")
                patterns_to_check = [
                    r'<title>([^<]+)</title>',
                    r'"name"[\s]*:[\s]*"([^"]+)"',
                    r'distance["\s]*:[\s]*([0-9.]+)',
                    r'elevation[_\s]*gain["\s]*:[\s]*([0-9.]+)'
                ]
                
                for pattern in patterns_to_check:
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    if matches:
                        print(f"   Found matches for '{pattern}': {matches[:3]}")
                    else:
                        print(f"   No matches for '{pattern}'")
                
                return False
            
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error: {e.code} - {e.reason}")
        if hasattr(e, 'read'):
            error_content = e.read().decode('utf-8', errors='ignore')[:200]
            print(f"   Error content sample: {error_content}")
        return False
        
    except urllib.error.URLError as e:
        print(f"❌ URL Error: {e.reason}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_json_request(api_url, route_id):
    """Test JSON API request"""
    headers = {
        'User-Agent': 'LoudounVelo-SiteBuilder/1.0',
        'Accept': 'application/json'
    }
    
    try:
        req = urllib.request.Request(api_url, headers=headers)
        print("📤 Making JSON API request...")
        
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            content_type = response.headers.get('content-type', '')
            
            print(f"✅ JSON Response received!")
            print(f"   Status: {status}")
            print(f"   Content-Type: {content_type}")
            
            if status != 200:
                print(f"⚠️  Non-200 status code: {status}")
                return False
            
            # Parse JSON
            data = json.loads(response.read().decode('utf-8'))
            print(f"   JSON keys: {list(data.keys())}")
            
            if 'route' in data:
                route = data['route']
                print(f"   Route keys: {list(route.keys())}")
                
                # Extract key fields
                title = route.get('name', f'Route {route_id}')
                distance = route.get('distance')
                elevation = route.get('elevation_gain')
                
                print(f"   Title: {title}")
                print(f"   Distance (raw): {distance}")
                print(f"   Elevation gain (raw): {elevation}")
                
                if distance:
                    distance_km = round(distance / 1000, 1)
                    print(f"   Distance (km): {distance_km}")
                
                if elevation:
                    elevation_m = round(elevation)
                    print(f"   Elevation (m): {elevation_m}")
                
                return True
            else:
                print("❌ No 'route' key in JSON response")
                print(f"   Full response: {json.dumps(data, indent=2)[:500]}...")
                return False
                
    except urllib.error.HTTPError as e:
        print(f"❌ JSON HTTP Error: {e.code} - {e.reason}")
        return False
        
    except urllib.error.URLError as e:
        print(f"❌ JSON URL Error: {e.reason}")
        return False
        
    except Exception as e:
        print(f"❌ JSON parsing error: {e}")
        return False


def parse_html_for_route_data(html, route_id):
    """Parse route data from HTML - simplified version for testing"""
    try:
        # Extract title
        title = None
        title_patterns = [
            r'<title>([^<]+?)\s*\|\s*Ride with GPS</title>',
            r'<h1[^>]*>([^<]+)</h1>',
            r'"name"[\s]*:[\s]*"([^"]+)"'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match and match.group(1).strip():
                title = match.group(1).strip()
                title = re.sub(r'\s*\|\s*Ride with GPS$', '', title, flags=re.IGNORECASE)
                break

        # Extract distance
        distance = None
        distance_patterns = [
            r'distance["\s]*:[\s]*([0-9.]+)',
            r'([0-9.]+)[\s]*km',
            r'"distance"[\s]*:[\s]*([0-9.]+)'
        ]
        
        for pattern in distance_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                distance = float(match.group(1))
                if distance > 500:  # Assume meters, convert to km
                    distance = distance / 1000
                distance = round(distance, 1)
                break

        # Extract elevation gain
        elevation = None
        elevation_patterns = [
            r'elevation[_\s]*gain["\s]*:[\s]*([0-9.]+)',
            r'"elevation_gain"[\s]*:[\s]*([0-9.]+)'
        ]
        
        for pattern in elevation_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                elevation = round(float(match.group(1)))
                break

        if title or distance or elevation:
            return {
                'title': title,
                'distance': distance,
                'elevation': elevation,
                'mapImage': f'https://ridewithgps.com/routes/{route_id}/thumb.png'
            }
        else:
            return None

    except Exception as error:
        print(f"    ⚠️  HTML parsing error: {error}")
        return None


def test_thumbnail_image(route_id):
    """Test if thumbnail image URL works"""
    thumb_url = f'https://ridewithgps.com/routes/{route_id}/thumb.png'
    print(f"\n🖼️  TESTING thumbnail image: {thumb_url}")
    
    try:
        req = urllib.request.Request(thumb_url)
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            content_type = response.headers.get('content-type', '')
            content_length = response.headers.get('content-length', '0')
            
            print(f"✅ Thumbnail accessible!")
            print(f"   Status: {status}")
            print(f"   Content-Type: {content_type}")
            print(f"   Size: {content_length} bytes")
            
            return True
            
    except Exception as e:
        print(f"❌ Thumbnail not accessible: {e}")
        return False


def main():
    """Main debug function"""
    print("🔍 RIDEWITHGPS NETWORK DEBUG TOOL")
    print("=" * 60)
    
    # Load URLs from rides.txt
    rides_file = Path('./rides.txt')
    
    if not rides_file.exists():
        print("❌ rides.txt not found!")
        return
    
    with open(rides_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Filter for RideWithGPS URLs
    urls = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and 'ridewithgps.com' in line:
            # Extract just the URL part (before comma if exists)
            url = line.split(',')[0].strip()
            urls.append(url)
    
    if not urls:
        print("❌ No RideWithGPS URLs found in rides.txt")
        return
    
    print(f"📋 Found {len(urls)} URLs to test")
    
    # Test each URL
    for i, url in enumerate(urls, 1):
        print(f"\n{'='*60}")
        print(f"TESTING URL {i}/{len(urls)}")
        print(f"{'='*60}")
        
        success = test_route_url(url)
        
        if success:
            # Also test thumbnail
            route_match = re.search(r'/routes/(\d+)', url)
            if route_match:
                route_id = route_match.group(1)
                test_thumbnail_image(route_id)
        
        if i < len(urls):
            print(f"\nPress Enter to continue to next URL...")
            input()
    
    print(f"\n🏁 DEBUG COMPLETE")
    print("If all tests passed but your build script still shows 0 routes,")
    print("the issue might be in the template file or JSON generation.")


if __name__ == '__main__':
    main()