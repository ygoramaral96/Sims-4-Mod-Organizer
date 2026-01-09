import PyInstaller.__main__
import os
import shutil

METHODS = [
    'main.py',
    '--name=Sims4ModOrganizer',
    '--onefile',
    '--windowed',
    '--clean',
    '--add-data=src:src',  # Include source package if needed, though pure python imports usually auto-detected
    # If we had data files (images, icons), we'd add them here
]

def build():
    # Clean previous builds
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')

    print("Building executable...")
    PyInstaller.__main__.run(METHODS)
    print("Build complete! Check dist/ folder.")

if __name__ == "__main__":
    build()
