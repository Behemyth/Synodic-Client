"""Schema for the client"""

from pydantic import BaseModel


class VersionInformation(BaseModel):
    """_summary_"""

    version: str
