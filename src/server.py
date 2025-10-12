import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from starlette.middleware.sessions import SessionMiddleware
from fastapi.routing import APIRouter
from src.utils.logging_config import setup_logging

# Setup logging before anything else
setup_logging()

# Load environment variables
SESSION_SECRET_KEY = "TODO: Set your session secret key here"

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
    secret_key=SESSION_SECRET_KEY,
    same_site="none",
    https_only=True,
)


# Automatically discover and include all routers
def include_all_routers():
    main_router = APIRouter()

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
