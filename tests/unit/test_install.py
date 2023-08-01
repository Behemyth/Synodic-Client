"""Installation tests"""


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
