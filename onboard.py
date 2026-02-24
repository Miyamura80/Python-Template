"""Interactive onboarding CLI for project setup."""

import asyncio
import os
import re
import shutil
import subprocess
from pathlib import Path

import questionary
import typer
import yaml
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from init.generate_banner import generate_banner as gen_banner
from init.generate_logo import generate_logo as gen_logo

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


STEPS: list[tuple[str, str]] = [
    ("Rename", "rename"),
    ("Dependencies", "deps"),
    ("Environment Variables", "env"),
    ("Pre-commit Hooks", "hooks"),
    ("Media Generation", "media"),
]

STEP_FUNCTIONS: dict[str, object] = {}


def _run_orchestrator() -> None:
    """Run the full onboarding flow, executing all steps in sequence."""
    project_name = _read_pyproject_name()
    rprint(
        Panel(
            f"[bold]{project_name}[/bold]\n\n"
            "This wizard will guide you through:\n"
            "  1. Rename - Set project name and description\n"
            "  2. Dependencies - Install project dependencies\n"
            "  3. Environment - Configure API keys and secrets\n"
            "  4. Hooks - Activate pre-commit hooks\n"
            "  5. Media - Generate banner and logo assets",
            title="Welcome to Project Onboarding",
            border_style="blue",
        )
    )

    total = len(STEPS)
    completed: list[str] = []
    skipped: list[str] = []

    for i, (label, cmd_name) in enumerate(STEPS, 1):
        rprint(f"\n[bold cyan]--- Step {i}/{total}: {label} ---[/bold cyan]")
        answer = questionary.select(
            "Run this step?",
            choices=["Yes", "Skip"],
            default="Yes",
        ).ask()
        if answer is None:
            raise typer.Abort()

        if answer == "Skip":
            skipped.append(label)
            rprint(f"[yellow]- {label} skipped[/yellow]")
            continue

        try:
            step_fn = STEP_FUNCTIONS[cmd_name]
            step_fn()  # type: ignore[operator]
            completed.append(label)
        except (typer.Exit, SystemExit) as exc:
            code = getattr(exc, "code", getattr(exc, "exit_code", 1))
            if code and code != 0:
                rprint(f"[red]✗ {label} failed.[/red]")
                cont = questionary.confirm(
                    "Continue with remaining steps?", default=True
                ).ask()
                if cont is None or not cont:
                    raise typer.Abort() from None
                skipped.append(f"{label} (failed)")
            else:
                completed.append(label)

    _print_summary(completed, skipped)


def _print_summary(completed: list[str], skipped: list[str]) -> None:
    """Print the final onboarding summary."""
    lines: list[str] = []
    for name in completed:
        lines.append(f"[green]✓[/green] {name}")
    for name in skipped:
        lines.append(f"[yellow]-[/yellow] {name}")
    lines.append("")
    lines.append("[bold]Suggested next commands:[/bold]")
    lines.append("  make test    - Run tests")
    lines.append("  make ci      - Run CI checks")
    lines.append("  make all     - Run main application")

    rprint(Panel("\n".join(lines), title="Onboarding Summary", border_style="green"))


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Run the full onboarding flow, or use a subcommand for a specific step."""
    if ctx.invoked_subcommand is None:
        _run_orchestrator()


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
    config_path = PROJECT_ROOT / ".pre-commit-config.yaml"
    if not config_path.exists():
        rprint("[red]✗ .pre-commit-config.yaml not found.[/red]")
        raise typer.Exit(code=1)

    config = yaml.safe_load(config_path.read_text())

    table = Table(title="Configured Pre-commit Hooks")
    table.add_column("Hook ID", style="cyan")
    table.add_column("Description", style="white")

    for repo in config.get("repos", []):
        for hook in repo.get("hooks", []):
            hook_id = hook.get("id", "unknown")
            hook_name = hook.get("name", hook_id)
            table.add_row(hook_id, hook_name)

    console.print(table)
    rprint("")

    activate = questionary.confirm(
        "Activate pre-commit hooks? (Recommended)",
        default=True,
    ).ask()
    if activate is None:
        raise typer.Abort()

    if activate:
        result = subprocess.run(
            ["uv", "run", "pre-commit", "install"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            rprint(f"[red]✗ Failed to activate hooks:[/red]\n{result.stderr}")
            raise typer.Exit(code=1)
        rprint("[green]✓ Pre-commit hooks activated.[/green]")
    else:
        rprint(
            "[yellow]Skipped.[/yellow] You can activate later with: "
            "[bold]pre-commit install[/bold]"
        )


def _check_gemini_key() -> bool:
    """Check if GEMINI_API_KEY is available in .env or environment."""
    if os.environ.get("GEMINI_API_KEY"):
        return True
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                value = line.split("=", 1)[1].strip()
                return _has_real_value(value)
    return False


def _run_media_generation(choice: str, project_name: str, theme: str) -> list[str]:
    """Run the selected media generation and return list of generated file paths."""
    generated_files: list[str] = []

    if choice in ("Banner only", "Both"):
        with console.status("[yellow]Generating banner...[/yellow]"):
            asyncio.run(gen_banner(title=project_name, theme=theme))
        banner_path = PROJECT_ROOT / "media" / "banner.png"
        generated_files.append(str(banner_path))
        rprint(f"[green]✓[/green] Banner saved to {banner_path}")

    if choice in ("Logo only", "Both"):
        with console.status("[yellow]Generating logo...[/yellow]"):
            asyncio.run(gen_logo(project_name=project_name, theme=theme))
        logo_dir = PROJECT_ROOT / "docs" / "public"
        for name in (
            "logo-light.png",
            "logo-dark.png",
            "icon-light.png",
            "icon-dark.png",
            "favicon.ico",
        ):
            generated_files.append(str(logo_dir / name))
        rprint(f"[green]✓[/green] Logo assets saved to {logo_dir}")

    return generated_files


@app.command()
def media() -> None:
    """Step 5: Generate banner and logo assets."""
    if not _check_gemini_key():
        rprint("[yellow]⚠ GEMINI_API_KEY is not configured.[/yellow]")
        skip = questionary.confirm("Skip media generation?", default=True).ask()
        if skip is None:
            raise typer.Abort()
        if skip:
            rprint("[yellow]Media generation skipped.[/yellow]")
            return

    project_name = _read_pyproject_name()

    rprint()
    theme = questionary.text(
        "Describe the visual theme/style for your project assets:",
        default="modern, clean, minimalist tech aesthetic",
    ).ask()
    if theme is None:
        raise typer.Abort()

    choice = questionary.select(
        "What would you like to generate?",
        choices=["Both", "Banner only", "Logo only", "Skip"],
        default="Both",
    ).ask()
    if choice is None:
        raise typer.Abort()

    if choice == "Skip":
        rprint("[yellow]Media generation skipped.[/yellow]")
        return

    generated_files = _run_media_generation(choice, project_name, theme)
    rprint("\n[green]Generated files:[/green]")
    for f in generated_files:
        rprint(f"  {f}")


# Register step functions for the orchestrator
STEP_FUNCTIONS.update(
    {
        "rename": rename,
        "deps": deps,
        "env": env,
        "hooks": hooks,
        "media": media,
    }
)

if __name__ == "__main__":
    app()
