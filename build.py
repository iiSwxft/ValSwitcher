"""
ValoSwitcher Build Script
Builds the application into a standalone .exe using PyInstaller
"""

import subprocess
import sys
import os
from pathlib import Path

def install_pyinstaller():
    """Install PyInstaller if not already installed."""
    print("Checking for PyInstaller...")
    try:
        import PyInstaller
        print("PyInstaller is already installed.")
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller installed successfully.")

def build_exe():
    """Build the .exe using PyInstaller."""
    print("\n" + "="*60)
    print("Building ValoSwitcher.exe...")
    print("="*60 + "\n")

    # PyInstaller command with all necessary flags
    command = [
        "pyinstaller",
        "--name=ValoSwitcher",
        "--onefile",  # Single exe file
        "--windowed",  # No console window
        "--icon=assets/iconVS.png",
        "--add-data=assets;assets",  # Include assets folder
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=qfluentwidgets",
        "--hidden-import=qframelesswindow",
        "--hidden-import=cloudscraper",
        "--hidden-import=win32com.client",
        "--hidden-import=win32gui",
        "--hidden-import=win32con",
        "--hidden-import=psutil",
        "--hidden-import=pyautogui",
        "--hidden-import=matplotlib",
        "--hidden-import=numpy",
        "--hidden-import=scipy",
        "--hidden-import=PIL",
        "--collect-all=qfluentwidgets",
        "--collect-all=qframelesswindow",
        "--exclude-module=PyQt5",  # Exclude PyQt5 to avoid conflicts
        "--exclude-module=PySide2",  # Exclude PySide2 to avoid conflicts
        "--exclude-module=PySide6",  # Exclude PySide6 to avoid conflicts
        "--noconfirm",  # Overwrite without asking
        "main.py"
    ]

    try:
        subprocess.check_call(command)
        print("\n" + "="*60)
        print("Build completed successfully!")
        print("="*60)
        print(f"\nYour executable is located at:")
        print(f"  {os.path.abspath('dist/ValoSwitcher.exe')}")
        print("\nIMPORTANT:")
        print("  1. Config is auto-created at Documents\\ValoSwitcher\\config.ini")
        print("  2. Sessions are saved in Documents\\ValoSwitcher\\sessions\\")
        print("  3. Just run the exe - everything is set up automatically!")
        print("\n" + "="*60)
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error: {e}")
        sys.exit(1)

def cleanup_build_files():
    """Ask user if they want to clean up build files."""
    print("\nDo you want to clean up build files? (y/n): ", end="")
    choice = input().lower()

    if choice == 'y':
        import shutil
        print("Cleaning up...")
        if os.path.exists('build'):
            shutil.rmtree('build')
            print("  - Removed 'build' folder")
        if os.path.exists('ValoSwitcher.spec'):
            os.remove('ValoSwitcher.spec')
            print("  - Removed 'ValoSwitcher.spec' file")
        print("Cleanup complete!")

if __name__ == "__main__":
    print("ValoSwitcher Build Script")
    print("="*60)

    # Check if we're in the right directory
    if not os.path.exists('main.py'):
        print("ERROR: main.py not found!")
        print("Please run this script from the ValoSwitcher-main directory.")
        sys.exit(1)

    if not os.path.exists('assets'):
        print("WARNING: assets folder not found!")
        print("The build will fail without the assets folder.")
        sys.exit(1)

    # Install PyInstaller
    install_pyinstaller()

    # Build the exe
    build_exe()

    # Cleanup
    cleanup_build_files()

    print("\nPress Enter to exit...")
    input()
