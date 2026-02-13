"""
Pestaña 2: Estándar COMTRADE (XLSX)
Interfaz dedicada a leer, organizar por tablas/bloques y hacer CRUD sobre el archivo Excel.
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QPushButton, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame,
    QFileDialog, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.excel_standard_parser import ExcelStandardParser


_BLOCK_COLORS = [
    ("#00883A", "#ffffff"),
    ("#00883A", "#ffffff"),
    ("#00883A", "#ffffff"),
    ("#00883A", "#ffffff"),
    ("#00883A", "#ffffff"),
    ("#00883A", "#ffffff"),
]


class XlsxBlockTable(QFrame):
    """Widget de edición para un bloque/tabla del XLSX."""

    data_changed = pyqtSignal(str, list)  # block_name, rows

    def __init__(self, block_name: str, rows: list[dict], color_bg: str, color_fg: str, parent=None):
        super().__init__(parent)
        self._block_name = block_name
        self._rows = rows
        self._syncing = False
        self._setup_ui(color_bg, color_fg)

    def _setup_ui(self, color_bg: str, color_fg: str):
        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet(
            "XlsxBlockTable { border: 1px solid #dee2e6; border-radius: 4px; background-color: #ffffff; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel(f"  {self._block_name} ({len(self._rows)})")
        header.setFixedHeight(24)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header.setStyleSheet(
            f"background-color: {color_bg}; color: {color_fg}; border-top-left-radius: 3px; border-top-right-radius: 3px;")
        layout.addWidget(header)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["Señal", "Descripción", "Start Std"])
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.AllEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(24)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(2, 110)
        self._table.cellChanged.connect(self._on_cell_changed)

        visible_rows = max(6, min(len(self._rows), 12))
        table_height = 34 + (visible_rows * 24)
        self._table.setMinimumHeight(table_height)
        self.setMinimumHeight(table_height + 28)

        layout.addWidget(self._table)
        self._populate()

    def _populate(self):
        self._syncing = True
        try:
            self._table.setRowCount(0)
            self._table.setRowCount(len(self._rows))
            for r, row_data in enumerate(self._rows):
                name = (row_data.get('name') or '').strip()
                description = (row_data.get('description') or '').strip()
                group = (row_data.get('group') or '').strip()
                name_it = QTableWidgetItem(name)
                desc_it = QTableWidgetItem(description)
                group_it = QTableWidgetItem(group)
                group_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(r, 0, name_it)
                self._table.setItem(r, 1, desc_it)
                self._table.setItem(r, 2, group_it)
        finally:
            self._syncing = False

    def _on_cell_changed(self, row: int, col: int):
        if self._syncing:
            return
        self.data_changed.emit(self._block_name, self.get_rows())

    def get_rows(self) -> list[dict]:
        rows = []
        for r in range(self._table.rowCount()):
            n_item = self._table.item(r, 0)
            d_item = self._table.item(r, 1)
            g_item = self._table.item(r, 2)
            name = n_item.text().strip() if n_item else ''
            description = d_item.text().strip() if d_item else ''
            group = g_item.text().strip() if g_item else ''
            if not name:
                continue
            rows.append({'name': name, 'description': description, 'group': group})
        return rows

    def add_row(self):
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(""))
        self._table.setItem(row, 1, QTableWidgetItem(""))
        self._table.setItem(row, 2, QTableWidgetItem(""))
        self.data_changed.emit(self._block_name, self.get_rows())

    def delete_selected_row(self) -> bool:
        row = self._table.currentRow()
        if row < 0:
            return False
        self._table.removeRow(row)
        self.data_changed.emit(self._block_name, self.get_rows())
        return True


class ComtradeTab(QWidget):
    """Pestaña del estándar COMTRADE basada completamente en XLSX."""

    standard_changed = pyqtSignal()
    comtrade_loaded = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        root_excel = "Estándar COMTRADE.xlsx"
        data_excel = os.path.join("data", "Estándar COMTRADE.xlsx")
        self._excel_path = root_excel if os.path.exists(root_excel) else data_excel

        self._excel_parser: ExcelStandardParser | None = None
        self._excel_data: dict[str, dict[str, list[dict]]] = {}
        self._block_widgets: dict[str, XlsxBlockTable] = {}
        self._setup_ui()
        self._load_default_xlsx()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Barra superior
        top = QHBoxLayout()
        top.setSpacing(6)

        self._btn_open = QPushButton("📂 Abrir XLSX")
        self._btn_open.setProperty("cssClass", "primary")
        self._btn_open.clicked.connect(self._on_open_xlsx)

        self._btn_save = QPushButton("💾 Guardar XLSX")
        self._btn_save.setProperty("cssClass", "success")
        self._btn_save.clicked.connect(self._on_save_xlsx)

        self._combo_sheet = QComboBox()
        self._combo_sheet.setMinimumWidth(180)
        self._combo_sheet.currentTextChanged.connect(self._on_sheet_changed)

        self._combo_block = QComboBox()
        self._combo_block.setMinimumWidth(180)

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Buscar tabla...")
        self._search.setMaximumWidth(220)
        self._search.textChanged.connect(self._apply_filter)

        self._lbl_file = QLabel("Sin XLSX cargado")
        self._lbl_file.setObjectName("subtitle")

        top.addWidget(self._btn_open)
        top.addWidget(self._btn_save)
        top.addWidget(QLabel("Hoja:"))
        top.addWidget(self._combo_sheet)
        top.addWidget(QLabel("Tabla objetivo:"))
        top.addWidget(self._combo_block)
        top.addWidget(self._search)
        top.addWidget(self._lbl_file, 1)
        root.addLayout(top)

        # Barra CRUD
        crud = QHBoxLayout()
        crud.setSpacing(6)

        self._btn_add_sheet = QPushButton("➕ Hoja")
        self._btn_add_sheet.clicked.connect(self._on_add_sheet)

        self._btn_del_sheet = QPushButton("🗑 Hoja")
        self._btn_del_sheet.setProperty("cssClass", "danger")
        self._btn_del_sheet.clicked.connect(self._on_delete_sheet)

        self._btn_add_block = QPushButton("➕ Tabla")
        self._btn_add_block.clicked.connect(self._on_add_block)

        self._btn_del_block = QPushButton("🗑 Tabla")
        self._btn_del_block.setProperty("cssClass", "danger")
        self._btn_del_block.clicked.connect(self._on_delete_block)

        self._btn_add_row = QPushButton("➕ Fila")
        self._btn_add_row.clicked.connect(self._on_add_row)

        self._btn_del_row = QPushButton("🗑 Fila")
        self._btn_del_row.setProperty("cssClass", "danger")
        self._btn_del_row.clicked.connect(self._on_delete_row)

        self._lbl_stats = QLabel("0 tablas")
        self._lbl_stats.setObjectName("subtitle")

        crud.addWidget(self._btn_add_sheet)
        crud.addWidget(self._btn_del_sheet)
        crud.addWidget(self._btn_add_block)
        crud.addWidget(self._btn_del_block)
        crud.addWidget(self._btn_add_row)
        crud.addWidget(self._btn_del_row)
        crud.addStretch()
        crud.addWidget(self._lbl_stats)
        root.addLayout(crud)

        # Scroll + grid de tablas
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background-color: #f4f5f7; }")

        self._container = QWidget()
        self._grid = QVBoxLayout(self._container)
        self._grid.setContentsMargins(2, 2, 2, 2)
        self._grid.setSpacing(6)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll.setWidget(self._container)
        root.addWidget(self._scroll, 1)

    def _load_default_xlsx(self):
        if not os.path.exists(self._excel_path):
            self._lbl_file.setText("No se encontró el archivo estándar XLSX")
            return
        try:
            self._excel_parser = ExcelStandardParser(self._excel_path)
            self._excel_data = self._excel_parser.parse_all_sheets()
            self._lbl_file.setText(f"📄 {os.path.basename(self._excel_path)}")
            self._refresh_sheet_selector()
            self.comtrade_loaded.emit(None)
        except Exception as e:
            QMessageBox.critical(self, "Error XLSX", str(e))

    def _on_open_xlsx(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir archivo estándar XLSX",
            "",
            "Archivos Excel (*.xlsx);;Todos los archivos (*)"
        )
        if not file_path:
            return
        try:
            self._excel_path = file_path
            self._excel_parser = ExcelStandardParser(file_path)
            self._excel_data = self._excel_parser.parse_all_sheets()
            self._lbl_file.setText(f"📄 {os.path.basename(file_path)}")
            self._refresh_sheet_selector()
            self.comtrade_loaded.emit(None)
        except Exception as e:
            QMessageBox.critical(self, "Error al abrir XLSX", str(e))

    def _refresh_sheet_selector(self):
        self._combo_sheet.blockSignals(True)
        self._combo_sheet.clear()
        for sheet_name in self._excel_data.keys():
            self._combo_sheet.addItem(sheet_name)
        self._combo_sheet.blockSignals(False)

        if self._combo_sheet.count() > 0:
            self._combo_sheet.setCurrentIndex(0)
            self._on_sheet_changed(self._combo_sheet.currentText())
        else:
            self._combo_block.clear()
            self._clear_block_widgets()
            self._update_stats()

    def _on_sheet_changed(self, sheet_name: str):
        self._refresh_block_selector(sheet_name)
        self._build_block_tables(sheet_name)
        self._update_stats()

    def _refresh_block_selector(self, sheet_name: str):
        self._combo_block.clear()
        blocks = self._excel_data.get(sheet_name, {})
        for block_name in blocks.keys():
            self._combo_block.addItem(block_name)

    def _build_block_tables(self, sheet_name: str):
        self._clear_block_widgets()

        blocks = self._excel_data.get(sheet_name, {})
        if not blocks:
            empty = QLabel("No hay tablas detectadas en esta hoja.")
            empty.setStyleSheet("color: #6c757d; padding: 8px;")
            self._grid.addWidget(empty)
            self._block_widgets["__empty__"] = empty  # type: ignore
            return

        color_idx = 0
        for block_name, rows in blocks.items():
            bg, fg = _BLOCK_COLORS[color_idx % len(_BLOCK_COLORS)]
            widget = XlsxBlockTable(block_name, rows, bg, fg)
            widget.data_changed.connect(self._on_block_data_changed)
            self._grid.addWidget(widget)
            self._block_widgets[block_name] = widget
            color_idx += 1

    def _clear_block_widgets(self):
        for w in self._block_widgets.values():
            self._grid.removeWidget(w)
            w.deleteLater()
        self._block_widgets.clear()

    def _on_block_data_changed(self, block_name: str, rows: list):
        sheet = self._combo_sheet.currentText().strip()
        if not sheet or block_name not in self._excel_data.get(sheet, {}):
            return
        self._excel_data[sheet][block_name] = rows
        self.standard_changed.emit()
        self._update_stats()

    def _on_add_block(self):
        sheet = self._combo_sheet.currentText().strip()
        if not sheet:
            QMessageBox.warning(self, "Sin hoja", "Seleccione una hoja primero.")
            return

        block_name, ok = QInputDialog.getText(self, "Nueva tabla", "Nombre del bloque (ej: B7RBDR):")
        block_name = block_name.strip() if block_name else ""
        if not ok or not block_name:
            return

        blocks = self._excel_data.setdefault(sheet, {})
        if block_name in blocks:
            QMessageBox.warning(self, "Duplicado", "Ya existe una tabla con ese nombre.")
            return

        blocks[block_name] = []
        self._refresh_block_selector(sheet)
        idx = self._combo_block.findText(block_name)
        if idx >= 0:
            self._combo_block.setCurrentIndex(idx)
        self._build_block_tables(sheet)
        self.standard_changed.emit()
        self._update_stats()

    def _on_add_sheet(self):
        sheet_name, ok = QInputDialog.getText(self, "Nueva hoja", "Nombre de la hoja:")
        sheet_name = sheet_name.strip() if sheet_name else ""
        if not ok or not sheet_name:
            return

        if sheet_name in self._excel_data:
            QMessageBox.warning(self, "Duplicado", "Ya existe una hoja con ese nombre.")
            return

        self._excel_data[sheet_name] = {}
        self._refresh_sheet_selector()
        idx = self._combo_sheet.findText(sheet_name)
        if idx >= 0:
            self._combo_sheet.setCurrentIndex(idx)
        self.standard_changed.emit()
        self._update_stats()

    def _on_delete_sheet(self):
        sheet = self._combo_sheet.currentText().strip()
        if not sheet:
            QMessageBox.warning(self, "Sin selección", "Seleccione una hoja para eliminar.")
            return

        if len(self._excel_data) <= 1:
            QMessageBox.warning(self, "Operación no permitida", "Debe existir al menos una hoja en el archivo.")
            return

        reply = QMessageBox.question(self, "Confirmar", f"¿Eliminar la hoja '{sheet}' completa?")
        if reply != QMessageBox.StandardButton.Yes:
            return

        if sheet in self._excel_data:
            del self._excel_data[sheet]

        self._refresh_sheet_selector()
        self.standard_changed.emit()
        self._update_stats()

    def _on_delete_block(self):
        sheet = self._combo_sheet.currentText().strip()
        block = self._combo_block.currentText().strip()
        if not sheet or not block:
            QMessageBox.warning(self, "Sin selección", "Seleccione una tabla objetivo.")
            return

        reply = QMessageBox.question(self, "Confirmar", f"¿Eliminar la tabla '{block}'?")
        if reply != QMessageBox.StandardButton.Yes:
            return

        if block in self._excel_data.get(sheet, {}):
            del self._excel_data[sheet][block]
        self._refresh_block_selector(sheet)
        self._build_block_tables(sheet)
        self.standard_changed.emit()
        self._update_stats()

    def _on_add_row(self):
        block = self._combo_block.currentText().strip()
        widget = self._block_widgets.get(block)
        if not isinstance(widget, XlsxBlockTable):
            QMessageBox.warning(self, "Sin selección", "Seleccione una tabla objetivo.")
            return
        widget.add_row()

    def _on_delete_row(self):
        block = self._combo_block.currentText().strip()
        widget = self._block_widgets.get(block)
        if not isinstance(widget, XlsxBlockTable):
            QMessageBox.warning(self, "Sin selección", "Seleccione una tabla objetivo.")
            return
        if not widget.delete_selected_row():
            QMessageBox.warning(self, "Sin selección", "Seleccione una fila dentro de la tabla.")

    def _on_save_xlsx(self):
        if not self._excel_parser:
            QMessageBox.warning(self, "Sin archivo", "No hay XLSX cargado.")
            return
        try:
            self._excel_parser.save_all_sheets(self._excel_data)
            QMessageBox.information(self, "Guardado", "Cambios guardados en el archivo XLSX.")
            self.standard_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))

    def _apply_filter(self):
        text = self._search.text().strip().upper()
        for name, widget in self._block_widgets.items():
            if not isinstance(widget, XlsxBlockTable):
                continue
            widget.setVisible(not text or text in name.upper())

    def _update_stats(self):
        sheet = self._combo_sheet.currentText().strip()
        blocks = self._excel_data.get(sheet, {}) if sheet else {}
        total_tables = len(blocks)
        total_rows = sum(len(rows) for rows in blocks.values())
        self._lbl_stats.setText(f"{total_tables} tablas | {total_rows} filas")

    # API de compatibilidad con MainWindow
    def get_config(self):
        return None

    def get_all_channel_names(self) -> list:
        sheet = self._combo_sheet.currentText().strip()
        blocks = self._excel_data.get(sheet, {}) if sheet else {}
        names = []
        for rows in blocks.values():
            for row in rows:
                name = (row.get('name') or '').strip()
                if name:
                    names.append(name)
        return names
