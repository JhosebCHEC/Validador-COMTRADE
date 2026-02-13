"""
Pestaña 1: XRIO / Disturbance Report
Muestra las señales del XRIO organizadas en tablas por bloque
(AxRADR = analog, BxRBDR = binary) con layout tipo grid.
"""
import os
from collections import OrderedDict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QPushButton, QLineEdit, QComboBox, QFileDialog, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
    QSizePolicy, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QBrush

from core.xrio_parser import XRIOParser
from core.excel_standard_parser import ExcelStandardParser
from models.signal_models import (
    XRIOData, AnalogSignal, BinarySignal, SignalType, ProtectionFunction,
    DisturbanceReportSignal
)


# ── Colores para cabeceras de bloques ──
_BLOCK_COLORS = [
    ("#00883A", "#ffffff"),
    ("#00883A", "#ffffff"),
    ("#00883A", "#ffffff"),
    ("#00883A", "#ffffff"),
    ("#00883A", "#ffffff"),
    ("#00883A", "#ffffff"),
    ("#00883A", "#ffffff"),
    ("#00883A", "#ffffff"),
]


class DisturbanceReportBlockTable(QFrame):
    """Widget para UN bloque BxRBDR específico."""

    def __init__(self, block_name: str, signals: list, std_start_map: dict | None = None, parent=None):
        super().__init__(parent)
        self._block_name = block_name
        self._signals = signals
        self._std_start_map = std_start_map or {}
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet(
            "DisturbanceReportBlockTable { border: 1px solid #dee2e6; border-radius: 4px; "
            "background-color: #ffffff; }")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Determinar color basado en el bloque (similar a la lógica anterior)
        # B1 = Azul, B2 = Verde, etc.
        color_idx = 7 # Default indigo
        match = "".join(filter(str.isdigit, self._block_name))
        if match:
             idx = int(match) - 1
             if 0 <= idx < len(_BLOCK_COLORS):
                 color_idx = idx
        
        bg_col, fg_col = _BLOCK_COLORS[color_idx]

        # ── Header ──
        header_text = f"  {self._block_name} ({len(self._signals)} Señales)"
        header = QLabel(header_text)
        header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setFixedHeight(24) # Reducido de 28
        header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header.setStyleSheet(
            f"background-color: {bg_col}; color: {fg_col}; " 
            "border-top-left-radius: 3px; border-top-right-radius: 3px; "
            "padding-left: 8px;")
        layout.addWidget(header)

        # ── Tabla ──
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(24)
        table.setShowGrid(True)
        
        # Estilo optimizado (más compacto)
        table.setStyleSheet(
            "QTableWidget { border: none; font-size: 11px; }" # Reducido de 12px
            "QHeaderView::section { font-size: 11px; font-weight: bold; padding: 2px 4px; background-color: #f8f9fa; border: 1px solid #dee2e6; }"
            "QTableWidget::item { padding-left: 4px; padding-right: 4px; }"
        )

        # Columnas solicitadas: V, Señal, Start XRIO, Start Std
        cols = ["V", "Señal", "Start XRIO", "Start Std"]
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setRowCount(len(self._signals))

        # Configurar anchos optimizados
        header_view = table.horizontalHeader()
        
        # V
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, 30)
        
        # Señal - Stretch para ocupar espacio
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # Start XRIO
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(2, 90)

        # Start Std
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(3, 90)

        for r, sig in enumerate(self._signals):
            sig_name = (sig.name or "").strip()
            std_start = self._std_start_map.get(sig_name.upper(), "")
            is_valid = bool(std_start)

            # V (Vacío hasta validar)
            item_v = QTableWidgetItem("✔" if is_valid else "")
            item_v.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_valid:
                item_v.setForeground(QBrush(QColor("#00883A")))
            table.setItem(r, 0, item_v)

            # Señal (Name)
            item_name = QTableWidgetItem(sig_name)
            item_name.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item_name.setToolTip(sig.description) # Descripción como tooltip
            if "On" in sig.trig_operation:
                 item_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            table.setItem(r, 1, item_name)

            # Start XRIO (Trig Oper)
            item_trig = QTableWidgetItem(sig.trig_operation)
            item_trig.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if "On" in sig.trig_operation:
                item_trig.setForeground(QBrush(QColor("#00883A")))
                item_trig.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            table.setItem(r, 2, item_trig)

            # Start Std desde XLSX si coincide
            item_std = QTableWidgetItem(std_start if std_start else "-")
            item_std.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(r, 3, item_std)

        # Ajuste de altura dinámica
        visible_rows = max(6, min(len(self._signals), 10))
        table_height = 34 + (visible_rows * 24)
        table.setMinimumHeight(table_height)
        self.setMinimumHeight(table_height + 28)

        layout.addWidget(table)


