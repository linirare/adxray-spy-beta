# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

project_root = Path(SPECPATH)
browser_path = Path(
    os.environ.get("PLAYWRIGHT_BROWSERS_PATH", project_root / ".playwright-browsers")
)
if not browser_path.exists():
    raise SystemExit(
        "Bundled Chromium is missing. Set PLAYWRIGHT_BROWSERS_PATH and run "
        "`python -m playwright install chromium` before building."
    )

playwright_datas, playwright_binaries, playwright_hiddenimports = collect_all("playwright")

a = Analysis(
    ["adxray_spy_gui.py"],
    pathex=[str(project_root)],
    binaries=playwright_binaries,
    datas=playwright_datas + [("README.md", "."), (str(browser_path), "ms-playwright")],
    hiddenimports=playwright_hiddenimports + ["adxray_spy_core", "openpyxl", "et_xmlfile"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "ad_creative_analysis",
        "analyze",
        "collect",
        "content_analysis",
        "cross_platform",
        "deep_dive",
        "fb_ad_spy",
        "install_opencv",
        "recommend",
        "run_all",
        "viral_deepdive",
        "lxml",
        "numpy",
        "pandas",
        "PIL",
        "pygame",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="adxray-spy",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="adxray-spy",
)
