"""Session and window geometry models for batmanoverlay."""

from pydantic import BaseModel, Field


class WindowGeometry(BaseModel):
    """Window position, dimensions, opacity, and overlay state."""

    x: int = 100
    y: int = 100
    width: int = 1024
    height: int = 768
    opacity: float = Field(default=1.0, ge=0.1, le=1.0)
    is_collapsed: bool = False
    is_pinned: bool = False
    is_always_on_top: bool = True
    active_panel: str = "settings"
