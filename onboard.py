"""Interactive onboarding CLI for project setup."""

import typer
from rich import print as rprint

app = typer.Typer(
    name="onboard",
    help="Interactive onboarding CLI for project setup.",
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Run the full onboarding flow, or use a subcommand for a specific step."""
    if ctx.invoked_subcommand is None:
        rprint("[yellow]Full onboarding flow not yet implemented.[/yellow]")


@app.command()
def rename() -> None:
    """Step 1: Rename the project and update metadata."""
    rprint("[yellow]Step 1 (rename) not yet implemented.[/yellow]")


@app.command()
def deps() -> None:
    """Step 2: Install project dependencies."""
    rprint("[yellow]Step 2 (deps) not yet implemented.[/yellow]")


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
