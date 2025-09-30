"""
API Routes Package
"""

from .ping import router as ping_router

__all__ = [
    "ping_router",
]
