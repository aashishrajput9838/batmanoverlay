"""Browser Domain Data Models for batmanoverlay."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class BrowserSecurityLevel(StrEnum):
    """Enumeration of browser security levels."""

    STRICT = "strict"
    STANDARD = "standard"
    PERMISSIVE = "permissive"


class NavigationState(BaseModel):
    """Domain model representing current web navigation state."""

    url: str = "about:blank"
    title: str = ""
    is_loading: bool = False
    progress: int = 0
    is_secure: bool = True
    can_go_back: bool = False
    can_go_forward: bool = False


class BrowserTabModel(BaseModel):
    """Domain model representing a single browser tab."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str = "about:blank"
    title: str = "New Tab"
    icon_url: str | None = None
    is_pinned: bool = False
    is_muted: bool = False
    security_level: BrowserSecurityLevel = BrowserSecurityLevel.STANDARD


class BrowserProfile(BaseModel):
    """Domain model representing a browser storage profile configuration."""

    profile_id: str
    name: str
    data_dir: Path
    cache_dir: Path
    cookies_dir: Path
    history_dir: Path
    downloads_dir: Path
    sessions_dir: Path


class BrowserSession(BaseModel):
    """Domain model representing a persisted browser session."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str = "default"
    open_tabs: list[BrowserTabModel] = Field(default_factory=list)
    active_tab_index: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
