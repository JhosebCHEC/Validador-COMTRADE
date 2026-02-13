"""
Estilos de la aplicación: Tema corporativo (paleta basada en logo CELSIA/EPM).
"""

APP_THEME = """
/* ========== BASE ========== */
QMainWindow, QWidget {
    background-color: #f3f6f4;
    color: #1f2937;
    font-family: "Segoe UI", sans-serif;
    font-size: 12px;
}

/* ========== TABS ========== */
QTabWidget::pane {
    border: 1px solid #d6e2db;
    border-radius: 8px;
    background-color: #ffffff;
    top: -1px;
    margin-top: 8px;
}

QTabWidget::tab-bar {
    left: 6px;
}

QTabBar::tab {
    background-color: #edf3ef;
    color: #3f4d44;
    padding: 8px 18px;
    margin-right: 6px;
    border: 1px solid #d6e2db;
    border-radius: 8px;
    font-weight: 600;
    min-width: 160px;
    min-height: 18px;
}

QTabBar::tab:selected {
    background-color: #00883A;
    color: #ffffff;
    border: 1px solid #00883A;
}

QTabBar::tab:hover:!selected {
    background-color: #e4efe7;
    border-color: #bcd0c2;
}

QTabBar::tab:!selected {
    margin-top: 2px;
}

QTabBar QToolButton {
    background-color: transparent;
    border: none;
}

/* ========== TABLES ========== */
QTableWidget, QTableView {
    background-color: #ffffff;
    alternate-background-color: #f7faf8;
    gridline-color: #d6e2db;
    border: 1px solid #d6e2db;
    selection-background-color: #dcefe0;
    selection-color: #1f2937;
    font-size: 11px;
}

QTableWidget::item, QTableView::item {
    padding: 2px 5px;
    border-bottom: 1px solid #e6eee9;
}

QHeaderView::section {
    background-color: #e7efe9;
    color: #3f4d44;
    padding: 3px 5px;
    border: none;
    border-right: 1px solid #d6e2db;
    border-bottom: 1px solid #bfd0c5;
    font-weight: 600;
    font-size: 11px;
}

/* ========== TREE VIEW ========== */
QTreeWidget, QTreeView {
    background-color: #ffffff;
    alternate-background-color: #f7faf8;
    border: 1px solid #d6e2db;
    selection-background-color: #dcefe0;
    selection-color: #1f2937;
    outline: none;
}

QTreeWidget::item, QTreeView::item {
    padding: 2px 5px;
}

QTreeWidget::item:selected, QTreeView::item:selected {
    background-color: #dcefe0;
}

/* ========== BUTTONS ========== */
QPushButton {
    background-color: #f7faf8;
    color: #1f2937;
    border: 1px solid #d2ded6;
    border-radius: 3px;
    padding: 4px 12px;
    font-weight: 500;
    min-height: 22px;
}

QPushButton:hover {
    background-color: #edf4ef;
    border-color: #b6c9bc;
}

QPushButton:pressed {
    background-color: #dbe8df;
}

QPushButton:disabled {
    color: #9fb1a6;
}

QPushButton[cssClass="primary"] {
    background-color: #00883A;
    color: white;
    border: none;
    font-weight: 600;
}
QPushButton[cssClass="primary"]:hover {
    background-color: #007533;
}

QPushButton[cssClass="success"] {
    background-color: #5AA61A;
    color: white;
    border: none;
    font-weight: 600;
}
QPushButton[cssClass="success"]:hover {
    background-color: #4f9316;
}

QPushButton[cssClass="danger"] {
    background-color: #a64040;
    color: white;
    border: none;
}
QPushButton[cssClass="danger"]:hover {
    background-color: #913838;
}

/* ========== INPUTS ========== */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #c8d7cd;
    border-radius: 3px;
    padding: 4px 7px;
    selection-background-color: #dcefe0;
}

QLineEdit:focus {
    border-color: #7fbf2a;
}

QLineEdit::placeholder {
    color: #95a8a0;
}

/* ========== COMBO BOX ========== */
QComboBox {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #c8d7cd;
    border-radius: 3px;
    padding: 4px 7px;
    min-height: 22px;
}

QComboBox:hover {
    border-color: #7fbf2a;
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #c8d7cd;
    selection-background-color: #dcefe0;
}

/* ========== SCROLL BARS ========== */
QScrollBar:vertical {
    background: transparent;
    width: 7px;
}

QScrollBar::handle:vertical {
    background: #b8c8be;
    border-radius: 3px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #9eb4a6;
}

QScrollBar:horizontal {
    background: transparent;
    height: 7px;
}

QScrollBar::handle:horizontal {
    background: #b8c8be;
    border-radius: 3px;
}

QScrollBar::add-line, QScrollBar::sub-line {
    height: 0; width: 0;
}

/* ========== SPLITTER ========== */
QSplitter::handle {
    background-color: #d6e2db;
    width: 1px;
}

/* ========== LABELS ========== */
QLabel {
    color: #212529;
    background: transparent;
}

QLabel#sectionTitle {
    font-size: 11px;
    font-weight: 700;
    color: #00883A;
    padding: 1px 0;
}

QLabel#subtitle {
    color: #5b6b62;
    font-size: 11px;
}

/* ========== GROUP BOX ========== */
QGroupBox {
    border: 1px solid #d6e2db;
    border-radius: 3px;
    margin-top: 6px;
    padding: 6px;
    padding-top: 14px;
    font-weight: 600;
    color: #5b6b62;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    color: #3f4d44;
    font-size: 11px;
}

/* ========== STATUS BAR ========== */
QStatusBar {
    background-color: #00883A;
    color: white;
    font-size: 11px;
    padding: 1px 6px;
    min-height: 18px;
    max-height: 20px;
}

QStatusBar::item {
    border: none;
}

/* ========== PROGRESS BAR ========== */
QProgressBar {
    background-color: #e7efe9;
    border: none;
    border-radius: 3px;
    text-align: center;
    height: 14px;
}

QProgressBar::chunk {
    background-color: #5AA61A;
    border-radius: 2px;
}

/* ========== TOOLTIP ========== */
QToolTip {
    background-color: #343a40;
    color: #fff;
    border: none;
    border-radius: 3px;
    padding: 3px 7px;
    font-size: 11px;
}
"""
