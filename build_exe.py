"""
打包构建脚本：PyInstaller + Playwright 浏览器依赖
生成 dist/DouyinAutoReply/ 目录，可直接分发给用户使用
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
DIST_DIR = ROOT / "dist" / "DouyinAutoReply"
PLAYWRIGHT_SRC = Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Local" / "ms-playwright"


def step(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}\n")


def run_pyinstaller():
    step("第1步: PyInstaller 打包 Python 应用")
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "-y", "desktop_app.spec"]
    print(f"执行: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=str(ROOT))
    print(f"打包输出目录: {DIST_DIR}")


def copy_playwright_browsers():
    step("第2步: 复制 Playwright 浏览器依赖")
    if not PLAYWRIGHT_SRC.exists():
        print(f"错误: 找不到 Playwright 浏览器目录: {PLAYWRIGHT_SRC}")
        print("请先运行: playwright install chromium")
        sys.exit(1)

    dest = DIST_DIR / "ms-playwright"
    if dest.exists():
        shutil.rmtree(dest)

    # 只复制 chromium（本项目只用 chromium 通过 CDP 连接 BitBrowser）
    browser_dirs = [d for d in PLAYWRIGHT_SRC.iterdir()
                    if d.is_dir() and d.name.startswith("chromium")]

    if not browser_dirs:
        print("错误: 未找到 chromium 浏览器，请运行: playwright install chromium")
        sys.exit(1)

    dest.mkdir(parents=True, exist_ok=True)
    for d in browser_dirs:
        print(f"  复制: {d.name} -> {dest / d.name}")
        shutil.copytree(d, dest / d.name)

    # 复制 .links 文件夹（如果存在）
    links_dir = PLAYWRIGHT_SRC / ".links"
    if links_dir.exists():
        shutil.copytree(links_dir, dest / ".links")

    print(f"Playwright 浏览器已复制到: {dest}")


def create_launcher_env():
    step("第3步: 创建环境配置（让 Playwright 使用本地浏览器）")
    env_script = DIST_DIR / "_set_env.bat"
    env_script.write_text(
        '@echo off\n'
        'set PLAYWRIGHT_BROWSERS_PATH=%~dp0ms-playwright\n'
        '"%~dp0DouyinAutoReply.exe"\n',
        encoding="utf-8",
    )
    print(f"启动脚本已创建: {env_script}")


def create_launcher_vbs():
    """创建无黑框启动器"""
    vbs_content = (
        'Set WshShell = CreateObject("WScript.Shell")\n'
        'WshShell.Environment("Process").Item("PLAYWRIGHT_BROWSERS_PATH") = '
        'Replace(WScript.ScriptFullName, WScript.ScriptName, "") & "ms-playwright"\n'
        'WshShell.Run Replace(WScript.ScriptFullName, WScript.ScriptName, "") & "DouyinAutoReply.exe", 1, False\n'
    )
    vbs_path = DIST_DIR / "启动抖音自动回复.vbs"
    vbs_path.write_text(vbs_content, encoding="utf-8")
    print(f"VBS 启动器已创建: {vbs_path}")


def create_playwright_env_hook():
    """创建 runtime hook 设置 PLAYWRIGHT_BROWSERS_PATH 环境变量"""
    hook_content = (
        'import os\n'
        'import sys\n'
        '\n'
        'if getattr(sys, "frozen", False):\n'
        '    app_dir = os.path.dirname(sys.executable)\n'
        '    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(app_dir, "ms-playwright")\n'
    )
    hook_path = ROOT / "_playwright_env_hook.py"
    hook_path.write_text(hook_content, encoding="utf-8")
    print(f"Runtime hook 已创建: {hook_path}")
    return hook_path


def update_spec_with_hook(hook_path):
    """更新 spec 文件加入 runtime hook"""
    import re
    spec_path = ROOT / "desktop_app.spec"
    content = spec_path.read_text(encoding="utf-8")

    if str(hook_path) not in content:
        content = content.replace(
            "runtime_hooks=[],",
            f'runtime_hooks=[r"{hook_path}"],',
        )
        spec_path.write_text(content, encoding="utf-8")
        print(f"已更新 spec 文件加入 runtime hook")


def main():
    print("抖音自动回复系统 - 打包构建")
    print(f"项目根目录: {ROOT}")
    print(f"Playwright 浏览器源: {PLAYWRIGHT_SRC}")

    # 0. 创建 runtime hook 并更新 spec
    step("第0步: 准备 runtime hook（设置 Playwright 浏览器路径）")
    hook_path = create_playwright_env_hook()
    update_spec_with_hook(hook_path)

    # 1. PyInstaller 打包
    run_pyinstaller()

    # 2. 复制 Playwright 浏览器
    copy_playwright_browsers()

    # 3. 创建启动器
    create_launcher_env()
    create_launcher_vbs()

    # 完成
    step("打包完成!")
    print(f"输出目录: {DIST_DIR}")
    print(f"")
    print(f"分发方式:")
    print(f"  将整个 dist/DouyinAutoReply/ 文件夹打包为 zip")
    print(f"  用户解压后双击 '启动抖音自动回复.vbs' 即可运行")
    print(f"  或直接运行 DouyinAutoReply.exe（需系统已设置 PLAYWRIGHT_BROWSERS_PATH）")
    print()

    total_size = sum(f.stat().st_size for f in DIST_DIR.rglob("*") if f.is_file())
    print(f"总大小: {total_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
