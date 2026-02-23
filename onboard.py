"""Interactive onboarding CLI for project setup."""

import re
import shutil
import subprocess
from pathlib import Path

import questionary
import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel

console = Console()

PROJECT_ROOT = Path(__file__).parent

app = typer.Typer(
    name="onboard",
    help="Interactive onboarding CLI for project setup.",
    invoke_without_command=True,
)


def _read_pyproject_name() -> str:
    """Read the current project name from pyproject.toml."""
    text = (PROJECT_ROOT / "pyproject.toml").read_text()
    match = re.search(r'^name\s*=\s*"([^"]*)"', text, re.MULTILINE)
    return match.group(1) if match else ""


def _validate_kebab_case(value: str) -> bool | str:
    """Validate that the value is kebab-case (lowercase, hyphens, no spaces)."""
    if not value:
        return "Project name cannot be empty."
    if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", value):
        return "Must be kebab-case (e.g. my-cool-project). Lowercase letters, digits, hyphens only."
    return True


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Run the full onboarding flow, or use a subcommand for a specific step."""
    if ctx.invoked_subcommand is None:
        rprint("[yellow]Full onboarding flow not yet implemented.[/yellow]")


@app.command()
def rename() -> None:
    """Step 1: Rename the project and update metadata."""
    current_name = _read_pyproject_name()
    if current_name != "python-template":
        rprint(
            f"[blue]ℹ Project already renamed to '{current_name}'. Skipping rename step.[/blue]"
        )
        return

    name = questionary.text(
        "Project name (kebab-case):",
        validate=_validate_kebab_case,
    ).ask()
    if name is None:
        raise typer.Abort()

    description = questionary.text("Project description:").ask()
    if description is None:
        raise typer.Abort()

    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    pyproject_text = pyproject_path.read_text()
    pyproject_text = pyproject_text.replace(
        'name = "python-template"', f'name = "{name}"'
    )
    if description:
        pyproject_text = pyproject_text.replace(
            'description = "Add your description here"',
            f'description = "{description}"',
        )
    pyproject_path.write_text(pyproject_text)

    readme_path = PROJECT_ROOT / "README.md"
    readme_text = readme_path.read_text()
    readme_text = readme_text.replace("# Python-Template", f"# {name}", 1)
    if description:
        readme_text = readme_text.replace(
            "<b>Opinionated Python project stack. 🔋 Batteries included. </b>",
            f"<b>{description}</b>",
            1,
        )
    readme_path.write_text(readme_text)

    changes = [f"[green]pyproject.toml[/green] name → {name}"]
    if description:
        changes.append(f"[green]pyproject.toml[/green] description → {description}")
    changes.append(f"[green]README.md[/green] heading → # {name}")
    if description:
        changes.append(f"[green]README.md[/green] tagline → {description}")

    rprint(Panel("\n".join(changes), title="✅ Rename Complete", border_style="green"))


@app.command()
def deps() -> None:
    """Step 2: Install project dependencies."""
    if not shutil.which("uv"):
        rprint(
            "[red]✗ uv is not installed.[/red]\n"
            "  Install it from: [link=https://docs.astral.sh/uv]https://docs.astral.sh/uv[/link]"
        )
        raise typer.Exit(code=1)

    venv_path = PROJECT_ROOT / ".venv"
    if not venv_path.is_dir():
        with console.status("[yellow]Creating virtual environment...[/yellow]"):
            result = subprocess.run(
                ["uv", "venv"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                rprint(f"[red]✗ Failed to create venv:[/red]\n{result.stderr}")
                raise typer.Exit(code=1)
        rprint("[green]✓[/green] Virtual environment created.")

    with console.status("[yellow]Installing dependencies (uv sync)...[/yellow]"):
        result = subprocess.run(
            ["uv", "sync"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        rprint(f"[red]✗ uv sync failed:[/red]\n{result.stderr}")
        raise typer.Exit(code=1)

    rprint("[green]✓ Dependencies installed successfully.[/green]")


def _is_secret_key(name: str) -> bool:
    """Check if an env var name suggests a secret value."""
    return any(word in name.upper() for word in ("SECRET", "KEY", "TOKEN", "PASSWORD"))


def _parse_env_example() -> list[dict[str, str]]:
    """Parse .env.example into a list of entries with group, key, and default value.

    Returns a list of dicts with keys: 'group', 'key', 'default'.
    Comment-only lines set the current group. Blank lines are skipped.
    """
    env_example_path = PROJECT_ROOT / ".env.example"
    if not env_example_path.exists():
        return []

    entries: list[dict[str, str]] = []
    current_group = "General"

    for line in env_example_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            current_group = line.lstrip("# ").strip()
            continue
        if "=" in line:
            key, _, default = line.partition("=")
            entries.append(
                {"group": current_group, "key": key.strip(), "default": default.strip()}
            )

    return entries


def _load_existing_env() -> dict[str, str]:
    """Load existing .env file into a dict."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return {}

    result: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def _has_real_value(value: str) -> bool:
    """Check if an env var value is a real (non-placeholder) value."""
    if not value:
        return False
    placeholders = {
        "sk-...",
        "sk-ant-...",
        "xai-...",
        "gsk_...",
        "pplx-...",
        "AIza...",
        "csk-...",
        "sk-lf-...",
        "pk-lf-...",
        "sk_test_...",
        "ghp_...",
        "postgresql://user:pass@host:port/db",
        "https://your-project.supabase.co",
    }
    return value not in placeholders


