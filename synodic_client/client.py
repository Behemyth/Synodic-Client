"""The client type"""
import importlib.metadata
import importlib.resources

from packaging.version import Version


class Client:
    """The client"""

    @property
    def version(self) -> Version:
        """Extracts the version from the installed client

        Returns:
            The version data
        """
        try:
            return Version(importlib.metadata.version(__package__))
        except importlib.metadata.PackageNotFoundError:
            with (importlib.resources.files("synodic_client") / "VERSION").open("r", encoding="utf-8") as file:
                return Version(file.read().strip())