class DisturbanceReportContainer(QWidget):
    """Contenedor que agrupa tablas de reporte de disturbios por bloque."""
    
    def __init__(self, signals: list, std_start_map: dict | None = None, parent=None):
        super().__init__(parent)
        self._signals = signals
        self._std_start_map = std_start_map or {}
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        # Agrupar señales por bloque
        # Usamos OrderedDict para mantener orden de aparición (o orden alfabético)
        blocks_map = OrderedDict()
        
        # Primero ordenamos las señales por bloque para que aparezcan ordenados B1, B2...
        sorted_signals = sorted(self._signals, key=lambda s: (s.block, s.channel))

        for sig in sorted_signals:
            if sig.block not in blocks_map:
                blocks_map[sig.block] = []
            blocks_map[sig.block].append(sig)
        
        if not blocks_map:
             lbl = QLabel("No Disturbance Report Configuration found.")
             layout.addWidget(lbl, 0, 0, 1, 2)
             return

        row = 0
        col = 0
        max_cols = 2
        for block_name, block_signals in blocks_map.items():
            table_widget = DisturbanceReportBlockTable(block_name, block_signals, self._std_start_map)
            layout.addWidget(table_widget, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1


class DisturbanceReportTable(DisturbanceReportContainer):
    """Wrapper para mantener compatibilidad con codigo existente si es necesario,
       o reemplazamos la clase original."""
    pass


class BlockTable(QFrame):
    """Widget que representa un solo bloque (AxRADR / BxRBDR) como tabla compacta."""

    def __init__(self, block_name: str, signals: list, signal_type: str,
                 color_bg: str, color_fg: str, std_start_map: dict | None = None,
                 parent=None):
        super().__init__(parent)
        self._block_name = block_name
        self._signals = signals
        self._signal_type = signal_type
        self._std_start_map = std_start_map or {}
        self._setup_ui(color_bg, color_fg)

    def _setup_ui(self, color_bg: str, color_fg: str):
        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet(
            "BlockTable { border: 1px solid #dee2e6; border-radius: 4px; "
            "background-color: #ffffff; }")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header del bloque ──
        header = QLabel(f"  {self._block_name}  ({len(self._signals)})")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFixedHeight(24)
        header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header.setStyleSheet(
            f"background-color: {color_bg}; color: {color_fg}; "
            f"border-top-left-radius: 3px; border-top-right-radius: 3px; "
            f"padding: 2px 6px;")
        layout.addWidget(header)

        # ── Tabla ──
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(24)
        table.setShowGrid(True)
        table.setStyleSheet(
            "QTableWidget { border: none; font-size: 11px; }"
            "QHeaderView::section { font-size: 10px; padding: 4px 6px; }")

        if self._signal_type == "analog":
            self._build_analog_table(table)
        else:
            self._build_binary_table(table)

        visible_rows = max(6, min(len(self._signals), 12))
        table_height = 34 + (visible_rows * 24)
        table.setMinimumHeight(table_height)
        self.setMinimumHeight(table_height + 28)

        # table.horizontalHeader().setStretchLastSection(True) # Reemplazado por modos específicos
        layout.addWidget(table)
        self._table = table

    def _build_analog_table(self, table: QTableWidget):
        # Columnas analógicas validadas contra estándar XLSX
        cols = ["V", "Señal", "Start XRIO", "Start Std", "Fase", "Unidad", "Prim"]
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setRowCount(len(self._signals))
        table.verticalHeader().setDefaultSectionSize(24)

        # Modos de redimensionamiento
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)            # V
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Señal
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)            # Start XRIO
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)            # Start Std
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)            # Fase
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)            # Unidad
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)            # Prim
        
        # Anchos iniciales
        table.setColumnWidth(0, 32)
        table.setColumnWidth(2, 95)
        table.setColumnWidth(3, 90)
        table.setColumnWidth(4, 60)
        table.setColumnWidth(5, 80)
        table.setColumnWidth(6, 95)

        for r, sig in enumerate(self._signals):
            sig_name = (sig.name or "").strip()
            std_start = self._std_start_map.get(sig_name.upper(), "")
            is_valid = bool(std_start)

            # V validación por coincidencia contra XLSX
            item_v = QTableWidgetItem("✔" if is_valid else "")
            item_v.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_valid:
                item_v.setForeground(QBrush(QColor("#00883A")))
            table.setItem(r, 0, item_v)

            status = sig.status if hasattr(sig, 'status') else "On"

            items = [
                # Column 1: Señal
                sig_name,
                # Column 2: Start XRIO
                status,
                # Column 3: Start Std (desde XLSX)
                std_start if std_start else "-",
                # Column 4: Fase
                sig.phase,
                # Column 5: Unidad
                sig.unit,
                # Column 6: Prim
                f"{sig.primary:g}",
            ]
            
            for i, txt in enumerate(items):
                col_idx = i + 1
                it = QTableWidgetItem(txt)
                # Alinear izquierda solo Nombre (1)
                align = (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter 
                         if col_idx == 1 else Qt.AlignmentFlag.AlignCenter)
                it.setTextAlignment(align)
                if col_idx == 1:
                    it.setToolTip(txt)
                table.setItem(r, col_idx, it)

    def _build_binary_table(self, table: QTableWidget):
        cols = ["V", "Señal", "Start XRIO", "Start Std"]
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setRowCount(len(self._signals))
        
        # Modos de redimensionamiento
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)            # V
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Señal
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)            # Start XRIO
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)            # Start Std

        table.setColumnWidth(0, 28)
        table.setColumnWidth(2, 95)
        table.setColumnWidth(3, 95)

        for r, sig in enumerate(self._signals):
            sig_name = (sig.name or "").strip()
            std_start = self._std_start_map.get(sig_name.upper(), "")
            is_valid = bool(std_start)

            # V validación por coincidencia contra XLSX
            chk = QTableWidgetItem("✔" if is_valid else "")
            chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_valid:
                chk.setForeground(QBrush(QColor("#00883A")))
            table.setItem(r, 0, chk)

            # Nombre
            name_it = QTableWidgetItem(sig_name)
            name_it.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(r, 1, name_it)

            # Start XRIO desde estado binario
            start_xrio = "On" if getattr(sig, 'state', 0) == 1 else "Off"
            xrio_it = QTableWidgetItem(start_xrio)
            xrio_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if start_xrio == "On":
                xrio_it.setForeground(QBrush(QColor("#00883A")))
                xrio_it.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            table.setItem(r, 2, xrio_it)

            # Start Std
            std_it = QTableWidgetItem(std_start if std_start else "-")
            std_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(r, 3, std_it)

    @property
    def block_name(self) -> str:
        return self._block_name

    @property
    def signal_count(self) -> int:
        return len(self._signals)


