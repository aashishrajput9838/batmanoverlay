"""Unit tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from src.models.settings import AppSettings, TypingSettings


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
