"""
Pestaña de Comparación con el Estándar de Excel.
Muestra tablas por bloque comparando las señales del XRIO con el estándar.
"""
import os
from collections import OrderedDict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
    QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QBrush

from core.excel_standard_parser import ExcelStandardParser
from models.signal_models import XRIOData

# Colores similares a los de la pestaña XRIO
_BLOCK_COLORS = [
    ("#0d6efd", "#ffffff"),
    ("#198754", "#ffffff"),
    ("#6f42c1", "#ffffff"),
    ("#fd7e14", "#ffffff"),
    ("#dc3545", "#ffffff"),
    ("#0dcaf0", "#212529"),
    ("#20c997", "#ffffff"),
    ("#6610f2", "#ffffff"),
]

class ComparisonBlockTable(QFrame):
    """Tabla que representa un bloque del estándar con estado de validación."""
    def __init__(self, block_name: str, standard_signals: list, xrio_signals: list,
                 color_bg: str, color_fg: str, parent=None):
        super().__init__(parent)
        self._block_name = block_name
        self._standard_signals = standard_signals
        self._xrio_signals = xrio_signals # Nombres de señales presentes en el XRIO
        self._setup_ui(color_bg, color_fg)

    def _setup_ui(self, color_bg: str, color_fg: str):
        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet(
            "ComparisonBlockTable { border: 1px solid #dee2e6; border-radius: 4px; "
            "background-color: #ffffff; }")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header del bloque
        header = QLabel(f"  {self._block_name}  ")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFixedHeight(24)
        header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header.setStyleSheet(
            f"background-color: {color_bg}; color: {color_fg}; "
            f"border-top-left-radius: 3px; border-top-right-radius: 3px; "
            f"padding: 2px 6px;")
        layout.addWidget(header)

        # Tabla
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(20)
        table.setShowGrid(True)
        table.setStyleSheet(
            "QTableWidget { border: none; font-size: 11px; }"
            "QHeaderView::section { font-size: 10px; padding: 2px 4px; }")

        cols = ["V", "SEÑAL", "G"]
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setRowCount(len(self._standard_signals))

        table.setColumnWidth(0, 28)
        table.setColumnWidth(1, 180)
        table.setColumnWidth(2, 28)

        green = QColor("#198754")
        
        # Normalizar nombres de señales XRIO para comparación (mayúsculas y quitar espacios)
        xrio_names_norm = [s.strip().upper() for s in self._xrio_signals]

        for r, sig in enumerate(self._standard_signals):
            std_name = sig['name']
            std_group = sig['group']
            
            # Comparar (fuzzy o exacta)
            exists = std_name.strip().upper() in xrio_names_norm
            
            # Columna V (check mark si existe)
            v_text = "✔" if exists else ""
            chk = QTableWidgetItem(v_text)
            chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            chk.setForeground(QBrush(green))
            table.setItem(r, 0, chk)

            # Nombre de la señal (del estándar)
            name_it = QTableWidgetItem(std_name)
            name_it.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if not exists:
                name_it.setForeground(QBrush(QColor("#dc3545"))) # Rojo si falta
            table.setItem(r, 1, name_it)

            # Columna G (Grupo del estándar)
            g_it = QTableWidgetItem(std_group)
            g_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(r, 2, g_it)

        table.horizontalHeader().setStretchLastSection(False)
        layout.addWidget(table)
        
        # Ajustar altura de la tabla basado en filas (máximo ajustable)
        row_height = 20
        header_height = 25
        total_height = (len(self._standard_signals) * row_height) + header_height + 30
        self.setMinimumHeight(min(total_height, 400))

class ComparisonTab(QWidget):
    def __init__(self, excel_path: str, parent=None):
        super().__init__(parent)
        self._excel_parser = ExcelStandardParser(excel_path)
        self._xrio_data: XRIOData | None = None
        self._block_widgets: list[ComparisonBlockTable] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        
        # Header orientativo
        self._lbl_info = QLabel("Cargue un archivo XRIO para comparar con el estándar de Excel")
        self._lbl_info.setStyleSheet("font-weight: bold; color: #555; padding: 5px;")
        layout.addWidget(self._lbl_info)

        # Area scroll
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background-color: #f4f5f7; }")

        self._grid_container = QWidget()
        self._grid_container.setStyleSheet("background-color: #f4f5f7;")
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(10)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._scroll.setWidget(self._grid_container)
        layout.addWidget(self._scroll)

    def set_xrio_data(self, data: XRIOData):
        self._xrio_data = data
        model = data.relay.model
        
        # Intentar encontrar el modelo en el excel
        models = self._excel_parser.get_available_models()
        best_match = None
        for m in models:
            if m.upper() in model.upper() or model.upper() in m.upper():
                best_match = m
                break
        
        if not best_match:
            # Fallback a REC670 si no hay match claro, o pedir al usuario
            best_match = "REC670" if "REC670" in models else models[0]
            self._lbl_info.setText(f"Mostrando estándar para: {best_match} (No se encontró match exacto para {model})")
        else:
            self._lbl_info.setText(f"Comparando {model} con estándar {best_match}")

        standard_data = self._excel_parser.parse_sheet(best_match)
        self._build_comparison_grid(standard_data)

    def _build_comparison_grid(self, standard_data: dict):
        # Limpiar
        for w in self._block_widgets:
            self._grid_layout.removeWidget(w)
            w.deleteLater()
        self._block_widgets.clear()

        if not self._xrio_data:
            return

        # Lista de todos los nombres de señales binarias y analógicas del XRIO
        xrio_all_names = [s.name for s in self._xrio_data.analog_signals] + \
                         [s.name for s in self._xrio_data.binary_signals]

        row, col = 0, 0
        max_cols = 3
        color_idx = 0

        for block_name, std_sigs in standard_data.items():
            bg, fg = _BLOCK_COLORS[color_idx % len(_BLOCK_COLORS)]
            
            widget = ComparisonBlockTable(block_name, std_sigs, xrio_all_names, bg, fg)
            self._block_widgets.append(widget)
            self._grid_layout.addWidget(widget, row, col)
            
            col += 1
            color_idx += 1
            if col >= max_cols:
                col = 0
                row += 1