def _build_env_choices(
    entries: list[dict[str, str]], existing: dict[str, str]
) -> list[questionary.Choice]:
    """Build questionary checkbox choices from env entries."""
    choices = []
    for entry in entries:
        key = entry["key"]
        has_value = _has_real_value(existing.get(key, ""))
        label = f"[{entry['group']}] {key}"
        if has_value:
            label += " (configured)"
        choices.append(questionary.Choice(title=label, value=key, checked=has_value))
    return choices


def _prompt_env_value(key: str, default: str, current_value: str) -> str:
    """Prompt the user for a single env var value, handling existing values."""
    if _has_real_value(current_value):
        keep = questionary.confirm(
            f"{key} already has a value. Keep existing value?",
            default=True,
        ).ask()
        if keep is None:
            raise typer.Abort()
        if keep:
            return current_value

    prompt_fn = questionary.password if _is_secret_key(key) else questionary.text
    default_hint = default if not _is_secret_key(key) else ""
    new_value = prompt_fn(f"{key}:", default=default_hint).ask()
    if new_value is None:
        raise typer.Abort()
    return new_value


def _write_env_file(entries: list[dict[str, str]], values: dict[str, str]) -> int:
    """Write .env file preserving group structure. Returns count of skipped keys."""
    lines: list[str] = []
    current_group = ""
    skipped = 0

    for entry in entries:
        if entry["group"] != current_group:
            if lines:
                lines.append("")
            lines.append(f"# {entry['group']}")
            current_group = entry["group"]

        key = entry["key"]
        if key in values:
            lines.append(f"{key}={values[key]}")
        else:
            lines.append(f"# {key}={entry['default']}")
            skipped += 1

    (PROJECT_ROOT / ".env").write_text("\n".join(lines) + "\n")
    return skipped


@app.command()
def env() -> None:
    """Step 3: Configure environment variables."""
    entries = _parse_env_example()
    if not entries:
        rprint("[red]✗ No .env.example found.[/red]")
        raise typer.Exit(code=1)

    existing = _load_existing_env()
    choices = _build_env_choices(entries, existing)

    selected_keys = questionary.checkbox(
        "Select environment variables to configure:",
        choices=choices,
    ).ask()
    if selected_keys is None:
        raise typer.Abort()

    selected_set = set(selected_keys)
    values: dict[str, str] = {}
    for entry in entries:
        key = entry["key"]
        if key not in selected_set:
            continue
        values[key] = _prompt_env_value(key, entry["default"], existing.get(key, ""))

    skipped = _write_env_file(entries, values)
    configured = len(values)

    rprint(
        f"\n[green]✓ {configured} key(s) configured, {skipped} key(s) skipped.[/green]"
    )


@app.command()
def hooks() -> None:
    """Step 4: Activate pre-commit hooks."""
    rprint("[yellow]Step 4 (hooks) not yet implemented.[/yellow]")


@app.command()
def media() -> None:
    """Step 5: Generate banner and logo assets."""
    rprint("[yellow]Step 5 (media) not yet implemented.[/yellow]")


if __name__ == "__main__":
    app()
