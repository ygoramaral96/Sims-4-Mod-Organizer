"""
Universal build script - detects platform and builds appropriate executable
"""
import sys
import platform

def build_all():
    """Detect platform and run appropriate build script"""
    
    system = platform.system()
    
    print(f"Detected OS: {system}")
    print()
    
    if system == 'Windows':
        print("Building for Windows...")
        from build_windows import build_windows
        build_windows()
        
    elif system == 'Darwin':  # macOS
        print("Building for macOS...")
        from build_mac import build_mac
        build_mac()
        
    elif system == 'Linux':
        print("Building for Linux...")
        from build_linux import build_linux
        build_linux()
        
    else:
        print(f"❌ Unsupported platform: {system}")
        sys.exit(1)

if __name__ == '__main__':
    build_all()
