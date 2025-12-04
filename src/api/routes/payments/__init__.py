"""Payments routes module"""

from .subscription import router as subscription_router

__all__ = ["subscription_router"]
