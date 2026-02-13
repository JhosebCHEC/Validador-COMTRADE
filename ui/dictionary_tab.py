"""
Pestaña 3: Diccionario de Alias
Base de datos dinámica que mapea nombres técnicos de relé a nombres estándar.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QHeaderView,
    QMessageBox, QFrame, QDialog, QFormLayout, QDialogButtonBox,
    QFileDialog, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from core.alias_database import AliasDatabase
from models.signal_models import AliasEntry, ProtectionFunction


class AddAliasDialog(QDialog):
    """Diálogo para agregar o editar un alias."""

    def __init__(self, entry: AliasEntry = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            "Editar Alias" if entry else "Agregar Alias")
        self.setMinimumWidth(450)
        self._entry = entry
        self._setup_ui()
        if entry:
            self._populate(entry)

    def _setup_ui(self):
        layout = QFormLayout(self)

        self._relay_name = QLineEdit()
        self._relay_name.setPlaceholderText(
            "Nombre técnico del relé (ej: IL1_Mag)")
        layout.addRow("Nombre Técnico (Relé):", self._relay_name)

        self._standard_name = QLineEdit()
        self._standard_name.setPlaceholderText(
            "Nombre estándar COMTRADE (ej: IA)")
        layout.addRow("Nombre Estándar:", self._standard_name)

        self._relay_model = QLineEdit()
        self._relay_model.setPlaceholderText("Ej: SIPROTEC 7SJ85")
        layout.addRow("Modelo del Relé:", self._relay_model)

        self._signal_type = QComboBox()
        self._signal_type.addItems(["analog", "binary"])
        layout.addRow("Tipo de Señal:", self._signal_type)

        self._function = QComboBox()
        for func in ProtectionFunction:
            self._function.addItem(func.value, func.name)
        layout.addRow("Función:", self._function)

        self._validated = QCheckBox("Validado manualmente")
        layout.addRow(self._validated)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _populate(self, entry: AliasEntry):
        self._relay_name.setText(entry.relay_name)
        self._standard_name.setText(entry.standard_name)
        self._relay_model.setText(entry.relay_model)
        idx = self._signal_type.findText(entry.signal_type)
        if idx >= 0:
            self._signal_type.setCurrentIndex(idx)
        for i in range(self._function.count()):
            if self._function.itemText(i) == entry.function:
                self._function.setCurrentIndex(i)
                break
        self._validated.setChecked(entry.validated)

    def get_entry(self) -> AliasEntry:
        return AliasEntry(
            relay_name=self._relay_name.text().strip(),
            standard_name=self._standard_name.text().strip(),
            relay_model=self._relay_model.text().strip(),
            signal_type=self._signal_type.currentText(),
            function=self._function.currentText(),
            auto_detected=False,
            validated=self._validated.isChecked(),
        )


class DictionaryTab(QWidget):
    """Pestaña del diccionario de alias."""

    alias_changed = pyqtSignal()

    def __init__(self, alias_db: AliasDatabase, parent=None):
        super().__init__(parent)
        self._db = alias_db
        self._setup_ui()
        self._refresh_table()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # --- Barra superior con estadísticas ---
        stats_bar = self._create_stats_bar()
        main_layout.addWidget(stats_bar)

        # --- Barra de búsqueda y filtros ---
        filter_bar = self._create_filter_bar()
        main_layout.addWidget(filter_bar)

        # --- Tabla principal ---
        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "Nombre Técnico", "Nombre Estándar", "Modelo Relé",
            "Tipo", "Función", "Auto-detectado", "Validado", "Acciones"
        ])
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(
            7, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(7, 160)
        main_layout.addWidget(self._table, 1)

        # --- Barra de acciones ---
        actions_bar = self._create_actions_bar()
        main_layout.addWidget(actions_bar)

    def _create_stats_bar(self) -> QFrame:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("📖 Diccionario de Alias")
        title.setObjectName("sectionTitle")

        self._lbl_total = QLabel("Total: 0")
        self._lbl_total.setObjectName("subtitle")

        self._lbl_validated = QLabel("Validados: 0")
        self._lbl_validated.setObjectName("subtitle")
        self._lbl_validated.setStyleSheet("color: #4caf50;")

        self._lbl_auto = QLabel("Auto-detectados: 0")
        self._lbl_auto.setObjectName("subtitle")
        self._lbl_auto.setStyleSheet("color: #ff9800;")

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self._lbl_total)
        layout.addWidget(QLabel("  |  "))
        layout.addWidget(self._lbl_validated)
        layout.addWidget(QLabel("  |  "))
        layout.addWidget(self._lbl_auto)

        return frame

    def _create_filter_bar(self) -> QFrame:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        # Búsqueda por texto
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(
            "🔍 Buscar por nombre técnico o estándar...")
        self._search_input.textChanged.connect(self._apply_filter)

        # Filtro por modelo
        lbl_model = QLabel("Modelo:")
        self._combo_model = QComboBox()
        self._combo_model.addItem("Todos", "ALL")
        self._combo_model.currentIndexChanged.connect(self._apply_filter)

        # Filtro por función
        lbl_func = QLabel("Función:")
        self._combo_function = QComboBox()
        self._combo_function.addItem("Todas", "ALL")
        for func in ProtectionFunction:
            self._combo_function.addItem(func.value, func.name)
        self._combo_function.currentIndexChanged.connect(self._apply_filter)

        # Filtro por tipo
        lbl_type = QLabel("Tipo:")
        self._combo_type = QComboBox()
        self._combo_type.addItems(["Todos", "analog", "binary"])
        self._combo_type.currentIndexChanged.connect(self._apply_filter)

        layout.addWidget(self._search_input, 2)
        layout.addWidget(lbl_model)
        layout.addWidget(self._combo_model)
        layout.addWidget(lbl_func)
        layout.addWidget(self._combo_function)
        layout.addWidget(lbl_type)
        layout.addWidget(self._combo_type)

        return frame

    def _create_actions_bar(self) -> QFrame:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        self._btn_add = QPushButton("➕  Agregar Alias")
        self._btn_add.setProperty("cssClass", "primary")
        self._btn_add.clicked.connect(self._on_add)

        self._btn_remove = QPushButton("🗑  Eliminar Seleccionado")
        self._btn_remove.setProperty("cssClass", "danger")
        self._btn_remove.clicked.connect(self._on_remove)

        self._btn_validate = QPushButton("✅  Marcar Validado")
        self._btn_validate.setProperty("cssClass", "success")
        self._btn_validate.clicked.connect(self._on_validate)

        self._btn_import = QPushButton("📥  Importar JSON")
        self._btn_import.clicked.connect(self._on_import)

        self._btn_export = QPushButton("📤  Exportar JSON")
        self._btn_export.clicked.connect(self._on_export)

        self._btn_clear = QPushButton("🗑  Limpiar Todo")
        self._btn_clear.clicked.connect(self._on_clear)

        layout.addWidget(self._btn_add)
        layout.addWidget(self._btn_remove)
        layout.addWidget(self._btn_validate)
        layout.addStretch()
        layout.addWidget(self._btn_import)
        layout.addWidget(self._btn_export)
        layout.addWidget(self._btn_clear)

        return frame

    # ======================== TABLA ========================

    def _refresh_table(self):
        """Recarga toda la tabla desde la base de datos."""
        entries = self._db.get_all()

        self._table.setRowCount(0)
        self._table.setRowCount(len(entries))

        validated_count = 0
        auto_count = 0

        for row, entry in enumerate(entries):
            self._table.setItem(row, 0, QTableWidgetItem(entry.relay_name))
            self._table.setItem(
                row, 1, QTableWidgetItem(entry.standard_name))
            self._table.setItem(
                row, 2, QTableWidgetItem(entry.relay_model))
            self._table.setItem(
                row, 3, QTableWidgetItem(entry.signal_type))
            self._table.setItem(
                row, 4, QTableWidgetItem(entry.function))

            # Auto-detectado
            auto_item = QTableWidgetItem("✓" if entry.auto_detected else "—")
            auto_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if entry.auto_detected:
                auto_item.setForeground(QColor("#ff9800"))
                auto_count += 1
            self._table.setItem(row, 5, auto_item)

            # Validado
            val_item = QTableWidgetItem("✓" if entry.validated else "✗")
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if entry.validated:
                val_item.setForeground(QColor("#4caf50"))
                validated_count += 1
            else:
                val_item.setForeground(QColor("#f44336"))
            self._table.setItem(row, 6, val_item)

            # Botón editar
            btn_edit = QPushButton("✏️ Editar")
            btn_edit.clicked.connect(
                lambda _, e=entry: self._on_edit(e))
            self._table.setCellWidget(row, 7, btn_edit)

        # Actualizar contadores
        self._lbl_total.setText(f"Total: {len(entries)}")
        self._lbl_validated.setText(f"Validados: {validated_count}")
        self._lbl_auto.setText(f"Auto-detectados: {auto_count}")

        # Actualizar filtro de modelos
        self._combo_model.blockSignals(True)
        current_model = self._combo_model.currentText()
        self._combo_model.clear()
        self._combo_model.addItem("Todos", "ALL")
        for model in self._db.get_models():
            self._combo_model.addItem(model)
        idx = self._combo_model.findText(current_model)
        if idx >= 0:
            self._combo_model.setCurrentIndex(idx)
        self._combo_model.blockSignals(False)

    def _apply_filter(self):
        """Aplica los filtros a la tabla."""
        search = self._search_input.text().lower()
        model_filter = self._combo_model.currentData()
        func_filter = self._combo_function.currentData()
        type_filter = self._combo_type.currentText()

        for row in range(self._table.rowCount()):
            relay_name = self._table.item(row, 0)
            std_name = self._table.item(row, 1)
            model = self._table.item(row, 2)
            sig_type = self._table.item(row, 3)
            function = self._table.item(row, 4)

            # Búsqueda por texto
            text_match = (not search
                          or (relay_name and search in
                              relay_name.text().lower())
                          or (std_name and search in
                              std_name.text().lower()))

            # Filtro modelo
            model_match = (model_filter == "ALL"
                           or (model and model.text()
                               == self._combo_model.currentText()))

            # Filtro función
            func_match = True
            if func_filter and func_filter != "ALL":
                try:
                    func_val = ProtectionFunction[func_filter].value
                    func_match = (function and
                                  function.text() == func_val)
                except KeyError:
                    pass

            # Filtro tipo
            type_match = (type_filter == "Todos"
                          or (sig_type and
                              sig_type.text() == type_filter))

            visible = (text_match and model_match
                       and func_match and type_match)
            self._table.setRowHidden(row, not visible)

    # ======================== ACCIONES ========================

    def _on_add(self):
        dlg = AddAliasDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            entry = dlg.get_entry()
            if not entry.relay_name or not entry.standard_name:
                QMessageBox.warning(
                    self, "Datos incompletos",
                    "Nombre técnico y estándar son obligatorios.")
                return
            self._db.add(entry)
            self._refresh_table()
            self.alias_changed.emit()

    def _on_edit(self, entry: AliasEntry):
        dlg = AddAliasDialog(entry, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Remover viejo y agregar nuevo
            self._db.remove(entry.relay_model, entry.relay_name)
            new_entry = dlg.get_entry()
            self._db.add(new_entry)
            self._refresh_table()
            self.alias_changed.emit()

    def _on_remove(self):
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Sin selección",
                                "Seleccione una fila para eliminar.")
            return

        relay_name = self._table.item(row, 0).text()
        relay_model = self._table.item(row, 2).text()

        reply = QMessageBox.question(
            self, "Confirmar eliminación",
            f"¿Eliminar alias '{relay_name}' → '{self._table.item(row, 1).text()}'?")

        if reply == QMessageBox.StandardButton.Yes:
            self._db.remove(relay_model, relay_name)
            self._refresh_table()
            self.alias_changed.emit()

    def _on_validate(self):
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Sin selección",
                                "Seleccione una fila para validar.")
            return

        relay_name = self._table.item(row, 0).text()
        relay_model = self._table.item(row, 2).text()
        entry = self._db.get(relay_model, relay_name)
        if entry:
            entry.validated = True
            self._db.add(entry)
            self._refresh_table()
            self.alias_changed.emit()

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar Diccionario",
            "", "Archivos JSON (*.json)")
        if path:
            try:
                count = self._db.import_from_json(path)
                QMessageBox.information(
                    self, "Importación completada",
                    f"Se importaron {count} nuevas entradas.")
                self._refresh_table()
                self.alias_changed.emit()
            except Exception as e:
                QMessageBox.critical(
                    self, "Error de importación", str(e))

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Diccionario",
            "alias_dictionary.json", "Archivos JSON (*.json)")
        if path:
            try:
                self._db.export_to_json(path)
                QMessageBox.information(
                    self, "Exportación completada",
                    f"Diccionario exportado a:\n{path}")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error de exportación", str(e))

    def _on_clear(self):
        reply = QMessageBox.question(
            self, "Confirmar limpieza",
            "¿Eliminar TODAS las entradas del diccionario?\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._db.clear()
            self._refresh_table()
            self.alias_changed.emit()

    # ======================== API PÚBLICA ========================

    def refresh(self):
        """Recarga la tabla desde la BD."""
        self._refresh_table()

    def add_entries_from_validation(self, entries: list):
        """Agrega entradas múltiples desde la validación."""
        for entry in entries:
            self._db.add(entry)
        self._refresh_table()
