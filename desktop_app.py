"""抖音自动回复系统桌面入口。"""

import logging
import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QDialog

from douyin_automation.config import APP_APPLICATION_NAME, APP_ORGANIZATION_NAME
from douyin_automation.gui.main_window import MainWindow
from douyin_automation.gui.wizard import FirstRunDialog
from douyin_automation.services.backend_orchestrator import BackendOrchestrator
from douyin_automation.utils.paths import get_log_dir


def configure_logging():
    log_path = get_log_dir() / "desktop_app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def main():
    QCoreApplication.setOrganizationName(APP_ORGANIZATION_NAME)
    QCoreApplication.setApplicationName(APP_APPLICATION_NAME)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    configure_logging()

    orchestrator = BackendOrchestrator()
    app.aboutToQuit.connect(orchestrator.shutdown)
    try:
        show_onboarding = False
        if orchestrator.repository.is_first_run():
            dialog = FirstRunDialog(orchestrator.repository)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                orchestrator.shutdown()
                return 0
            show_onboarding = True

        logging.info("桌面端已启动。")
        window = MainWindow(orchestrator, show_onboarding=show_onboarding)
        window.show()
        return app.exec()
    except Exception:
        orchestrator.shutdown()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
