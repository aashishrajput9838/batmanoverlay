"""Production Typing UI Panel integrated with HumanTypingEngine."""

from typing import Any

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.core.events import AppSignals
from src.platform.models import TargetInfo
from src.typing.config import TypingConfig
from src.typing.engine import HumanTypingEngine
from src.ui.dialogs import TargetPreviewDialog
from src.ui.icons import IconManager


class TypingPanel(QWidget):
    """Production Typing Engine Control Panel interface."""

    def __init__(
        self,
        typing_engine: HumanTypingEngine,
        signals: AppSignals,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("TypingPanel")
        self._engine = typing_engine
        self._signals = signals

        self._active_job_id: str | None = None
        self._current_target: TargetInfo | None = None

        self._setup_ui()
        self._apply_initial_config()
        self._connect_signals()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. Header Toolbar Bar (Title, Status Badge, Action Buttons)
        # -------------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Title
        title_label = QLabel("<h2>Human Typing Engine</h2>", self)
        header_layout.addWidget(title_label)

        # Status Badge Pill
        self._lbl_status = QLabel("READY", self)
        self._lbl_status.setObjectName("StatusBadge")
        self._update_status_badge("READY", "#94E2D5", "#181825")
        header_layout.addWidget(self._lbl_status)

        header_layout.addStretch()

        # Action Buttons
        self._btn_start = QPushButton("Start Typing", self)
        self._btn_start.setIcon(IconManager.get_icon("chevron_right", "#11111B"))
        self._btn_start.setStyleSheet(
            "QPushButton { background-color: #89B4FA; color: #11111B; font-weight: bold; "
            "border-radius: 6px; padding: 8px 16px; } "
            "QPushButton:hover { background-color: #B4BEFE; } "
            "QPushButton:disabled { background-color: #45475A; color: #7F849C; }"
        )
        self._btn_start.clicked.connect(self._on_start_typing)
        header_layout.addWidget(self._btn_start)

        self._btn_pause = QPushButton("Pause", self)
        self._btn_pause.setEnabled(False)
        self._btn_pause.clicked.connect(self._on_pause_resume)
        header_layout.addWidget(self._btn_pause)

        self._btn_stop = QPushButton("Stop / Abort (ESC)", self)
        self._btn_stop.setIcon(IconManager.get_icon("stop", "#F38BA8"))
        self._btn_stop.setEnabled(False)
        self._btn_stop.setStyleSheet(
            "QPushButton { background-color: #313244; color: #F38BA8; border: 1px solid #F38BA8; "
            "border-radius: 6px; padding: 8px 14px; font-weight: bold; } "
            "QPushButton:hover { background-color: #45475A; } "
            "QPushButton:disabled { border-color: #45475A; color: #7F849C; }"
        )
        self._btn_stop.clicked.connect(self._on_stop_typing)
        header_layout.addWidget(self._btn_stop)

        main_layout.addLayout(header_layout)

        # -------------------------------------------------------------
        # 2. Main Content Split Area (Left Column: Input & Progress, Right: Controls & Target)
        # -------------------------------------------------------------
        split_layout = QHBoxLayout()
        split_layout.setSpacing(16)

        # ── LEFT COLUMN ──
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Text Input Card Group
        grp_text = QGroupBox("Input Text to Simulate", left_widget)
        grp_text_layout = QVBoxLayout(grp_text)
        grp_text_layout.setContentsMargins(12, 12, 12, 12)
        grp_text_layout.setSpacing(8)

        self._txt_input = QPlainTextEdit(grp_text)
        self._txt_input.setPlaceholderText(
            "Paste or type the text here that you wish to simulate character-by-character...\n\n"
            "Default Workflow:\n"
            "1. Click 'Start Typing'\n"
            "2. Countdown begins (10s default)\n"
            "3. Switch to any app (Notepad, VS Code, Browser, ChatGPT)\n"
            "4. Place cursor inside editable field\n"
            "5. Typing starts automatically!"
        )
        self._txt_input.textChanged.connect(self._on_text_changed)
        grp_text_layout.addWidget(self._txt_input, stretch=1)

        # Text Stats Footer
        txt_meta_layout = QHBoxLayout()
        self._lbl_text_stats = QLabel("0 characters | 0 words | 0 lines | Est: 0s", grp_text)
        txt_meta_layout.addWidget(self._lbl_text_stats)

        txt_meta_layout.addStretch()

        btn_clear = QPushButton("Clear Text", grp_text)
        btn_clear.clicked.connect(lambda: self._txt_input.clear())
        txt_meta_layout.addWidget(btn_clear)
        grp_text_layout.addLayout(txt_meta_layout)

        left_layout.addWidget(grp_text, stretch=1)

        # Live Countdown Card (Hidden when inactive)
        self._card_countdown = QFrame(left_widget)
        self._card_countdown.setFrameShape(QFrame.Shape.StyledPanel)
        self._card_countdown.setStyleSheet(
            "QFrame { background-color: #1E1E2E; border: 1px solid #FAB387; "
            "border-radius: 8px; padding: 12px; }"
        )
        self._card_countdown.setVisible(False)
        countdown_layout = QVBoxLayout(self._card_countdown)
        countdown_layout.setSpacing(8)

        self._lbl_countdown_title = QLabel(
            "<b>Countdown Active — Switch to target app and place cursor!</b>",
            self._card_countdown,
        )
        countdown_layout.addWidget(self._lbl_countdown_title)

        countdown_row = QHBoxLayout()
        self._lbl_countdown_timer = QLabel(
            "<font size='+3' color='#FAB387'><b>10s</b></font>", self._card_countdown
        )
        countdown_row.addWidget(self._lbl_countdown_timer)

        self._bar_countdown = QProgressBar(self._card_countdown)
        self._bar_countdown.setRange(0, 10)
        self._bar_countdown.setValue(10)
        self._bar_countdown.setTextVisible(False)
        countdown_row.addWidget(self._bar_countdown, stretch=1)

        btn_cancel_cd = QPushButton("Cancel Countdown", self._card_countdown)
        btn_cancel_cd.clicked.connect(self._on_stop_typing)
        countdown_row.addWidget(btn_cancel_cd)

        countdown_layout.addLayout(countdown_row)
        left_layout.addWidget(self._card_countdown)

        # Live Typing Progress Card (Hidden when inactive)
        self._card_progress = QFrame(left_widget)
        self._card_progress.setFrameShape(QFrame.Shape.StyledPanel)
        self._card_progress.setStyleSheet(
            "QFrame { background-color: #1E1E2E; border: 1px solid #89B4FA; "
            "border-radius: 8px; padding: 12px; }"
        )
        self._card_progress.setVisible(False)
        progress_layout = QVBoxLayout(self._card_progress)
        progress_layout.setSpacing(8)

        self._lbl_progress_title = QLabel(
            "<b>Typing Execution in Progress...</b>", self._card_progress
        )
        progress_layout.addWidget(self._lbl_progress_title)

        self._bar_typing = QProgressBar(self._card_progress)
        self._bar_typing.setRange(0, 100)
        self._bar_typing.setValue(0)
        progress_layout.addWidget(self._bar_typing)

        self._lbl_progress_stats = QLabel("Step 0 / 0 (0.0%)", self._card_progress)
        progress_layout.addWidget(self._lbl_progress_stats)

        left_layout.addWidget(self._card_progress)

        split_layout.addWidget(left_widget, stretch=3)

        # ── RIGHT COLUMN ──
        right_scroll = QScrollArea(self)
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        right_scroll.setFixedWidth(340)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        # Dynamic Target Acquisition Information Card
        grp_target = QGroupBox("Active Target Window & Control", right_container)
        form_target = QFormLayout(grp_target)
        form_target.setContentsMargins(12, 12, 12, 12)
        form_target.setSpacing(8)

        self._lbl_target_win = QLabel("<i>Acquired at T=0s</i>", grp_target)
        self._lbl_target_win.setWordWrap(True)
        form_target.addRow("Window:", self._lbl_target_win)

        self._lbl_target_proc = QLabel("-", grp_target)
        form_target.addRow("Process:", self._lbl_target_proc)

        self._lbl_target_ctrl = QLabel("-", grp_target)
        form_target.addRow("Control Class:", self._lbl_target_ctrl)

        self._lbl_target_hwnd = QLabel("-", grp_target)
        form_target.addRow("HWND:", self._lbl_target_hwnd)

        btn_test_target = QPushButton("Acquire Current Active Target", grp_target)
        btn_test_target.clicked.connect(self._on_test_target_acquirer)
        form_target.addRow(btn_test_target)

        right_layout.addWidget(grp_target)

        # Typing Configuration Options Group
        grp_config = QGroupBox("Engine Parameters", right_container)
        form_config = QFormLayout(grp_config)
        form_config.setContentsMargins(12, 12, 12, 12)
        form_config.setSpacing(10)

        # Speed WPM
        wpm_layout = QHBoxLayout()
        self._spin_wpm = QSpinBox(grp_config)
        self._spin_wpm.setRange(20, 2000)
        self._spin_wpm.setValue(60)

        self._slider_wpm = QSlider(Qt.Orientation.Horizontal, grp_config)
        self._slider_wpm.setRange(20, 2000)
        self._slider_wpm.setValue(60)

        self._spin_wpm.valueChanged.connect(self._on_spin_wpm_changed)
        self._slider_wpm.valueChanged.connect(self._on_slider_wpm_changed)

        wpm_layout.addWidget(self._slider_wpm)
        wpm_layout.addWidget(self._spin_wpm)
        form_config.addRow("Speed (WPM):", wpm_layout)

        # Countdown Start Delay
        self._combo_delay = QComboBox(grp_config)
        self._combo_delay.addItem("0 seconds (Immediate)", 0.0)
        self._combo_delay.addItem("3 seconds", 3.0)
        self._combo_delay.addItem("5 seconds", 5.0)
        self._combo_delay.addItem("10 seconds (Default)", 10.0)
        self._combo_delay.addItem("15 seconds", 15.0)
        self._combo_delay.addItem("30 seconds", 30.0)
        self._combo_delay.setCurrentIndex(3)  # 10s default
        form_config.addRow("Start Delay:", self._combo_delay)

        # Typo Mistake Rate (% range 0% - 20%) with paired Slider + SpinBox
        mistake_layout = QHBoxLayout()
        self._spin_mistake = QSpinBox(grp_config)
        self._spin_mistake.setRange(0, 20)
        self._spin_mistake.setValue(2)
        self._spin_mistake.setSuffix("%")

        self._slider_mistake = QSlider(Qt.Orientation.Horizontal, grp_config)
        self._slider_mistake.setRange(0, 20)
        self._slider_mistake.setValue(2)

        self._spin_mistake.valueChanged.connect(self._on_spin_mistake_changed)
        self._slider_mistake.valueChanged.connect(self._on_slider_mistake_changed)

        mistake_layout.addWidget(self._slider_mistake)
        mistake_layout.addWidget(self._spin_mistake)
        form_config.addRow("Typo Rate:", mistake_layout)

        # Preview Confirmation Mode (Optional — OFF by default)
        self._chk_preview = QCheckBox("Show preview before typing", grp_config)
        self._chk_preview.setChecked(False)
        form_config.addRow(self._chk_preview)

        # Auto-Paste Threshold Toggle & Limit
        self._chk_enable_paste = QCheckBox("Enable Auto-Paste Threshold", grp_config)
        self._chk_enable_paste.setChecked(True)
        form_config.addRow(self._chk_enable_paste)

        self._spin_paste = QSpinBox(grp_config)
        self._spin_paste.setRange(100, 50000)
        self._spin_paste.setValue(5000)
        self._spin_paste.setSingleStep(500)
        form_config.addRow("Paste Limit (chars):", self._spin_paste)

        right_layout.addWidget(grp_config)
        right_layout.addStretch()

        right_scroll.setWidget(right_container)
        split_layout.addWidget(right_scroll, stretch=1)

        main_layout.addLayout(split_layout, stretch=1)

    def _connect_signals(self) -> None:
        """Connect Qt signals from controls and HumanTypingEngine backend."""
        # Control signals
        self._combo_delay.currentIndexChanged.connect(self._on_config_changed)
        self._chk_preview.toggled.connect(self._on_config_changed)
        self._chk_enable_paste.toggled.connect(self._spin_paste.setEnabled)
        self._chk_enable_paste.toggled.connect(self._on_config_changed)
        self._spin_paste.valueChanged.connect(self._on_config_changed)

        # Engine signals
        s = self._engine.signals
        s.countdown_started.connect(self._on_countdown_started)
        s.countdown_tick.connect(self._on_countdown_tick)
        s.target_acquired.connect(self._on_target_acquired)
        s.target_validation_failed.connect(self._on_target_validation_failed)
        s.preview_requested.connect(self._on_preview_requested)
        s.typing_started.connect(self._on_typing_started)
        s.typing_progress.connect(self._on_typing_progress)
        s.paused.connect(self._on_engine_paused)
        s.resumed.connect(self._on_engine_resumed)
        s.completed.connect(self._on_engine_completed)
        s.cancelled.connect(self._on_engine_cancelled)
        s.error_occurred.connect(self._on_engine_error)

    def _on_spin_wpm_changed(self, val: int) -> None:
        self._slider_wpm.blockSignals(True)
        self._slider_wpm.setValue(val)
        self._slider_wpm.blockSignals(False)
        self._on_config_changed()

    def _on_slider_wpm_changed(self, val: int) -> None:
        self._spin_wpm.blockSignals(True)
        self._spin_wpm.setValue(val)
        self._spin_wpm.blockSignals(False)
        self._on_config_changed()

    def _on_spin_mistake_changed(self, val: int) -> None:
        self._slider_mistake.blockSignals(True)
        self._slider_mistake.setValue(val)
        self._slider_mistake.blockSignals(False)
        self._on_config_changed()

    def _on_slider_mistake_changed(self, val: int) -> None:
        self._spin_mistake.blockSignals(True)
        self._spin_mistake.setValue(val)
        self._spin_mistake.blockSignals(False)
        self._on_config_changed()

    def _apply_initial_config(self) -> None:
        cfg = self._engine.default_config
        self._spin_wpm.setValue(int(cfg.speed_wpm))
        self._chk_preview.setChecked(cfg.show_preview_dialog)
        self._spin_mistake.setValue(round(cfg.mistake_probability * 100))
        self._chk_enable_paste.setChecked(cfg.enable_paste_threshold)
        self._spin_paste.setEnabled(cfg.enable_paste_threshold)
        self._spin_paste.setValue(cfg.paste_threshold_chars)

    def _get_current_config(self) -> TypingConfig:
        val = self._combo_delay.currentData()
        delay_seconds = float(val) if val is not None else 10.0
        return TypingConfig(
            speed_wpm=float(self._spin_wpm.value()),
            start_delay_seconds=delay_seconds,
            show_preview_dialog=self._chk_preview.isChecked(),
            mistake_probability=float(self._spin_mistake.value()) / 100.0,
            enable_paste_threshold=self._chk_enable_paste.isChecked(),
            paste_threshold_chars=self._spin_paste.value(),
        )

    def _on_config_changed(self) -> None:
        cfg = self._get_current_config()
        self._engine.set_default_config(cfg)
        self._update_text_stats()

    def _on_text_changed(self) -> None:
        self._update_text_stats()

    def _update_text_stats(self) -> None:
        text = self._txt_input.toPlainText()
        char_count = len(text)
        word_count = len(text.split())
        line_count = text.count("\n") + (1 if text else 0)

        cfg = self._get_current_config()
        est_seconds = cfg.calculate_estimated_duration_seconds(char_count)
        mins = int(est_seconds // 60)
        secs = int(est_seconds % 60)
        est_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

        self._lbl_text_stats.setText(
            f"{char_count:,} characters | {word_count:,} words | "
            f"{line_count:,} lines | Est: {est_str}"
        )

    def _update_status_badge(self, text: str, bg_hex: str, fg_hex: str = "#11111B") -> None:
        self._lbl_status.setText(text)
        self._lbl_status.setStyleSheet(
            f"background-color: {bg_hex}; color: {fg_hex}; font-weight: bold; "
            f"border-radius: 4px; padding: 4px 10px; font-size: 11px;"
        )

    # -------------------------------------------------------------
    # UI Control Handlers
    # -------------------------------------------------------------
    def _on_start_typing(self) -> None:
        text = self._txt_input.toPlainText().strip()
        if not text:
            self._signals.toast_requested.emit(
                "warning", "Please enter or paste text to type before starting."
            )
            return

        cfg = self._get_current_config()
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_pause.setEnabled(False)

        self._active_job_id = self._engine.type_text(text, cfg)
        logger.info(f"User launched typing job '{self._active_job_id}' from UI.")

    def _on_pause_resume(self) -> None:
        if self._btn_pause.text() == "Pause":
            self._engine.pause()
        else:
            self._engine.resume()

    def _on_stop_typing(self) -> None:
        self._engine.emergency_abort()
        self._reset_ui_state()

    def _on_test_target_acquirer(self) -> None:
        from src.platform import get_platform_target_acquirer

        acquirer = get_platform_target_acquirer()
        target = acquirer.get_foreground_target()
        val = acquirer.validate_target(target)

        if target and val.is_valid:
            self._update_target_display(target)
            self._signals.toast_requested.emit(
                "info", f"Target Acquired: '{target.window_title}' ({target.process_name})"
            )
        else:
            reason = val.reason if val else "No window acquired"
            self._signals.toast_requested.emit("warning", f"Target Validation Failed: {reason}")

    def _update_target_display(self, target: TargetInfo) -> None:
        self._current_target = target
        self._lbl_target_win.setText(f"<b>{target.window_title}</b>")
        self._lbl_target_proc.setText(f"<code>{target.process_name}</code>")
        self._lbl_target_ctrl.setText(f"<code>{target.control_type}</code>")
        self._lbl_target_hwnd.setText(f"<code>0x{target.hwnd_window:08X}</code>")

    def _reset_ui_state(self) -> None:
        self._btn_start.setEnabled(True)
        self._btn_pause.setEnabled(False)
        self._btn_pause.setText("Pause")
        self._btn_stop.setEnabled(False)
        self._card_countdown.setVisible(False)
        self._card_progress.setVisible(False)
        self._update_status_badge("READY", "#94E2D5", "#181825")

    # -------------------------------------------------------------
    # Engine Signal Handlers
    # -------------------------------------------------------------
    def _on_countdown_started(self, _job_id: str, duration: float) -> None:
        self._update_status_badge("COUNTDOWN", "#FAB387", "#11111B")
        self._card_countdown.setVisible(True)
        self._bar_countdown.setRange(0, int(duration))
        self._bar_countdown.setValue(int(duration))
        self._lbl_countdown_timer.setText(
            f"<font size='+3' color='#FAB387'><b>{int(duration)}s</b></font>"
        )

    def _on_countdown_tick(self, _job_id: str, remaining: int) -> None:
        self._bar_countdown.setValue(remaining)
        self._lbl_countdown_timer.setText(
            f"<font size='+3' color='#FAB387'><b>{remaining}s</b></font>"
        )

    def _on_target_acquired(
        self, _job_id: str, target: Any, _char_count: int, _est_seconds: float
    ) -> None:
        if isinstance(target, TargetInfo):
            self._update_target_display(target)

    def _on_target_validation_failed(self, _job_id: str, reason: str) -> None:
        self._update_status_badge("TARGET VALIDATION FAILED", "#F38BA8", "#11111B")
        self._signals.toast_requested.emit("error", f"Target Validation Failed: {reason}")
        self._reset_ui_state()

    def _on_preview_requested(
        self, _job_id: str, target: Any, char_count: int, est_seconds: float
    ) -> None:
        self._update_status_badge("PREVIEW WAIT", "#CBA6F7", "#11111B")
        if isinstance(target, TargetInfo):
            if not self.isVisible():
                self._engine.confirm_preview()
                return

            dlg = TargetPreviewDialog(target, char_count, est_seconds, parent=self)
            if dlg.exec() == TargetPreviewDialog.DialogCode.Accepted:
                if dlg.dont_show_again():
                    self._chk_preview.setChecked(False)
                    self._on_config_changed()
                self._engine.confirm_preview()
            else:
                self._engine.cancel_preview()

    def _on_typing_started(self, _job_id: str, _text: str) -> None:
        self._update_status_badge("TYPING", "#89B4FA", "#11111B")
        self._card_countdown.setVisible(False)
        self._card_progress.setVisible(True)
        self._btn_pause.setEnabled(True)

    def _on_typing_progress(self, _job_id: str, current: int, total: int, percent: float) -> None:
        self._bar_typing.setValue(int(percent))
        self._lbl_progress_stats.setText(f"Step {current:,} / {total:,} ({percent:.1f}%)")

    def _on_engine_paused(self, _job_id: str) -> None:
        self._update_status_badge("PAUSED", "#F9E2AF", "#11111B")
        self._btn_pause.setText("Resume")

    def _on_engine_resumed(self, _job_id: str) -> None:
        self._update_status_badge("TYPING", "#89B4FA", "#11111B")
        self._btn_pause.setText("Pause")

    def _on_engine_completed(self, _job_id: str, duration: float) -> None:
        self._update_status_badge("COMPLETED", "#A6E3A1", "#11111B")
        self._signals.toast_requested.emit(
            "success", f"Typing completed successfully in {duration}s."
        )
        self._reset_ui_state()

    def _on_engine_cancelled(self, _job_id: str, reason: str) -> None:
        self._update_status_badge("CANCELLED", "#9399B2", "#11111B")
        self._signals.toast_requested.emit("info", f"Typing Cancelled: {reason}")
        self._reset_ui_state()

    def _on_engine_error(self, _job_id: str, error_message: str) -> None:
        self._update_status_badge("ERROR", "#F38BA8", "#11111B")
        self._signals.toast_requested.emit("error", f"Typing Error: {error_message}")
        self._reset_ui_state()
