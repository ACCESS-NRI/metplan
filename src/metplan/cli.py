"""Console script for metplan."""
import metplan

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def main():
    """Console script for metplan."""
    console.print("Replace this message by putting your code into "
               "metplan.cli.main")
    console.print("See Typer documentation at https://typer.tiangolo.com/")
    


if __name__ == "__main__":
    app()
