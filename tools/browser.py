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

def open_browser_handler(url: str):
    """Open a URL in the default browser with proper error handling."""
    try:
        logger.info(f"🌐 Opening browser URL: {url}")
        
        # Try detected browser first
        browser_name = get_default_browser()
        if browser_name == "brave":
            brave_path = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser'
            webbrowser.register('brave', None, webbrowser.BackgroundBrowser(brave_path))
            webbrowser.get('brave').open(url)
        else:
            webbrowser.get().open(url)
            
        cl.run_sync(
            cl.Message(
                content=f"✅ Opened {url} in your browser"
            ).send()
        )
            
        return {"status": "success", "message": f"Opened {url} in browser"}
    except webbrowser.Error as e:
        error_msg = f"❌ Browser error: {str(e)}"
        logger.error(error_msg)
        cl.run_sync(cl.Message(content=error_msg).send())
        return {"status": "error", "message": str(e)}
    except Exception as e:
        error_msg = f"❌ Unexpected error: {str(e)}"
        logger.error(error_msg)
        cl.run_sync(cl.Message(content=error_msg).send())
        return {"status": "error", "message": str(e)}

open_browser = (open_browser_def, open_browser_handler)
