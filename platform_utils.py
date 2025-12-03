#!/usr/bin/env python3
"""
Cross-platform utilities for process and system management.

Provides platform-independent functions for operations that differ between
Windows and Unix-like systems (Linux, macOS).
"""

import platform
import subprocess
import sys
from typing import Optional, List
from pathlib import Path


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system() == "Windows"


def is_linux() -> bool:
    """Check if running on Linux."""
    return platform.system() == "Linux"


def is_macos() -> bool:
    """Check if running on macOS."""
    return platform.system() == "Darwin"


def get_platform_name() -> str:
    """Get human-readable platform name."""
    system = platform.system()
    if system == "Windows":
        return f"Windows {platform.release()}"
    elif system == "Linux":
        return f"Linux {platform.release()}"
    elif system == "Darwin":
        return f"macOS {platform.mac_ver()[0]}"
    return system


def find_process(pattern: str) -> Optional[int]:
    """
    Find process ID by name pattern.
    
    Args:
        pattern: String to search for in process command line
        
    Returns:
        Process ID if found, None otherwise
    """
    try:
        if is_windows():
            # Use WMIC to find Python processes
            result = subprocess.run(
                ["wmic", "process", "where", f"CommandLine like '%{pattern}%'", "get", "ProcessId"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                # Parse output (skip header, get first PID)
                lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                if len(lines) > 1:  # Skip "ProcessId" header
                    try:
                        return int(lines[1])
                    except (ValueError, IndexError):
                        pass
        else:
            # Use pgrep on Unix-like systems
            result = subprocess.run(
                ["pgrep", "-f", pattern],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split()[0])
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    
    return None


def find_all_processes(pattern: str) -> List[int]:
    """
    Find all process IDs matching a pattern.
    
    Args:
        pattern: String to search for in process command line
        
    Returns:
        List of process IDs
    """
    pids = []
    
    try:
        if is_windows():
            # Use WMIC to find Python processes
            result = subprocess.run(
                ["wmic", "process", "where", f"CommandLine like '%{pattern}%'", "get", "ProcessId"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                for line in lines[1:]:  # Skip header
                    try:
                        pids.append(int(line))
                    except ValueError:
                        continue
        else:
            # Use pgrep on Unix-like systems
            result = subprocess.run(
                ["pgrep", "-f", pattern],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pids = [int(pid) for pid in result.stdout.strip().split('\n')]
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    
    return pids


def kill_process(pattern: str, force: bool = False) -> bool:
    """
    Kill process(es) by name pattern.
    
    Args:
        pattern: String to search for in process command line
        force: Use force kill (SIGKILL on Unix, /F on Windows)
        
    Returns:
        True if processes were killed, False otherwise
    """
    killed = False
    
    try:
        if is_windows():
            # Find PIDs first
            pids = find_all_processes(pattern)
            
            for pid in pids:
                cmd = ["taskkill"]
                if force:
                    cmd.append("/F")
                cmd.extend(["/PID", str(pid)])
                
                result = subprocess.run(cmd, capture_output=True, timeout=5)
                if result.returncode == 0:
                    killed = True
        else:
            # Use pkill on Unix-like systems
            cmd = ["pkill"]
            if force:
                cmd.append("-9")
            cmd.extend(["-f", pattern])
            
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            if result.returncode == 0:
                killed = True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return killed


def kill_process_by_pid(pid: int, force: bool = False) -> bool:
    """
    Kill a specific process by PID.
    
    Args:
        pid: Process ID to kill
        force: Use force kill
        
    Returns:
        True if process was killed, False otherwise
    """
    try:
        if is_windows():
            cmd = ["taskkill"]
            if force:
                cmd.append("/F")
            cmd.extend(["/PID", str(pid)])
            
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            return result.returncode == 0
        else:
            import signal
            sig = signal.SIGKILL if force else signal.SIGTERM
            
            import os
            os.kill(pid, sig)
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, ProcessLookupError, PermissionError):
        return False


def get_python_executable() -> str:
    """
    Get the current Python executable path.
    
    Returns:
        Path to Python executable
    """
    return sys.executable


def get_app_data_dir() -> Path:
    """
    Get platform-appropriate application data directory.
    
    Returns:
        Path to application data directory
    """
    if is_windows():
        # Use %APPDATA%\Jackdaw on Windows
        appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        return appdata / 'Jackdaw'
    else:
        # Use ~/.local/share/jackdaw on Unix-like systems
        xdg_data = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
        return xdg_data / 'jackdaw'


def get_config_dir() -> Path:
    """
    Get platform-appropriate configuration directory.
    
    Returns:
        Path to configuration directory
    """
    if is_windows():
        # Use %APPDATA%\Jackdaw on Windows
        appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        return appdata / 'Jackdaw'
    else:
        # Use ~/.config/jackdaw on Unix-like systems
        xdg_config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
        return xdg_config / 'jackdaw'


def get_log_dir() -> Path:
    """
    Get platform-appropriate log directory.
    
    Returns:
        Path to log directory
    """
    if is_windows():
        # Use %LOCALAPPDATA%\Jackdaw\Logs on Windows
        localappdata = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        return localappdata / 'Jackdaw' / 'Logs'
    else:
        # Use ~/.local/share/jackdaw/logs on Unix-like systems
        return get_app_data_dir() / 'logs'


# Import os for environment variables
import os
