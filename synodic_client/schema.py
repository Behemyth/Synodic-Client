"""Schema for the client"""

from pydantic import BaseModel


class VersionInformation(BaseModel):
    """Comparable information that can be extracted from a Python package"""

    version: str
