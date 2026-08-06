"""Core services package for batmanoverlay."""

from src.core.config_manager import ConfigManager
from src.core.events import AppSignals
from src.core.exceptions import BatmanOverlayError
from src.core.logger import setup_logging
from src.core.protocols import ConfigProviderProtocol

__all__ = [
    "AppSignals",
    "BatmanOverlayError",
    "ConfigManager",
    "ConfigProviderProtocol",
    "setup_logging",
]
