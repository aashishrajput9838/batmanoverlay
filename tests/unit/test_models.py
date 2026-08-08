"""Unit tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from src.models.settings import AppearanceSettings, AppSettings, TypingSettings


@pytest.mark.unit
def test_app_settings_defaults() -> None:
    settings = AppSettings()
    assert settings.version == 1
    assert settings.typing.default_speed == 5
    assert settings.appearance.theme == "system"


@pytest.mark.unit
def test_typing_settings_bounds() -> None:
    # Valid
    s = TypingSettings(default_speed=1, pre_typing_delay=10)
    assert s.default_speed == 1

    # Invalid speed low
    with pytest.raises(ValidationError):
        TypingSettings(default_speed=0)

    # Invalid speed high
    with pytest.raises(ValidationError):
        TypingSettings(default_speed=11)


@pytest.mark.unit
def test_appearance_settings_overlay_transparency_bounds() -> None:
    """Verify overlay_transparency range [0.0..99.99] and legacy clamping."""
    # Valid bounds
    s1 = AppearanceSettings(overlay_transparency=0)
    assert s1.overlay_transparency == 0.0

    s2 = AppearanceSettings(overlay_transparency=99.99)
    assert s2.overlay_transparency == 99.99

    # Integer values 25, 50, 75, 99 remain valid
    s3 = AppearanceSettings(overlay_transparency=50)
    assert s3.overlay_transparency == 50.0

    # Legacy 100% normalized to 99.99
    s4 = AppearanceSettings(overlay_transparency=100)
    assert s4.overlay_transparency == 99.99
