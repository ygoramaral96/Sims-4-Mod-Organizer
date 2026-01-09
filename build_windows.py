"""
Build script for Windows executable using PyInstaller
"""
import os
import sys
import subprocess

def build_windows():
    """Build Windows .exe using PyInstaller"""
    
    print("=" * 60)
    print("Building Sims 4 Mod Organizer for Windows")
    print("=" * 60)
    
    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',           # Single executable file
        '--windowed',          # No console window (GUI only)
        '--name', 'Sims4ModOrganizer',
        '--icon=icon.ico',     # Optional: add if you have an icon
        '--add-data', 'src;src',  # Include src folder
        'main.py'
    ]
    
    # Remove --icon if icon.ico doesn't exist
    if not os.path.exists('icon.ico'):
        cmd.remove('--icon=icon.ico')
    
    print(f"\nRunning: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✓ Build successful!")
        print("=" * 60)
        print(f"\nExecutable location: dist\\Sims4ModOrganizer.exe")
        print("\nYou can distribute this .exe file to Windows users.")
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("\n✗ PyInstaller not found!")
        print("Install it with: pip install pyinstaller")
        sys.exit(1)

if __name__ == '__main__':
    build_windows()
