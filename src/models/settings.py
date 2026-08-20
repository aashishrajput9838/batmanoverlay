"""AppSettings Pydantic data model hierarchy."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GeneralSettings(BaseModel):
    language: str = "en"
    check_updates: bool = True
    restore_session: bool = True
    default_workspace: str = "default"


class TypingSettings(BaseModel):
    default_speed: int = Field(default=5, ge=1, le=10)
    pre_typing_delay: int = Field(default=3, ge=1, le=10)
    jitter_enabled: bool = True
    jitter_range: float = Field(default=0.15, ge=0.05, le=0.25)


class AppearanceSettings(BaseModel):
    theme: str = Field(default="system", pattern=r"^(dark|light|system)$")
    accent_color: str = Field(default="#5B8DEF", pattern=r"^#[0-9a-fA-F]{6}$")
    font_family: str = "Inter"
    font_scale: float = Field(default=1.0, ge=0.8, le=2.0)
    default_opacity: float = Field(default=1.0, ge=0.1, le=1.0)
    overlay_transparency: float = Field(default=0.0, ge=0.0, le=99.99)
    hide_from_capture: bool = True

    @field_validator("overlay_transparency", mode="before")
    @classmethod
    def normalize_transparency(cls, v: Any) -> float:
        """Clamp legacy setting values > 99.99 down to 99.99."""
        if isinstance(v, (int, float)):
            return round(max(0.0, min(99.99, float(v))), 2)
        return 0.0


class BrowserSettings(BaseModel):
    home_page: str = "about:blank"
    user_agent: str | None = None
    javascript_enabled: bool = True
    cookies_enabled: bool = True
    proxy: str = "system"


class DownloadSettings(BaseModel):
    directory: str | None = None
    ask_before_download: bool = True
    show_notifications: bool = True


class ClipboardSettings(BaseModel):
    max_entries: int = Field(default=10000, ge=100)
    auto_archive: bool = True
    default_sort: str = Field(default="recency", pattern=r"^(recency|alphabetical|category)$")


class AccessibilitySettings(BaseModel):
    screen_reader: str = Field(default="auto", pattern=r"^(auto|enabled|disabled)$")
    high_contrast: bool = False
    reduce_animations: bool = False
    focus_indicators: bool = True


class ScreenshotSettings(BaseModel):
    screen_selection: str = Field(default="ask", pattern=r"^(ask|primary|all|[0-9]+)$")
    save_directory: str | None = None


class AppSettings(BaseModel):
    """Root Application Settings model."""

    model_config = ConfigDict(validate_assignment=True)

    version: int = 1
    general: GeneralSettings = Field(default_factory=GeneralSettings)
    typing: TypingSettings = Field(default_factory=TypingSettings)
    appearance: AppearanceSettings = Field(default_factory=AppearanceSettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    downloads: DownloadSettings = Field(default_factory=DownloadSettings)
    clipboard: ClipboardSettings = Field(default_factory=ClipboardSettings)
    accessibility: AccessibilitySettings = Field(default_factory=AccessibilitySettings)
    screenshot: ScreenshotSettings = Field(default_factory=ScreenshotSettings)
