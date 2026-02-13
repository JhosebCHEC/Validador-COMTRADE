"""
Ventana principal — diseño compacto con tema claro.
"""
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap

from ui.styles import APP_THEME
from ui.xrio_tab import XRIOTab
from ui.comtrade_tab import ComtradeTab
from ui.dictionary_tab import DictionaryTab
from core.validator import SignalValidator
from core.alias_database import AliasDatabase


class MainWindow(QMainWindow):
    """Ventana principal compacta y profesional."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Validador de Estándar — Relés de Protección")
        self.setMinimumSize(1100, 680)
        self.resize(1280, 780)
        self.setStyleSheet(APP_THEME)

        logo_path = "LOGO.png"
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self._alias_db = AliasDatabase()
        self._validator = SignalValidator(self._alias_db)
        self._setup_ui()
        self._connect_signals()

    # ─── UI ───────────────────────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 6, 8, 2)
        root.setSpacing(6)

        # ── Header bar (compacto, una sola línea) ──
        header = QHBoxLayout()
        header.setSpacing(8)

        lbl_logo = QLabel()
        logo_path = "LOGO.png"
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            if not pix.isNull():
                lbl_logo.setPixmap(pix.scaled(110, 34,
                                              Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation))

        lbl_title = QLabel("Validador de Estándar")
        fnt = QFont("Segoe UI", 12, QFont.Weight.Bold)
        lbl_title.setFont(fnt)
        lbl_title.setStyleSheet("color: #00883A;")

        lbl_sep = QLabel("—")
        lbl_sep.setStyleSheet("color: #9fb1a6; font-size: 12px;")

        self._lbl_relay = QLabel("Sin relé cargado")
        self._lbl_relay.setStyleSheet("color: #5b6b62; font-size: 11px;")

        header.addWidget(lbl_logo)
        header.addWidget(lbl_title)
        header.addWidget(lbl_sep)
        header.addWidget(self._lbl_relay)
        header.addStretch()

        self._btn_validate = QPushButton("  Validar Señales")
        self._btn_validate.setProperty("cssClass", "primary")
        self._btn_validate.setEnabled(False)
        self._btn_validate.setFixedHeight(26)
        self._btn_validate.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_validate.clicked.connect(self._run_validation)

        header.addWidget(self._btn_validate)
        root.addLayout(header)

        # ── Tabs ──
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(False)
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        self._tabs.setUsesScrollButtons(True)
        self._tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self._tabs.tabBar().setExpanding(False)
        self._tabs.tabBar().setDrawBase(False)

        self._xrio_tab = XRIOTab()
        self._comtrade_tab = ComtradeTab()
        self._dictionary_tab = DictionaryTab(self._alias_db)

        self._tabs.addTab(self._xrio_tab, "XRIO / Disturbance Report")
        self._tabs.addTab(self._comtrade_tab, "Estándar COMTRADE (XLSX)")
        self._tabs.addTab(self._dictionary_tab, "Diccionario de Alias")

        root.addWidget(self._tabs, 1)

        # ── Status Bar ──
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_label = QLabel("Listo")
        sb.addWidget(self._status_label, 1)

    # ─── Signals ──────────────────────────────────────────────────────
    def _connect_signals(self):
        self._xrio_tab.xrio_loaded.connect(self._on_xrio_loaded)
        self._xrio_tab.relay_detected.connect(self._on_relay_detected)
        self._comtrade_tab.comtrade_loaded.connect(self._on_comtrade_loaded)
        self._comtrade_tab.standard_changed.connect(self._on_standard_changed)
        self._dictionary_tab.alias_changed.connect(self._on_alias_changed)

    # ─── Slots ────────────────────────────────────────────────────────
    def _on_xrio_loaded(self, data):
        n = data.total_signals if data else 0
        self._status_label.setText(f"XRIO cargado — {n} señales detectadas")
        self._check_validate_ready()

    def _on_relay_detected(self, relay_info: str):
        self._lbl_relay.setText(relay_info)
        self._lbl_relay.setStyleSheet("color: #00883A; font-weight:600; font-size:11px;")

    def _on_comtrade_loaded(self, config):
        n = config.total_channels if config else 0
        self._status_label.setText(f"COMTRADE cargado — {n} canales")
        self._check_validate_ready()

    def _on_standard_changed(self):
        self._status_label.setText("Estándar COMTRADE modificado")

    def _on_alias_changed(self):
        self._status_label.setText("Diccionario de alias actualizado")

    def _check_validate_ready(self):
        xrio_ok = self._xrio_tab.get_signal_count() > 0

        # Compatibilidad con dos modos de la pestaña COMTRADE:
        # 1) modo clásico (ComtradeConfig)
        # 2) modo XLSX (sin ComtradeConfig, usa nombres de tablas)
        comtrade_ok = False
        cfg = self._comtrade_tab.get_config()
        if cfg is not None:
            comtrade_ok = cfg.total_channels > 0
        else:
            try:
                comtrade_ok = len(self._comtrade_tab.get_all_channel_names()) > 0
            except Exception:
                comtrade_ok = False

        self._btn_validate.setEnabled(bool(xrio_ok and comtrade_ok))

    # ─── Validación ──────────────────────────────────────────────────
    def _run_validation(self):
        xrio = self._xrio_tab.get_xrio_data()
        comtrade = self._comtrade_tab.get_config()

        if not xrio or not comtrade:
            QMessageBox.warning(self, "Faltan Datos",
                                "Cargue un archivo XRIO y un estándar COMTRADE primero.")
            return

        summary = self._validator.auto_validate_and_update(xrio, comtrade)
        total = summary.get("total", 0)
        matched = summary.get("exact", 0) + summary.get("alias", 0) + summary.get("fuzzy", 0)

        msg = (f"Validación completada\n\n"
               f"  • Total señales: {total}\n"
               f"  • Coincidencias exactas: {summary.get('exact', 0)}\n"
               f"  • Coincidencias por alias: {summary.get('alias', 0)}\n"
               f"  • Coincidencias difusas: {summary.get('fuzzy', 0)}\n"
               f"  • Sin coincidencia: {summary.get('new', 0)}\n\n"
               f"Tasa de coincidencia: {matched}/{total}")

        QMessageBox.information(self, "Resultado de Validación", msg)
        self._status_label.setText(
            f"Validación: {matched}/{total} señales coinciden")
