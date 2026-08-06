"""Unit tests for ConfigManager."""

from pathlib import Path

import pytest

from src.core.config_manager import ConfigManager


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_config_manager_default_creation(tmp_data_dir: Path) -> None:
    config_mgr = ConfigManager(tmp_data_dir)
    settings = config_mgr.settings()

    assert settings.version == 1
    assert settings.general.language == "en"
    assert config_mgr.get("general.language") == "en"
    assert config_mgr.get("typing.default_speed") == 5


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_config_manager_update_setting(tmp_data_dir: Path) -> None:
    config_mgr = ConfigManager(tmp_data_dir)
    changed_keys: list[tuple[str, object]] = []

    config_mgr.config_changed.connect(lambda k, v: changed_keys.append((k, v)))

    config_mgr.set("typing.default_speed", 8)
    assert config_mgr.get("typing.default_speed") == 8
    assert len(changed_keys) == 1
    assert changed_keys[0] == ("typing.default_speed", 8)

    # Re-instantiate to verify persistence
    new_config_mgr = ConfigManager(tmp_data_dir)
    assert new_config_mgr.get("typing.default_speed") == 8


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_config_manager_corrupted_file_recovery(
    tmp_data_dir: Path,
) -> None:
    config_dir = tmp_data_dir / "config"
    settings_file = config_dir / "settings.json"
    settings_file.write_text("{CORRUPTED JSON", encoding="utf-8")

    config_mgr = ConfigManager(tmp_data_dir)
    assert config_mgr.get("general.language") == "en"
    assert (config_dir / "settings.json.bak").exists()
