"""Plotly chart drawing tool."""

import chainlit as cl
import plotly
import json
from utils.common import logger
import asyncio
from tools.stock import query_stock_price_handler

draw_plotly_chart_def = {
    "name": "draw_plotly_chart",
    "description": "Draws stock chart. Auto-fetches data if needed. Provide either chart_data OR symbol+period.",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Contextual message for the chart"
            },
            "plotly_json_fig": {
                "type": "string",
                "description": "Pre-generated chart data from query_stock_price"
            },
            "symbol": {
                "type": "string",
                "description": "Stock symbol to chart (e.g. NVDA)"
            },
            "period": {
                "type": "string",
                "description": "Time period for chart (e.g. '1mo')"
            },
            "reset_session": {
                "type": "boolean",
                "description": "Whether to reset the session data before processing"
            }
        },
        "required": ["message"]  
    },
}

def reset_stock_session():
    """Reset all stock-related session data"""
    session_keys = ["chart_data", "last_symbol", "last_period"]
    for key in session_keys:
        if cl.user_session.get(key):
            cl.user_session.set(key, None)
    logger.info("🔄 Reset stock session data")

def draw_plotly_chart_handler(message: str, plotly_json_fig: str = None, symbol: str = None, period: str = None, reset_session: bool = False):
    try:
        logger.info(f"🎨 Drawing Plotly chart with message: {message}")
        
        cl.run_sync(
            cl.Message(content=f"⏳ Generating chart for {symbol or 'selected stock'}...").send()
        )

        if isinstance(reset_session, str):
            reset_session = reset_session.lower() == 'true'
        
        if reset_session or (symbol and symbol != cl.user_session.get("last_symbol")) or (period and period != cl.user_session.get("last_period")):
            reset_stock_session()        
        symbol = symbol or cl.user_session.get("last_symbol")
        period = period or cl.user_session.get("last_period")        
        if not plotly_json_fig:
            stored_chart_data = cl.user_session.get("chart_data")
            if stored_chart_data and not reset_session:
                plotly_json_fig = stored_chart_data
                logger.info("📊 Using stored chart data")
            else:
                logger.info("🔍 No chart data available - attempting fetch")
                
                if not symbol or not period:
                    error_msg = "Need stock symbol and period to fetch data. Please specify like: 'Chart for NVDA last month'"
                    logger.error(f"❌ {error_msg}")
                    cl.run_sync(
                        cl.Message(content=error_msg).send()
                    )
                    return {"error": error_msg}
                
                logger.info(f"📈 Fetching data for {symbol} ({period})")
                stock_result = query_stock_price_handler(symbol, period, reset_session=False)  
                
                if "error" in stock_result:
                    error_msg = stock_result["error"]
                    cl.run_sync(
                        cl.Message(content=f"Error: {error_msg}").send()
                    )
                    return stock_result
                
                plotly_json_fig = stock_result.get("chart_data")
                if not plotly_json_fig:
                    error_msg = "Failed to generate chart data"
                    cl.run_sync(
                        cl.Message(content=f"Error: {error_msg}").send()
                    )
                    return {"error": error_msg}
        try:
            fig = plotly.io.from_json(plotly_json_fig)
            cl.run_sync(
                cl.Message(
                    content=message,
                    elements=[cl.Plotly(name="chart", figure=fig, display="inline")]
                ).send()
            )
            return {"status": "success"}
        except Exception as chart_error:
            error_msg = f"Failed to render chart: {str(chart_error)}"
            logger.error(f"❌ {error_msg}")
            cl.run_sync(
                cl.Message(content=f"Error: {error_msg}").send()
            )
            return {"error": error_msg}
    
    except Exception as e:
        error_msg = f"Chart error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        cl.run_sync(
            cl.Message(content=f"Error: {error_msg}").send()
        )
        return {"error": error_msg}

draw_plotly_chart = (draw_plotly_chart_def, draw_plotly_chart_handler)
