"""Common utilities and configurations."""

import os
import logging
from dotenv import load_dotenv
from together import Together
from tavily import TavilyClient
load_dotenv()


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

scratch_pad_dir = "./scratchpad"
os.makedirs(scratch_pad_dir, exist_ok=True)

together_client = None
tavily_client = None

try:
    if together_api_key := os.environ.get("TOGETHER_API_KEY"):
        together_client = Together(api_key=together_api_key)
    else:
        logger.warning("⚠️ TOGETHER_API_KEY not found in environment variables")
except Exception as e:
    logger.error(f"❌ Error initializing Together client: {str(e)}")

try:
    if tavily_api_key := os.environ.get("TAVILY_API_KEY"):
        tavily_client = TavilyClient(api_key=tavily_api_key)
    else:
        logger.warning("⚠️ TAVILY_API_KEY not found in environment variables")
except Exception as e:
    logger.error(f"❌ Error initializing Tavily client: {str(e)}")