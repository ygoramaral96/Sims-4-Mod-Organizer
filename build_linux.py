"""
Build script for Linux binary using PyInstaller
"""
import os
import sys
import subprocess

def build_linux():
    """Build Linux binary using PyInstaller"""
    
    print("=" * 60)
    print("Building Sims 4 Mod Organizer for Linux")
    print("=" * 60)
    
    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',           # Single executable file
        '--name', 'sims4-mod-organizer',
        '--add-data', 'src:src',  # Include src folder (Linux uses colon)
        'main.py'
    ]
    
    print(f"\nRunning: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("[SUCCESS] Build successful!")
        print("=" * 60)
        print(f"\nBinary location: dist/sims4-mod-organizer")
        print("\nMake it executable:")
        print("  chmod +x dist/sims4-mod-organizer")
        print("\nYou can distribute this binary to Linux users.")
        
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Build failed: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("\n[ERROR] PyInstaller not found!")
        print("Install it with: pip install pyinstaller")
        sys.exit(1)

if __name__ == '__main__':
    build_linux()
