"""Test script to check if ValoSwitcher components are working"""
import sys
import os
import requests
import urllib.parse
import cloudscraper

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

def test_imports():
    """Test if all required packages are installed"""
    print("Testing imports...")
    try:
        import PyQt6
        import qfluentwidgets
        import win32gui
        import psutil
        import pyautogui
        import matplotlib
        import numpy
        import scipy
        import PIL
        print("✅ All dependencies installed successfully!\n")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}\n")
        print("Run: pip install -r requirements.txt")
        return False

def test_tracker_api():
    """Test if tracker.gg API is still working"""
    print("Testing Tracker.gg API...")
    # Test with a known public account
    test_name = "Shroud"
    test_tag = "6102"

    # Use cloudscraper to bypass Cloudflare
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': f'https://tracker.gg/valorant/profile/riot/{urllib.parse.quote(test_name)}%23{urllib.parse.quote(test_tag)}/overview',
        'Origin': 'https://tracker.gg',
    }

    try:
        url = f"https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{urllib.parse.unquote(test_name)}%23{urllib.parse.quote(test_tag)}?source=web"
        print(f"Testing API URL: {url}")
        response = scraper.get(url, headers=headers, timeout=10)

        # 200 = Success, 404 = Not Found, 451 = Private Profile
        # All these mean the API is working (not blocked by Cloudflare)
        if response.status_code in [200, 404, 451]:
            data = response.json()
            if response.status_code == 200 and 'data' in data:
                print(f"✅ Tracker.gg API working!")
                print(f"   Sample data: Level {data['data']['metadata'].get('accountLevel', 'N/A')}")
                return True
            elif response.status_code == 404:
                print(f"✅ Tracker.gg API working! (Test account not found, but API is responding)")
                return True
            elif response.status_code == 451:
                print(f"✅ Tracker.gg API working! (Test account is private, but API is responding)")
                return True
            else:
                print(f"⚠️ API returned unexpected format")
                print(f"   Response: {response.text[:200]}")
                return False
        else:
            print(f"❌ API returned status code: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False

def test_valorant_api():
    """Test if valorant-api.com is still working"""
    print("\nTesting Valorant API (for level borders)...")
    test_url = "https://media.valorant-api.com/levelborders/ebc736cd-4b6a-137b-e2b0-1486e31312c9/levelnumberappearance.png"

    try:
        response = requests.get(test_url, timeout=10)
        if response.status_code == 200:
            print(f"✅ Valorant API working!")
            return True
        else:
            print(f"❌ Valorant API returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing Valorant API: {e}")
        return False

def main():
    print("=" * 50)
    print("ValoSwitcher Diagnostic Test")
    print("=" * 50 + "\n")

    results = []
    results.append(("Dependencies", test_imports()))

    if results[0][1]:  # Only test APIs if dependencies are installed
        results.append(("Tracker.gg API", test_tracker_api()))
        results.append(("Valorant API", test_valorant_api()))

    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print("=" * 50)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")

    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n🎉 All tests passed! ValoSwitcher should work.")
    else:
        print("\n⚠️ Some tests failed. Check errors above.")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
