"""The client type"""
import importlib.metadata
import importlib.resources
from contextlib import AbstractContextManager
from pathlib import Path

from packaging.version import Version


class Client:
    """The client"""

    @property
    def version(self) -> Version:
        """Extracts the version from the installed client

        Returns:
            The version data
        """

        return Version(importlib.metadata.version(__package__))

    def resource(self, resource: str) -> AbstractContextManager[Path]:
        """_summary_

        Args:
            resource: _description_

        Returns:
            _description_
        """
        return importlib.resources.path(__package__, resource)
