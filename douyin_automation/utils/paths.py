"""应用目录路径。"""

from pathlib import Path

from PySide6.QtCore import QStandardPaths


def get_app_data_dir():
    location = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    if not location:
        location = str(Path.cwd() / ".douyin_auto_reply")
    path = Path(location)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path():
    return get_app_data_dir() / "app.db"


def get_log_dir():
    path = get_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