class ComparisonBlockTable(QFrame):
    """Tabla que representa un bloque del estándar con estado de validación."""
    def __init__(self, block_name: str, standard_signals: list, xrio_signals_map: dict,
                 color_bg: str, color_fg: str, parent=None):
        super().__init__(parent)
        self._block_name = block_name
        self._standard_signals = standard_signals
        self._xrio_signals_map = xrio_signals_map
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

        # Columnas solicitadas: V, Señal, Arranca XRIO, Arranca Estándar
        cols = ["V", "Señal", "Start XRIO", "Start Std"]
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setRowCount(len(self._standard_signals))
        
        # Modos de redimensionamiento
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)            # V
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Señal
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)            # Start XRIO
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)            # Start Std

        table.setColumnWidth(0, 28)
        table.setColumnWidth(2, 90)
        table.setColumnWidth(3, 90)

        green = QColor("#198754")
        red = QColor("#dc3545")
        
        for r, sig in enumerate(self._standard_signals):
            std_name = sig['name']
            std_start = sig['group']
            
            # Buscar en mapa XRIO
            xrio_sig = self._xrio_signals_map.get(std_name.strip().upper())
            exists = xrio_sig is not None

            # Obtener Trigger XRIO
            xrio_start_val = ""
            if exists and hasattr(xrio_sig, 'trig_operation'):
                xrio_start_val = xrio_sig.trig_operation
            
            # 1. Columna V
            v_text = "✔" if exists else ""
            chk = QTableWidgetItem(v_text)
            chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if exists:
                chk.setForeground(QBrush(green))
            table.setItem(r, 0, chk)

            # 2. Señal
            name_it = QTableWidgetItem(std_name)
            name_it.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if not exists:
                name_it.setForeground(QBrush(red))
            table.setItem(r, 1, name_it)

            # 3. Start XRIO
            xrio_it = QTableWidgetItem(xrio_start_val if xrio_start_val else "-")
            xrio_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if "On" in xrio_start_val:
                xrio_it.setForeground(QBrush(green))
                xrio_it.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            table.setItem(r, 2, xrio_it)

            # 4. Start Std
            std_it = QTableWidgetItem(std_start)
            std_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(r, 3, std_it)

        table.horizontalHeader().setStretchLastSection(False)
        layout.addWidget(table)

    @property
    def block_name(self) -> str:
        return self._block_name

