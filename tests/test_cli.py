from src.cli.main import run, update
from unittest.mock import patch, MagicMock

@patch('requests.get')
def test_cli_run(mock_get, capsys):
    """
    Tests that the eito run command works with typer.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "pong"
    mock_get.return_value = mock_response

    run()

    captured = capsys.readouterr()
    assert "pong" in captured.out

@patch('src.cli.main.update_package')
def test_cli_update(mock_update):
    """
    Tests that the eito update command calls update_package.
    """
    update()
    mock_update.assert_called_once()
