"""Stock price querying tool."""

import yfinance as yf
from typing import Dict, Any
from utils.common import logger
import pandas as pd
import json
import chainlit as cl
from retry import retry
import time
import requests
from functools import partial
import asyncio

query_stock_price_def = {
    "name": "query_stock_price",
    "description": "Queries stock price information for a given symbol and time period.",
    "parameters": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "The stock symbol to query (e.g., 'AAPL' for Apple Inc.)"
            },
            "period": {
                "type": "string",
                "description": "Time period for data retrieval (e.g., '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max')"
            },
            "reset_session": {
                "type": "boolean",
                "description": "Whether to reset the session data before processing"
            }
        },
        "required": ["symbol", "period"]
    }
}

def reset_stock_session():
    """Reset all stock-related session data"""
    session_keys = ["chart_data", "last_symbol", "last_period"]
    for key in session_keys:
        if cl.user_session.get(key):
            cl.user_session.set(key, None)
    logger.info("🔄 Reset stock session data")

@retry(tries=3, delay=2, backoff=2, max_delay=10)
def query_stock_price_handler(symbol: str, period: str, reset_session: bool = False) -> Dict[str, Any]:
    """Queries stock price information for a given symbol and time period."""
    try:
        # Reset session if requested or if new stock/period
        if reset_session or (symbol != cl.user_session.get("last_symbol")) or (period != cl.user_session.get("last_period")):
            reset_stock_session()
        
        symbol = symbol.strip().upper()
        cl.user_session.set("last_symbol", symbol)
        cl.user_session.set("last_period", period)
        
        logger.info(f"📈 Fetching stock price for symbol: {symbol}, period: {period}")
        
        # Create async context for yfinance
        loop = asyncio.get_event_loop()
        
        # Run yfinance operations in a thread pool
        def yf_operations():
            stock = yf.Ticker(symbol, session=requests.Session())
            hist = stock.history(period=period)
            info = stock.info
            return hist, info
            
        hist, info = yf_operations()
        
        if hist.empty:
            logger.warning(f"⚠️ No data found for symbol: {symbol}")
            return {
                "error": f"No data found for symbol: {symbol}. Please check if the symbol is correct."
            }
            
        logger.info(f"📊 Got {len(hist)} data points for {symbol}")
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        prices = hist['Close'].tolist()
        
        # Create optimized Plotly figure structure
        chart_data = {
            "data": [{
                "type": "scatter",
                "mode": "lines+markers",
                "x": dates,
                "y": [float(price) for price in prices],
                "line": {"simplify": True}  
            }],
            "layout": {
                "title": f"{symbol} Stock Prices - Last {period}",
                "showlegend": False,
                "margin": dict(t=40, b=60, l=40, r=20),
                "xaxis": {
                    "tickangle": -45,
                    "type": "date",
                    "tickformat": "%b %d",
                    "automargin": True
                },
                "yaxis": {
                    "automargin": True
                }
            }
        }
        
        json_data = json.dumps(chart_data, separators=(',', ':'))
        logger.info(f"📈 Generated chart data with {len(dates)} points")
        
        # Store chart data in session
        cl.user_session.set("chart_data", json_data)
        
        result = {
            "symbol": symbol,
            "company": info.get("longName", symbol),
            "period": period,
            "currency": info.get("currency", "USD"),
            "current_price": float(prices[-1]),
            "price_change": float(prices[-1] - prices[0]),
            "price_change_percent": float((prices[-1] - prices[0]) / prices[0] * 100),
            "chart_data": json_data
        }
        
        logger.info(f"💸 Successfully prepared stock data for {symbol}")
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error querying stock price: {error_msg}")
        return {"error": f"Failed to retrieve stock data: {error_msg}"}

query_stock_price = (query_stock_price_def, query_stock_price_handler)
