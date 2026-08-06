"""Protocol definitions for batmanoverlay module boundaries."""

from typing import Any, Protocol, runtime_checkable

from src.models.settings import AppSettings


@runtime_checkable
class ConfigProviderProtocol(Protocol):
    """Protocol for reading configuration settings."""

    def get(self, key_path: str, default: Any = None) -> Any: ...
    def settings(self) -> AppSettings: ...
