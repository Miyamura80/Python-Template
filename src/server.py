import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from starlette.middleware.sessions import SessionMiddleware
from fastapi.routing import APIRouter
from src.utils.logging_config import setup_logging
from common import global_config

# Setup logging before anything else
setup_logging()

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware with specific allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware (required for OAuth flow)
app.add_middleware(
    SessionMiddleware,
    secret_key=global_config.SESSION_SECRET_KEY,
    same_site="none",
    https_only=True,
)


# Automatically discover and include all routers
def include_all_routers():
    from src.api.routes import all_routers

    main_router = APIRouter()
    for router in all_routers:
        main_router.include_router(router)

    return main_router


app.include_router(include_all_routers())


if __name__ == "__main__":
    # Configure uvicorn to use our logging config
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        log_config=None,  # Disable uvicorn's logging config
        access_log=False,  # Disable access logs
    )
