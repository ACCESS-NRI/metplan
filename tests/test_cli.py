import pytest

import metplan.cli as mc
from metplan import __version__
from metplan.metplan import run_met


@pytest.fixture
def parser():
    return mc.get_parser(run_met)


def test_version(parser, capsys):
    """Test metplan -V"""
    # Ensure we catch the system exit
    with pytest.raises(SystemExit) as exc_info:
        args = parser.parse_args(["-V"])

    # Clean exit
    assert exc_info.value.code == 0

    # Correct output
    captured = capsys.readouterr()
    assert f"metplan {__version__}" in captured.out
