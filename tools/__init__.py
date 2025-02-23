"""Tool definitions and handlers."""

from .stock import query_stock_price
from .chart import draw_plotly_chart
from .image import generate_image
from .search import internet_search
from .linkedin import draft_linkedin_post
from .python_file import create_python_file, execute_python_file
from .browser import open_browser
from .email import draft_email

tools = [
    query_stock_price,
    draw_plotly_chart,
    generate_image,
    internet_search,
    draft_linkedin_post,
    create_python_file,
    execute_python_file,
    open_browser,
    draft_email,
]

__all__ = ["tools"]
