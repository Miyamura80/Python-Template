import importlib
import inspect
from types import ModuleType

from src.db.models import Base
from loguru import logger as log

# Programmatically import all models from the public schema
# Subclasses of Base:
TableType = Base


def _discover_models() -> list[TableType]:
    """Dynamically discover and import all SQLAlchemy models from the public schema."""
    models: list[TableType] = []

    # Import the public schema package
    public_package: ModuleType = importlib.import_module("src.db.models.public")  # type: ignore

    # Get all attributes from the public package
    for name in dir(public_package):
        obj = getattr(public_package, name)

        # Check if it's a SQLAlchemy model class (inherits from Base and has __tablename__)
        if (
            inspect.isclass(obj)
            and hasattr(obj, "__tablename__")
            and issubclass(obj, Base)
            and obj != Base
        ):
            log.info(f"Found model: {obj.__tablename__}")
            models.append(obj)  # type: ignore

    return models


# List of all model classes that we have responsibility over for migrations
# This includes only models in the 'public' schema that we manage via Alembic
MANAGED_MODELS: list[TableType] = _discover_models()