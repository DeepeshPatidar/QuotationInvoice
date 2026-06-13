import sys

from PyQt6.QtWidgets import QApplication

from app.container import ApplicationContainer
from app.ui.main_window import MainWindow


def create_window(container: ApplicationContainer | None = None) -> MainWindow:
    container = container or ApplicationContainer.build()
    window = MainWindow(
        container.database,
        container.document_generator,
        container.quotation_service,
        container.invoice_service,
    )
    window._application_container = container
    return window


def main() -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    window = create_window()
    window.showMaximized()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
