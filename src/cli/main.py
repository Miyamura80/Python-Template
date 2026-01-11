import typer
import requests

app = typer.Typer()

@app.command()
def run():
    """
    Pings app.eito.me/ping and prints the response.
    """
    try:
        response = requests.get("https://app.eito.me/ping")
        response.raise_for_status()  # Raise an exception for bad status codes
        print(response.text)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    app()
