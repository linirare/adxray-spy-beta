@echo off
setlocal
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_release.ps1"
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)
echo Build complete. See dist\release.
