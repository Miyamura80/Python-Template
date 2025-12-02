import sys
import subprocess
import importlib.metadata
import requests
from packaging import version
from loguru import logger as log
import typer
import json
import time
from pathlib import Path

PACKAGE_NAME = "eito-cli"
# Fallback for local development if the directory name matches the package name in pyproject.toml
LOCAL_PACKAGE_NAME = "python-template"
CACHE_DIR = Path.home() / ".eito-cli"
CACHE_FILE = CACHE_DIR / "update_check.json"
CACHE_TTL = 86400  # 24 hours

def get_current_version() -> str | None:
    """
    Get the currently installed version of the package.
    """
    try:
        return importlib.metadata.version(PACKAGE_NAME)
    except importlib.metadata.PackageNotFoundError:
        try:
            # Fallback for local development
            return importlib.metadata.version(LOCAL_PACKAGE_NAME)
        except importlib.metadata.PackageNotFoundError:
            log.debug(f"Package {PACKAGE_NAME} (or {LOCAL_PACKAGE_NAME}) not found.")
            return None

def get_latest_version(package_name: str = PACKAGE_NAME) -> str | None:
    """
    Get the latest version of the package from PyPI.
    """
    try:
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json", timeout=2)
        if response.status_code == 200:
            return response.json()["info"]["version"]
        else:
            log.debug(f"Failed to fetch package info from PyPI. Status code: {response.status_code}")
            return None
    except requests.RequestException as e:
        log.debug(f"Error checking for updates: {e}")
        return None

def get_cached_latest_version() -> str | None:
    """
    Get the latest version from cache if valid.
    """
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        timestamp = data.get("timestamp", 0)
        if time.time() - timestamp < CACHE_TTL:
            return data.get("version")
    except Exception:
        pass
    return None

def save_cached_latest_version(version_str: str):
    """
    Save the latest version to cache.
    """
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps({
            "timestamp": time.time(),
            "version": version_str
        }))
    except Exception:
        # Silently fail if we can't write cache
        pass

def is_update_available() -> tuple[bool, str | None, str | None]:
    """
    Check if an update is available.
    Returns: (update_available, current_version, latest_version)
    """
    current_v = get_current_version()

    # Try cache first
    latest_v = get_cached_latest_version()

    # If not in cache or expired, fetch from PyPI
    if not latest_v:
        latest_v = get_latest_version()
        if latest_v:
            save_cached_latest_version(latest_v)

    if current_v and latest_v:
        try:
            if version.parse(latest_v) > version.parse(current_v):
                return True, current_v, latest_v
        except version.InvalidVersion:
            log.warning(f"Invalid version string encountered: current={current_v}, latest={latest_v}")

    return False, current_v, latest_v

def update_package():
    """
    Update the package using pip.
    """
    package = PACKAGE_NAME
    # If we are in local dev (detected by checking if LOCAL_PACKAGE_NAME is installed but PACKAGE_NAME is not),
    # we might strictly want to update PACKAGE_NAME, but users might be confused.
    # However, the requirement is to update the CLI.
    # We will always try to install the main package name.

    log.info(f"Updating {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])
        typer.secho(f"Successfully updated {package}!", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError as e:
        typer.secho(f"Failed to update {package}. Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
