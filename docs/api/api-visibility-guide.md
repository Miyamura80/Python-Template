# API Visibility Guide

This guide explains how to mark code as public-facing or private/internal in this codebase.

## Overview

The codebase uses markers and naming conventions to distinguish between:
- **Public APIs**: User-facing code that should be documented in `/docs`
- **Private/Internal code**: Implementation details that only need docstrings

This is defined in `.cursor/docs-scope.yml` and enforced by `.cursor/rules/documentation.mdc`.

## Naming Conventions

### Public APIs (Documented in /docs)

```python
# ✅ Public function (no leading underscore)
def calculate_total(items: list) -> float:
    """Calculate the total price of items.

    This is a public API - documented in docs/api/
    """
    pass

# ✅ Public class (PascalCase, no underscore)
class GlobalConfig:
    """Global configuration manager.

    Public API - documented in docs/api/common.md
    """
    pass
```

### Private/Internal APIs (Docstrings only)

```python
# ❌ Private function (leading underscore)
def _internal_helper(data: dict) -> str:
    """Internal helper function. Not part of public API."""
    # Internal only - no /docs needed
    pass

# ❌ Private class (leading underscore)
class _InternalCache:
    """Internal caching mechanism. Not for external use."""
    pass
```

## Explicit Markers

You can also use explicit markers in comments:

### Public API Marker

```python
# Public API
def export_data(format: str) -> bytes:
    """Export data in the specified format.

    This marker indicates this should be documented in /docs
    even if there might be ambiguity.
    """
    pass
```

### Internal Marker

```python
# Internal only
def _process_queue():
    """Process internal message queue.

    This marker indicates this is internal and should NOT
    be documented in /docs.
    """
    pass
```

## Module-Level Visibility

### Public Modules

Defined in `.cursor/docs-scope.yml` under `public_modules`:

```
public_modules:
  - path: "common/"
    description: "Shared utilities and global configuration"
    doc_level: "comprehensive"
```

All exports from public modules should be documented in `/docs`.

**Example - common/global_config.py:**

```python
"""Global configuration module.

This is a public module. All exported functions and classes
should be documented in docs/api/common.md.
"""

# Public API
class GlobalConfig:
    """Global configuration manager."""

    def get_value(self, key: str):
        """Get a configuration value.

        Args:
            key: Configuration key

        Returns:
            Configuration value
        """
        pass

# Public API
def load_config(path: str) -> GlobalConfig:
    """Load configuration from file."""
    pass

# Internal only - not exported
def _validate_schema(config: dict) -> bool:
    """Internal validation helper."""
    pass
```

### Private Modules

Defined in `.cursor/docs-scope.yml` under `private_modules`:

```
private_modules:
  - path: "src/utils/"
    description: "Internal utilities"
    doc_level: "minimal"
```

Code in private modules only needs docstrings, not `/docs` files.

**Example - src/utils/logging_config.py:**

```python
"""Internal logging configuration utilities.

This is a private module. Only docstrings needed, no /docs files.
"""

# Internal only
def configure_logger(name: str):
    """Configure a logger instance."""
    pass
```

## Using `__all__` for Exports

Use `__all__` to explicitly define the public API of a module:

```python
# common/__init__.py

# Public API - These are exported
from .global_config import GlobalConfig, load_config

__all__ = [
    'GlobalConfig',
    'load_config',
]

# Anything not in __all__ is considered internal
```

## Documentation Requirements by Visibility

### Public APIs (in /docs)

```python
# Public API
class APIClient:
    """Client for interacting with the REST API.

    This is a public-facing class that users will import and use.

    Public API - documented in docs/api/client.md

    Attributes:
        base_url (str): Base URL for API requests
        timeout (int): Request timeout in seconds

    Example:
        >>> from api import APIClient
        >>> client = APIClient("https://api.example.com")
        >>> response = client.get("/users")

    See Also:
        - docs/api/client.md - Complete API reference
        - docs/guides/authentication.md - Authentication guide
    """

    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize the API client.

        Args:
            base_url: Base URL for API requests
            timeout: Request timeout in seconds (default: 30)
        """
        pass

    def get(self, endpoint: str) -> dict:
        """Make a GET request to the API.

        Args:
            endpoint: API endpoint path

        Returns:
            JSON response as dictionary

        Raises:
            APIError: If request fails

        Example:
            >>> client.get("/users/123")
            {'id': 123, 'name': 'John'}
        """
        pass
```

### Private/Internal APIs (docstrings only)

```python
# Internal only
def _retry_request(func, max_retries: int = 3):
    """Internal retry decorator for API requests.

    Args:
        func: Function to retry
        max_retries: Maximum retry attempts

    Returns:
        Wrapped function with retry logic
    """
    pass
```

## Module Structure Example

```
common/
├── __init__.py          # Public exports (✅ document in /docs)
├── global_config.py     # Public module (✅ document in /docs)
└── _internal.py         # Private module (❌ only docstrings)

src/
├── api/
│   ├── __init__.py      # Public API (✅ document in /docs)
│   └── client.py        # Public API (✅ document in /docs)
└── utils/
    ├── __init__.py      # Internal utils (❌ only docstrings)
    └── _helpers.py      # Internal (❌ only docstrings)

tests/
└── test_config.py       # Test code (❌ only docstrings)
```

## Quick Reference

| Pattern | Visibility | Documentation |
|---------|-----------|---------------|
| `def public_func()` | Public | ✅ /docs + docstrings |
| `def _private_func()` | Private | ❌ Docstrings only |
| `class PublicClass` | Public | ✅ /docs + docstrings |
| `class _PrivateClass` | Private | ❌ Docstrings only |
| In `public_modules` | Public | ✅ /docs + docstrings |
| In `private_modules` | Private | ❌ Docstrings only |
| In `__all__` | Public | ✅ /docs + docstrings |
| `# Public API` marker | Public | ✅ /docs + docstrings |
| `# Internal only` marker | Private | ❌ Docstrings only |

## Configuration Files

- **`.cursor/docs-scope.yml`**: Defines which modules are public vs private
- **`.cursor/rules/documentation.mdc`**: Documentation standards and rules
- **`.github/workflows/cursor_update_docs.yml`**: Automated docs update workflow

## Best Practices

1. **Use leading underscores** for private functions and classes
2. **Define `__all__`** in `__init__.py` to make public API clear
3. **Add markers** when visibility might be ambiguous
4. **Keep private modules** in separate files (e.g., `_internal.py`)
5. **Document comprehensively** for public APIs
6. **Document minimally** for private code (just docstrings)
7. **Update `.cursor/docs-scope.yml`** when adding new public modules

## Examples from this Codebase

### Public: `common/global_config.py`

This is in `public_modules` in docs-scope.yml, so it needs comprehensive documentation in `/docs/api/`.

### Private: `src/utils/logging_config.py`

This is in `private_modules`, so it only needs docstrings, not `/docs` files.

### Private: `tests/`

Test code is always considered private and doesn't need `/docs` documentation.

## For Cursor Agents

When updating documentation:

1. **Read** `.cursor/docs-scope.yml` first
2. **Check** if changed files are in `public_modules` or `private_modules`
3. **Only document** public modules in `/docs`
4. **Skip** private modules (they only need docstrings)
5. **Never modify** code files, only `/docs` files
