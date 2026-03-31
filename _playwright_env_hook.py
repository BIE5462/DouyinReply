import os
import sys

if getattr(sys, "frozen", False):
    app_dir = os.path.dirname(sys.executable)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(app_dir, "ms-playwright")
