"""The client type"""

import importlib.metadata
from contextlib import AbstractContextManager
from importlib.resources import as_file, files
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

        source = files(self.distribution).joinpath(resource)
        return as_file(source)
