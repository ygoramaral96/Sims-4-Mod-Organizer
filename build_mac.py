"""
Build script for macOS .app bundle using PyInstaller
"""
import os
import sys
import subprocess

def build_mac():
    """Build macOS .app bundle using PyInstaller"""
    
    print("=" * 60)
    print("Building Sims 4 Mod Organizer for macOS")
    print("=" * 60)
    
    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',           # Single executable
        '--windowed',          # Create .app bundle (not console app)
        '--name', 'Sims4ModOrganizer',
        '--icon=icon.icns',    # Optional: macOS icon format
        '--add-data', 'src:src',  # Include src folder (macOS uses colon)
        '--osx-bundle-identifier', 'com.sims4.modorganizer',
        'main.py'
    ]
    
    # Remove --icon if icon.icns doesn't exist
    if not os.path.exists('icon.icns'):
        cmd.remove('--icon=icon.icns')
    
    print(f"\nRunning: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✓ Build successful!")
        print("=" * 60)
        print(f"\nApp bundle location: dist/Sims4ModOrganizer.app")
        print("\nYou can distribute this .app to macOS users.")
        print("Note: Users may need to right-click → Open to bypass Gatekeeper")
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("\n✗ PyInstaller not found!")
        print("Install it with: pip install pyinstaller")
        sys.exit(1)

if __name__ == '__main__':
    build_mac()
