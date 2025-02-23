"""Browser interaction tools."""
# TODOs : add other platforms ( Windows, Linux, etc.)
import webbrowser
import platform
from typing import Optional
import chainlit as cl
from utils.common import logger
import sys

def get_default_browser():
    try:
        if sys.platform != 'darwin':
            return 'default'
            
        from AppKit import NSWorkspace, NSURL
        handler = NSWorkspace.sharedWorkspace().URLForApplicationToOpenURL_(
            NSURL.URLWithString_("http://example.com")
        )
        return handler.lastPathComponent().lower().replace(" ", "")
    except ImportError:
        logger.warning("AppKit not available, using default browser")
        return 'default'
    except Exception as e:
        logger.error(f"Error detecting default browser: {e}")
        return 'default'

open_browser_def = {
    "name": "open_browser",
    "description": "Opens a URL in the user's default web browser.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to open in the browser (e.g., 'https://example.com')",
            }
        },
        "required": ["url"],
    },
}

def open_browser(url: str) -> str:
    """Open a URL in the user's default browser"""
    try:
        # Handle macOS differently if needed
        if platform.system() == 'Darwin':
            # Use macOS-specific open command
            import subprocess
            subprocess.call(['open', url])
        else:
            webbrowser.open(url)
        return f"Successfully opened {url}"
    except Exception as e:
        return f"Error opening browser: {str(e)}"

open_browser_handler = open_browser

open_browser = (open_browser_def, open_browser_handler)
