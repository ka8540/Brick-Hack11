"""Internet search tool using Tavily API."""
# todos : proper search result display and ai read for them
from typing import Dict, Any
import chainlit as cl
from utils.common import tavily_client, logger

internet_search_def = {
    "name": "internet_search",
    "description": "Search the internet for real-time information using Tavily's search API.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to execute"
            },
            "search_depth": {
                "type": "string",
                "description": "The depth of search - 'basic' for quick results or 'deep' for comprehensive search"
            }
        },
        "required": ["query", "search_depth"]
    }
}

def internet_search_handler(query: str, search_depth: str) -> Dict[str, Any]:
    """Executes an internet search using the Tavily API and returns the result."""
    try:
        logger.info(f"🕵 Performing internet search for query: '{query}'")
        response = tavily_client.search(
            query,
            search_depth=search_depth,
            include_images=True
        )

        results = response.get("results", [])
        if not results:
            cl.run_sync(cl.Message(content=f"🔍 No results found for '{query}'").send())
            return None

        for i, result in enumerate(results[:4]):  
            content = f"""
{i+1}. {result['title']}
{result['url']}
{result['content'][:150].strip()}{'...' if len(result['content']) > 150 else ''}
            """.strip()
            
            images = result.get('image_urls', [])
            elements = []            
            elements.append(
                cl.Text(
                    name=result['title'],
                    content=result['content'],
                    display="side"
                )
            )            
            if images:
                for img_url in images[:2]:  
                    elements.append(
                        cl.Image(
                            name=f"Search Result Image",
                            url=img_url,
                            display="inline"
                        )
                    )
            
            cl.run_sync(
                cl.Message(
                    content=content,
                    elements=elements
                ).send()
            )

        logger.info(f"📏 Search results for '{query}' retrieved successfully.")
        return response["results"]
    except Exception as e:
        error_msg = f"Search error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        cl.run_sync(cl.Message(content=error_msg).send())
        return {"error": error_msg}

internet_search = (internet_search_def, internet_search_handler)