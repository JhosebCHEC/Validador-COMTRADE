"""
Validador de Estándar — Relés de Protección
=============================================
Aplicación de escritorio para gestión y validación de señales
de relés de protección según IEEE C37.111 (COMTRADE) y OMICRON XRIO.

Autor: Desarrollador Senior - Sector Eléctrico
"""
import sys
import os

# Agregar raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    # Habilitar DPI scaling para pantallas HiDPI
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("Validador de Estándar")
    app.setOrganizationName("ProtectionRelay")
    app.setApplicationVersion("1.0.0")

    # Crear ventana principal
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
