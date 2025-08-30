#!/usr/bin/env python3
"""
Debug version of Loudoun Velo Routes Site Builder
Adds extra debugging to identify why no routes are created
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


def debug_rides_file():
    """Debug the rides.txt file"""
    print("🔍 DEBUGGING rides.txt file...")
    
    rides_file = Path('./rides.txt')
    
    if not rides_file.exists():
        print("❌ rides.txt file does not exist!")
        print("📍 Current working directory:", os.getcwd())
        print("📁 Files in current directory:", list(Path('.').iterdir()))
        return []
    
    print("✅ rides.txt file exists")
    
    try:
        with open(rides_file, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Re-open to get lines properly
        with open(rides_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            
    except Exception as e:
        print(f"❌ Error reading rides.txt: {e}")
        return []
    
    print(f"📄 File size: {len(content)} characters")
    print(f"📝 Total lines: {len(lines)}")
    
    # Show first few lines for debugging
    print("\n📖 File contents (first 10 lines):")
    for i, line in enumerate(lines[:10], 1):
        print(f"  {i:2d}: {repr(line)}")
    
    if len(lines) > 10:
        print(f"  ... ({len(lines) - 10} more lines)")
        print("\n📖 Last few lines:")
        for i, line in enumerate(lines[-5:], len(lines)-4):
            print(f"  {i:2d}: {repr(line)}")
    
    # Process lines like the original script
    processed_lines = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        print(f"\n🔍 Line {i}: {repr(stripped)}")
        
        if not stripped:
            print("  ⏭️  Empty line, skipping")
            continue
            
        if stripped.startswith('#'):
            print("  ⏭️  Comment line, skipping")
            continue
            
        if 'ridewithgps.com' not in stripped:
            print("  ⚠️  No RideWithGPS URL found, skipping")
            continue
            
        print("  ✅ Valid RideWithGPS line found")
        processed_lines.append(stripped)
    
    print(f"\n📊 Summary: {len(processed_lines)} valid RideWithGPS URLs found")
    return processed_lines


def debug_url_parsing(line):
    """Debug URL parsing"""
    print(f"\n🔗 DEBUGGING URL parsing for: {line}")
    
    parts = [part.strip() for part in line.split(',')]
    print(f"📝 Split parts: {parts}")
    
    url = parts[0]
    specified_type = parts[1].lower() if len(parts) > 1 else None
    
    print(f"🔗 URL: {url}")
    print(f"🏷️  Specified type: {specified_type}")
    
    # Test URL format
    route_match = re.search(r'/routes/(\d+)', url)
    if route_match:
        route_id = route_match.group(1)
        print(f"✅ Valid URL format, route ID: {route_id}")
        return url, specified_type, route_id
    else:
        print("❌ Invalid URL format - no route ID found")
        return None, None, None


def test_network_connection(url):
    """Test if we can connect to RideWithGPS"""
    print(f"\n🌐 TESTING network connection to: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; LoudounVelo-SiteBuilder-Debug/1.0)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            content_type = response.headers.get('content-type', '')
            content_length = response.headers.get('content-length', 'unknown')
            
            print(f"✅ Connection successful!")
            print(f"📊 Status: {status}")
            print(f"📄 Content-Type: {content_type}")
            print(f"📏 Content-Length: {content_length}")
            
            # Read a small sample
            sample = response.read(500).decode('utf-8', errors='ignore')
            print(f"📖 Content sample (first 200 chars): {sample[:200]}...")
            
            return True, status
            
    except urllib.error.URLError as e:
        print(f"❌ Network error: {e}")
        return False, str(e)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False, str(e)


def main():
    """Debug main function"""
    print("🔍 LOUDOUN VELO ROUTES DEBUG TOOL")
    print("=" * 50)
    
    # Debug current directory and files
    print(f"\n📍 Current directory: {os.getcwd()}")
    print("📁 Files in current directory:")
    for item in sorted(Path('.').iterdir()):
        if item.is_file():
            size = item.stat().st_size
            print(f"  📄 {item.name} ({size} bytes)")
        else:
            print(f"  📁 {item.name}/")
    
    # Debug rides.txt
    valid_lines = debug_rides_file()
    
    if not valid_lines:
        print("\n❌ No valid RideWithGPS URLs found!")
        print("\n💡 TROUBLESHOOTING TIPS:")
        print("1. Make sure rides.txt exists in the current directory")
        print("2. Add RideWithGPS URLs like: https://ridewithgps.com/routes/12345")
        print("3. Each URL should be on its own line")
        print("4. You can add route type: https://ridewithgps.com/routes/12345, road")
        print("5. Lines starting with # are comments and will be ignored")
        
        # Create a test rides.txt if none exists
        rides_file = Path('./rides.txt')
        if not rides_file.exists():
            test_content = """# Loudoun Velo Test Routes
# Add your RideWithGPS URLs below, one per line
# Format: URL, route_type (optional)

# Example (replace with real URLs):
# https://ridewithgps.com/routes/12345, road
# https://ridewithgps.com/routes/23456, gravel
"""
            rides_file.write_text(test_content)
            print(f"\n📝 Created test rides.txt file at: {rides_file.absolute()}")
        return
    
    # Test the first URL
    first_line = valid_lines[0]
    url, route_type, route_id = debug_url_parsing(first_line)
    
    if url and route_id:
        # Test network connection
        success, result = test_network_connection(url)
        
        if success:
            print(f"\n✅ Everything looks good for route {route_id}!")
            print("🔧 The original script should be able to process this route.")
        else:
            print(f"\n❌ Network issue detected: {result}")
            print("💡 This might be why no routes are being created.")
    
    # Check for other required files
    print(f"\n🔍 CHECKING other required files...")
    
    template_file = Path('./templates/index.template.html')
    if template_file.exists():
        print("✅ Template file exists")
    else:
        print("❌ Template file missing - this will cause the build to fail")
        print(f"📍 Expected: {template_file.absolute()}")
    
    routes_dir = Path('./routes')
    if routes_dir.exists():
        json_files = list(routes_dir.glob('*.json'))
        print(f"📁 Routes cache directory exists with {len(json_files)} cached routes")
    else:
        print("📁 No routes cache directory (will be created)")
    
    print(f"\n🎯 NEXT STEPS:")
    print("1. Fix any issues identified above")
    print("2. Run the original build.py script")
    print("3. Check the console output for detailed error messages")


if __name__ == '__main__':
    main()