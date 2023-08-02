"""Installation tests"""


from pathlib import Path

from packaging.version import Version

from synodic_client.client import Client


class TestInstall:
    """Install tests"""

    def test_version(self) -> None:
        """Verify that the imported package version can be read"""

        client = Client()

        # The test should be running inside a PDM virtual environment which means that
        #   the package has the version metadata
        version = client.version

        assert version > Version("0.0.0")

    def test_data(self) -> None:
        """Verify that all the files in 'static' can be read"""

        client = Client()

        directory = Path("data")

        assert directory.is_dir()

        paths = directory.rglob("*")

        for file in paths:
            file_string = str(file.name)
            with client.resource(file_string) as path:
                assert path.name == file.name