class XRIOTab(QWidget):
    """Pestaña de XRIO con tablas organizadas por bloque."""

    xrio_loaded = pyqtSignal(object)     # XRIOData
    relay_detected = pyqtSignal(str)     # relay full_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parser = XRIOParser()
        root_excel = "Estándar COMTRADE.xlsx"
        data_excel = os.path.join("data", "Estándar COMTRADE.xlsx")
        excel_path = root_excel if os.path.exists(root_excel) else data_excel
        self._excel_parser = ExcelStandardParser(excel_path)
        self._std_start_map: dict[str, str] = {}
        self._xrio_data: XRIOData | None = None
        self._block_widgets: list[BlockTable] = []
        self._comparison_widgets: list[ComparisonBlockTable] = []
        self._setup_ui()

    # ─── UI ───────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 4, 6, 4)
        root.setSpacing(4)

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self._btn_load = QPushButton("Abrir XRIO")
        self._btn_load.setProperty("cssClass", "primary")
        self._btn_load.setFixedHeight(26)
        self._btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_load.clicked.connect(self._load_file)

        self._lbl_file = QLabel("Ningún archivo cargado")
        self._lbl_file.setObjectName("subtitle")

        toolbar.addWidget(self._btn_load)
        toolbar.addWidget(self._lbl_file, 1)

        # ── Filtros ──
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Buscar señal...")
        self._search.setFixedWidth(200)
        self._search.textChanged.connect(self._apply_filter)

        self._filter_type = QComboBox()
        self._filter_type.addItems(["Todos", "Analógicos (AxRADR)", "Binarios (BxRBDR)"])
        self._filter_type.setFixedWidth(160)
        self._filter_type.currentIndexChanged.connect(self._apply_filter)

        toolbar.addWidget(self._search)
        toolbar.addWidget(self._filter_type)

        root.addLayout(toolbar)

        # ── Info del relé (compacta, una línea) ──
        self._relay_bar = QFrame()
        self._relay_bar.setFixedHeight(24)
        self._relay_bar.setStyleSheet(
            "background-color: #eaf4ec; border: 1px solid #c8ddcd; "
            "border-radius: 3px; padding: 0 8px;")
        relay_lay = QHBoxLayout(self._relay_bar)
        relay_lay.setContentsMargins(8, 0, 8, 0)

        self._lbl_relay_info = QLabel("Cargue un archivo .xrio para ver la información del relé")
        self._lbl_relay_info.setStyleSheet("color: #1E7A3E; font-size: 11px;")
        relay_lay.addWidget(self._lbl_relay_info)

        self._lbl_count = QLabel("")
        self._lbl_count.setStyleSheet("color: #1E7A3E; font-size: 11px; font-weight:600;")
        self._lbl_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        relay_lay.addWidget(self._lbl_count)

        root.addWidget(self._relay_bar)

        # ── Area scroll con grid de bloques ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background-color: #f4f5f7; }")

        self._grid_container = QWidget()
        self._grid_container.setStyleSheet("background-color: #f4f5f7;")
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(6)
        self._grid_layout.setContentsMargins(2, 2, 2, 2)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Removed AlignLeft to allow stretching

        self._scroll.setWidget(self._grid_container)
        root.addWidget(self._scroll, 1)

        # ── Placeholder cuando no hay datos ──
        self._placeholder = QLabel(
            "📂  Abra un archivo .xrio para visualizar las señales organizadas por bloques")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            "color: #adb5bd; font-size: 13px; padding: 40px;")
        self._grid_layout.addWidget(self._placeholder, 0, 0, 1, 3)

    # ─── Cargar archivo ───────────────────────────────────────────────
    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir Archivo XRIO", "",
            "XRIO Files (*.xrio);;XML Files (*.xml);;Todos (*)")
        if not path:
            return

        # Paso 1: parseo del archivo
        try:
            self._xrio_data = self._parser.parse(path)
            self._lbl_file.setText(os.path.basename(path))
        except Exception as e:
            QMessageBox.critical(self, "Error al cargar XRIO", str(e))
            return

        # Paso 2: actualización de UI con protección de errores
        warnings = []

        try:
            self._std_start_map = self._build_std_start_map()
        except Exception as e:
            self._std_start_map = {}
            warnings.append(f"No se pudo cargar estándar XLSX para validación: {e}")

        try:
            self._update_relay_bar()
        except Exception as e:
            warnings.append(f"Error actualizando barra de relé: {e}")

        try:
            self._build_block_grid()
        except Exception as e:
            warnings.append(f"Error construyendo tablas XRIO: {e}")

        try:
            self.xrio_loaded.emit(self._xrio_data)
            if self._xrio_data.relay:
                self.relay_detected.emit(self._xrio_data.relay.full_id())
        except Exception as e:
            warnings.append(f"Error emitiendo eventos UI: {e}")

        if warnings:
            QMessageBox.warning(
                self,
                "XRIO cargado con advertencias",
                "\n".join(warnings)
            )

    def _update_relay_bar(self):
        if not self._xrio_data:
            return
        r = self._xrio_data.relay
        self._lbl_relay_info.setText(
            f"🔌 {r.manufacturer}  •  {r.model}  •  FW {r.firmware}")
        na = len(self._xrio_data.analog_signals)
        nb = len(self._xrio_data.binary_signals)
        self._lbl_count.setText(f"{na} analógicas  |  {nb} binarias  |  {na+nb} total")

    # ─── Construir grid de bloques ────────────────────────────────────
    def _build_block_grid(self):
        if not self._xrio_data:
            return

        # Limpiar grid anterior
        self._clear_grid()
        current_row = 0

        # Mostrar BxRBDR (Disturbance Report) como parte importante del XRIO
        if self._xrio_data.disturbance_report_signals:
            dr_widget = DisturbanceReportTable(
                self._xrio_data.disturbance_report_signals,
                self._std_start_map
            )
            self._block_widgets.append(dr_widget)
            self._grid_layout.addWidget(dr_widget, current_row, 0, 1, 2)
            current_row += 1

        # Agrupar señales por bloque
        analog_blocks = self._group_by_block(self._xrio_data.analog_signals)
        binary_blocks = self._group_by_block(self._xrio_data.binary_signals)

        all_blocks: list[tuple[str, list, str]] = []
        for name, sigs in analog_blocks.items():
            all_blocks.append((name, sigs, "analog"))
        for name, sigs in binary_blocks.items():
            all_blocks.append((name, sigs, "binary"))

        if not all_blocks:
            return

        # Menos columnas para mejorar legibilidad y espacio por tabla
        max_cols = 2
        row, col = current_row, 0
        color_idx = 0

        for block_name, signals, sig_type in all_blocks:
            bg, fg = _BLOCK_COLORS[color_idx % len(_BLOCK_COLORS)]
            widget = BlockTable(block_name, signals, sig_type, bg, fg, self._std_start_map)
            self._block_widgets.append(widget)
            self._grid_layout.addWidget(widget, row, col)

            col += 1
            color_idx += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _build_std_start_map(self) -> dict[str, str]:
        """Construye mapa de validación desde XLSX: NOMBRE_SEÑAL -> Start Std."""
        std_map: dict[str, str] = {}
        if not self._xrio_data:
            return std_map

        relay_model = (self._xrio_data.relay.model or "").strip()
        if not relay_model:
            return std_map

        available_models = self._excel_parser.get_available_models()
        best_match = None
        for model in available_models:
            if model.upper() in relay_model.upper() or relay_model.upper() in model.upper():
                best_match = model
                break

        if not best_match:
            return std_map

        standard_data = self._excel_parser.parse_sheet(best_match)
        for _, rows in standard_data.items():
            for row in rows:
                signal_name = (row.get('name') or '').strip()
                start_std = (row.get('group') or '').strip()
                if signal_name and signal_name.upper() not in std_map:
                    std_map[signal_name.upper()] = start_std

        return std_map

    def _group_by_block(self, signals: list) -> OrderedDict:
        blocks = OrderedDict()
        for sig in signals:
            bname = sig.xrio_block or "SIN_BLOQUE"
            if bname not in blocks:
                blocks[bname] = []
            blocks[bname].append(sig)
        return blocks

    def _clear_grid(self):
        for w in self._block_widgets:
            self._grid_layout.removeWidget(w)
            w.deleteLater()
        self._block_widgets.clear()
        
        for w in self._comparison_widgets:
            self._grid_layout.removeWidget(w)
            w.deleteLater()
        self._comparison_widgets.clear()

        # Remover placeholder si existe
        if self._placeholder:
            self._grid_layout.removeWidget(self._placeholder)
            self._placeholder.hide()

    def _build_comparison_grid(self):
        """Construye las tablas de comparación con el estándar de Excel."""
        if not self._xrio_data:
            return
        
        # Obtener el modelo del relé
        relay_model = self._xrio_data.relay.model
        if not relay_model:
            return
        
        # Buscar la hoja correspondiente en el Excel
        available_models = self._excel_parser.get_available_models()
        best_match = None
        for m in available_models:
            if m.upper() in relay_model.upper() or relay_model.upper() in m.upper():
                best_match = m
                break
        
        if not best_match:
            return  # No hay match, no mostrar comparación
        
        # Obtener los bloques del estándar
        standard_data = self._excel_parser.parse_sheet(best_match)
        if not standard_data:
            return
        
        # Mapa de señales del reporte de disturbios: { NOMBRE_UPPER: objeto_señal }
        # Usamos disturbance_report_signals porque son las que tienen 'Trig Oper'
        xrio_dr_map = {}
        if self._xrio_data.disturbance_report_signals:
            for s in self._xrio_data.disturbance_report_signals:
                name_key = s.name.strip().upper()
                xrio_dr_map[name_key] = s
        
        # Determinar la fila de inicio para las tablas de comparación
        # (después de las tablas de señales XRIO)
        current_row = 0
        for w in self._block_widgets:
            current_row = max(current_row, self._grid_layout.getItemPosition(
                self._grid_layout.indexOf(w))[0] + 1)
        
        row, col = current_row, 0
        max_cols = 2
        color_idx = 0
        
        for block_name, std_sigs in standard_data.items():
            bg, fg = _BLOCK_COLORS[color_idx % len(_BLOCK_COLORS)]
            
            # Pasar el mapa de objetos en lugar de lista de nombres
            widget = ComparisonBlockTable(block_name, std_sigs, xrio_dr_map, bg, fg)
            self._comparison_widgets.append(widget)
            self._grid_layout.addWidget(widget, row, col)
            
            col += 1
            color_idx += 1
            if col >= max_cols:
                col = 0
                row += 1

    # ─── Filtro ──────────────────────────────────────────────────────
    def _apply_filter(self):
        text = self._search.text().strip().upper()
        ftype = self._filter_type.currentIndex()  # 0=all, 1=analog, 2=binary

        for w in self._block_widgets:
            if not hasattr(w, 'block_name'):
                w.show()
                continue

            # Filtro por tipo
            is_analog = w.block_name.upper().endswith("RADR") or "RADR" in w.block_name.upper()
            if ftype == 1 and not is_analog:
                w.hide()
                continue
            if ftype == 2 and is_analog:
                w.hide()
                continue

            # Filtro por texto
            if text:
                match = text in w.block_name.upper()
                if not match:
                    # Buscar en señales de la tabla
                    tbl = w._table
                    row_match = False
                    for r in range(tbl.rowCount()):
                        for c in range(tbl.columnCount()):
                            item = tbl.item(r, c)
                            if item and text in item.text().upper():
                                row_match = True
                                break
                        if row_match:
                            break
                    match = row_match
                w.setVisible(match)
            else:
                w.show()

    # ─── API pública ─────────────────────────────────────────────────
    def get_xrio_data(self) -> XRIOData | None:
        return self._xrio_data

    def get_signal_count(self) -> int:
        if not self._xrio_data:
            return 0
        return self._xrio_data.total_signals
