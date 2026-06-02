@echo off
REM ESP32 固件下载器启动脚本

echo ========================================
echo   ESP32 Firmware Downloader
echo ========================================
echo.

if "%1"=="ui" goto open_ui
if "%1"=="-ui" goto open_ui

echo 启动命令行版本...
python "%~dp0firmware_downloader.py" %*
goto end

:open_ui
echo 启动 Web UI 版本...
start "" "%~dp0index.html"

:end
