# Unnecessary Code Cleanup Guideline

This document defines the conservative rules Jules must follow when identifying
and removing unnecessary (dead) code from this repository.

## Philosophy

We prefer **false negatives over false positives**. It is better to leave
questionable code in place than to remove something that turns out to be needed.
Every removal must be justified with concrete evidence that the code is unused.

## What Counts as Unnecessary Code

- **Dead functions/methods/classes**: Defined but never called, imported, or
  referenced anywhere in the codebase (including tests).
- **Unused imports**: Imports that are not referenced in the file.
- **Commented-out code**: Blocks of commented-out Python/JS code (not
  explanatory comments or TODOs).
- **Unreachable code**: Code after unconditional `return`, `raise`, `break`, or
  `continue` statements.
- **Unused variables/constants**: Assigned but never read. Excludes `_`
  convention variables.
- **Stale compatibility shims**: Version checks or feature flags for versions
  no longer supported per `pyproject.toml` `requires-python`.

## Protected Patterns - NEVER Remove

The following patterns must **never** be removed, even if they appear unused by
static analysis:

1. **FastAPI/Starlette routes**: Any function decorated with `@app`, `@router`,
   or framework routing decorators.
2. **SQLAlchemy/Pydantic models**: Model classes, even if not directly imported
   elsewhere (they may be used via ORM relationships or migrations).
3. **Celery/RQ tasks**: Functions decorated with `@task`, `@shared_task`, or
   registered as background workers.
4. **Signal handlers and hooks**: Functions connected to framework signals,
   event hooks, or lifecycle callbacks.
5. **`__init__.py` exports**: Anything listed in `__all__` or imported in
   `__init__.py` for re-export.
6. **CLI entry points**: Functions referenced in `pyproject.toml`
   `[project.scripts]` or Typer/Click commands.
7. **Test fixtures**: pytest fixtures, conftest definitions, and test helper
   functions in `tests/`.
8. **Configuration classes**: Pydantic `Settings` or `BaseModel` subclasses in
   `common/`.
9. **Dunder methods**: `__str__`, `__repr__`, `__hash__`, `__eq__`, etc.
10. **Security-related code**: Authentication, authorization, rate limiting,
    input validation, and CSRF protection code.
11. **Migration files**: Database migration scripts.
12. **Protocol/ABC implementations**: Methods implementing an abstract base
    class or Protocol interface.
13. **Vulture whitelist entries**: Anything referenced in
    `pyproject.toml [tool.vulture]` exclusions.

## Validation Before Removal

For each piece of code you plan to remove, verify:

1. **No dynamic references**: Search for string-based lookups like `getattr()`,
   `importlib.import_module()`, `globals()`, or `locals()` that might reference it.
2. **No config references**: Check YAML, JSON, TOML, and `.env` files for
   references to the symbol name.
3. **No test references**: Search `tests/` directory for any usage.
4. **No documentation references**: Check that docs don't describe the code as
   part of the public API.
5. **No cross-repo usage**: If this is a library/package, the code may be used
   by consumers.

## PR Requirements

- Title format: `chore: prune unnecessary code (automated weekly cleanup)`
- Each removal must be listed in the PR description with:
  - File path and symbol name
  - Evidence it is unused (e.g., "zero references found in codebase")
- Group removals by file, not by type.
- If no unnecessary code is found, do **not** create a PR.
