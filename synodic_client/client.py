"""The client type"""
import importlib.metadata
import importlib.resources
from contextlib import AbstractContextManager
from pathlib import Path
from typing import LiteralString

from packaging.version import Version


class Client:
    """The client"""

    distribution: LiteralString = "synodic_client"

    @property
    def version(self) -> Version:
        """Extracts the version from the installed client

        Returns:
            The version data
        """

        return Version(importlib.metadata.version(self.distribution))

    @property
    def package(self) -> str:
        """Returns the client package

        Returns:
            The package name
        """
        return self.distribution

    def resource(self, resource: str) -> AbstractContextManager[Path]:
        """_summary_

        Args:
            resource: _description_

        Returns:
            _description_
        """
        return importlib.resources.path(self.distribution, resource)
