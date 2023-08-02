"""Test the click cli"""
from click.testing import CliRunner

from synodic_client.application.click import cli


class TestCLI:
    """_summary_"""

    def test_version(self) -> None:
        """_summary_"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert result.output
