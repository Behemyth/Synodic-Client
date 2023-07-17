"""The client type"""
import importlib.metadata
import importlib.resources


class Client:
    """The client"""

    @property
    def version(self) -> str:
        """_summary_

        Returns:
            _description_
        """
        try:
            return importlib.metadata.version(__package__)
        except importlib.metadata.PackageNotFoundError:
            with (importlib.resources.files("synodic_client") / "VERSION").open("r", encoding="utf-8") as file:
                return file.read().strip()
