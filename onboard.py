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


@app.command()
def env() -> None:
    """Step 3: Configure environment variables."""
    rprint("[yellow]Step 3 (env) not yet implemented.[/yellow]")


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
