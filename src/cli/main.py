import typer
import requests
from src.utils.logging_config import setup_logging
from src.utils.version import update_package, is_update_available

# Initialize logging
setup_logging()

app = typer.Typer()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Eito CLI
    """
    # Check for updates, but skip if we are running the update command
    if ctx.invoked_subcommand == "update":
        return

    try:
        available, current, latest = is_update_available()
        if available:
            typer.secho(
                f"\nUpdate available: {current} -> {latest}\nRun 'eito update' to upgrade.\n",
                fg=typer.colors.YELLOW,
                err=True
            )
    except Exception:
        # Don't let update check crash the app
        pass

    # If no subcommand was invoked (e.g. just `eito`), show help
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()

@app.command()
def update():
    """
    Update the CLI to the latest version.
    """
    update_package()

@app.command()
def run():
    """
    Pings app.eito.me/ping and prints the response.
    """
    try:
        response = requests.get("https://app.eito.me/ping")
        response.raise_for_status()  # Raise an exception for bad status codes
        print(response.text)
    except requests.RequestException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    app()
