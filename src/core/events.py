"""Application-wide PySide6 signal hub for batmanoverlay."""

from PySide6.QtCore import QObject, Signal


class AppSignals(QObject):
    """Central signal hub. One instance per application."""

    # Config signals
    config_changed = Signal(str, object)  # (key_path, new_value)

    # Window signals
    panel_changed = Signal(str)  # panel_name
    geometry_changed = Signal(object)  # WindowGeometry

    # Theme signals
    theme_changed = Signal(str)  # "dark" | "light" | "system"

    # Status & Toast signals
    status_message = Signal(str)  # message
    toast_requested = Signal(str, str)  # (level, message)

    # Clipboard signals
    clipboard_item_added = Signal(str)  # item_id
    clipboard_item_deleted = Signal(str)  # item_id
    clipboard_cleared = Signal()  # empty
