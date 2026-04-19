"""The `spurtle` package provides the core functionality for the Synodic Client application."""

import importlib.metadata

from spurtle.client import Client
from spurtle.schema import (
    UpdateChannel,
    UpdateConfig,
    UpdateInfo,
    UpdateState,
)
from spurtle.updater import Updater

try:
    __version__ = importlib.metadata.version('spurtle')
except importlib.metadata.PackageNotFoundError:
    __version__ = '0.0.0.dev0'

__all__ = [
    '__version__',
    'Client',
    'UpdateChannel',
    'UpdateConfig',
    'UpdateInfo',
    'UpdateState',
    'Updater',
]
