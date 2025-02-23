"""Browser interaction tools."""
# TODOs : add other platforms ( Windows, Linux, etc.)
import webbrowser
import AppKit
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

async def open_browser_handler(url: str) -> dict:
    """Opens a URL in the default browser."""
    try:
        import webbrowser
        webbrowser.open(url)
        logger.info(f"🌐 Opening browser URL: {url}")
        return {"status": "success", "url": url}
    except Exception as e:
        logger.error(f"Failed to open browser: {str(e)}")
        return {"status": "error", "message": str(e)}

open_browser = (open_browser_def, open_browser_handler)
