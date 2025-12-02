"""
API Routes Package

This package contains all API route modules. When adding a new route:
1. Create your route module in this directory (or subdirectory)
2. Import the router here with a descriptive name (e.g., `router as <feature>_router`)
3. Add it to the `all_routers` list
4. The router will be automatically included in the FastAPI app

See .cursor/rules/routes.mdc for detailed instructions.
"""

from .ping import router as ping_router
from .agent.agent import router as agent_router
from .payments import stripe_router

# List of all routers to be included in the application
# Add new routers to this list when creating new endpoints
all_routers = [
    ping_router,
    agent_router,
    stripe_router,
]

__all__ = [
    "all_routers",
    "ping_router",
    "agent_router",
    "stripe_router",
]
