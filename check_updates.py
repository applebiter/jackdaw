#!/usr/bin/env python3
"""
Check for Jackdaw updates from GitHub without auto-updating.
"""

import subprocess
import sys
from pathlib import Path


def check_for_updates(verbose=True) -> dict:
    """
    Check if updates are available from GitHub.
    
    Returns:
        dict with keys: 'available' (bool), 'local_commit' (str), 'remote_commit' (str), 'message' (str)
    """
    result = {
        'available': False,
        'local_commit': '',
        'remote_commit': '',
        'message': ''
    }
    
    try:
        # Fetch latest from origin without merging
        subprocess.run(
            ['git', 'fetch', 'origin'],
            check=True,
            capture_output=True,
            timeout=10
        )
        
        # Get local HEAD commit
        local = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            check=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        result['local_commit'] = local.stdout.strip()[:7]
        
        # Get remote HEAD commit
        remote = subprocess.run(
            ['git', 'rev-parse', '@{u}'],
            check=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        result['remote_commit'] = remote.stdout.strip()[:7]
        
        # Compare
        if result['local_commit'] != result['remote_commit']:
            result['available'] = True
            result['message'] = f"Updates available: {result['local_commit']} -> {result['remote_commit']}"
            
            # Get number of commits behind
            count = subprocess.run(
                ['git', 'rev-list', '--count', f'{result["local_commit"]}..{result["remote_commit"]}'],
                check=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            commits_behind = count.stdout.strip()
            result['message'] += f" ({commits_behind} commit{'s' if commits_behind != '1' else ''} behind)"
            
            if verbose:
                print(f"[Updates] {result['message']}")
        else:
            result['message'] = "Jackdaw is up to date"
            if verbose:
                print(f"[Updates] {result['message']}")
                
    except subprocess.TimeoutExpired:
        result['message'] = "Update check timed out (network issue?)"
        if verbose:
            print(f"[Updates] {result['message']}")
    except subprocess.CalledProcessError as e:
        result['message'] = f"Update check failed: {e}"
        if verbose:
            print(f"[Updates] {result['message']}")
    except Exception as e:
        result['message'] = f"Update check error: {e}"
        if verbose:
            print(f"[Updates] {result['message']}")
    
    return result


def write_update_notification(result: dict):
    """Write update notification to file for tray widget to display"""
    try:
        notification_file = Path(".update_available")
        if result['available']:
            notification_file.write_text(result['message'])
        else:
            # Remove notification file if no updates
            if notification_file.exists():
                notification_file.unlink()
    except Exception as e:
        print(f"[Updates] Failed to write notification: {e}")


if __name__ == "__main__":
    result = check_for_updates(verbose=True)
    write_update_notification(result)
    sys.exit(0 if not result['available'] else 1)
