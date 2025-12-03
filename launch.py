#!/usr/bin/env python3
"""
Cross-platform launcher for Jackdaw voice assistant.

This script works on Windows, Linux, and macOS. It launches the system tray
application and ensures the virtual environment is used correctly.

Usage:
    python launch.py           # Launch tray app
    python launch.py --help    # Show help
"""

import sys
import subprocess
from pathlib import Path
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import platform_utils


def find_venv_python() -> Path:
    """
    Find the Python executable in the virtual environment.
    
    Returns:
        Path to venv Python executable, or current Python if not found
    """
    script_dir = Path(__file__).parent
    
    if platform_utils.is_windows():
        # Windows: .venv\Scripts\python.exe
        venv_python = script_dir / '.venv' / 'Scripts' / 'python.exe'
    else:
        # Unix-like: .venv/bin/python
        venv_python = script_dir / '.venv' / 'bin' / 'python'
    
    if venv_python.exists():
        return venv_python
    
    # Fall back to current Python
    return Path(sys.executable)


def check_dependencies() -> bool:
    """
    Check if required dependencies are available.
    
    Returns:
        True if dependencies are OK, False otherwise
    """
    try:
        import PySide6
        return True
    except ImportError:
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Launch Jackdaw voice assistant',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch.py              # Launch tray app
  python launch.py --version    # Show version
        """
    )
    
    parser.add_argument(
        '--version',
        action='store_true',
        help='Show version information'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check dependencies without launching'
    )
    
    args = parser.parse_args()
    
    # Show version
    if args.version:
        print(f"Jackdaw Voice Assistant v2.0.0")
        print(f"Platform: {platform_utils.get_platform_name()}")
        print(f"Python: {sys.version}")
        return 0
    
    # Check dependencies
    if not check_dependencies():
        print("Error: Required dependencies not found.")
        print("Please install dependencies:")
        print("  pip install -r requirements.txt")
        return 1
    
    if args.check:
        print("✓ Dependencies OK")
        print(f"Platform: {platform_utils.get_platform_name()}")
        return 0
    
    # Find Python executable
    python_exe = find_venv_python()
    
    # Find tray app script
    script_dir = Path(__file__).parent
    tray_app = script_dir / "voice_assistant_tray.py"
    
    if not tray_app.exists():
        print(f"Error: Could not find {tray_app}")
        return 1
    
    # Check for config file
    config_file = script_dir / "voice_assistant_config.json"
    if not config_file.exists():
        config_example = script_dir / "voice_assistant_config.json.example"
        if config_example.exists():
            print("Warning: No configuration file found.")
            print(f"Copy {config_example.name} to voice_assistant_config.json and edit it.")
        else:
            print("Warning: No configuration file found.")
        print("The application may not function correctly without configuration.")
        response = input("Continue anyway? [y/N] ")
        if response.lower() not in ['y', 'yes']:
            return 1
    
    # Launch the tray app
    print(f"Starting Jackdaw on {platform_utils.get_platform_name()}...")
    print(f"Using Python: {python_exe}")
    
    try:
        # Launch as subprocess so this script can exit
        if platform_utils.is_windows():
            # On Windows, use CREATE_NEW_PROCESS_GROUP to detach
            subprocess.Popen(
                [str(python_exe), str(tray_app)],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            # On Unix-like, just launch normally
            subprocess.Popen(
                [str(python_exe), str(tray_app)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        print("✓ Jackdaw tray app launched")
        print("Look for the Jackdaw icon in your system tray")
        return 0
        
    except Exception as e:
        print(f"Error launching Jackdaw: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
