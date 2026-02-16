@echo off
title ValoSwitcher Setup
color 0B
echo ============================================================
echo              ValoSwitcher - Setup Script
echo ============================================================
echo.

:: Check for Python
echo [1/4] Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found! Downloading Python installer...
    echo.

    :: Download Python installer
    powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe' -OutFile '%TEMP%\python_installer.exe'}"

    if not exist "%TEMP%\python_installer.exe" (
        echo ERROR: Failed to download Python installer.
        echo Please download Python manually from https://www.python.org/downloads/
        echo IMPORTANT: Check "Add Python to PATH" during installation!
        pause
        exit /b 1
    )

    echo Installing Python 3.12...
    echo IMPORTANT: This will install Python with PATH enabled.
    "%TEMP%\python_installer.exe" /passive InstallAllUsers=0 PrependPath=1 Include_test=0

    if %errorlevel% neq 0 (
        echo ERROR: Python installation failed.
        echo Please install Python manually from https://www.python.org/downloads/
        echo IMPORTANT: Check "Add Python to PATH" during installation!
        pause
        exit /b 1
    )

    :: Refresh PATH
    echo Refreshing PATH...
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

    del "%TEMP%\python_installer.exe" >nul 2>&1
    echo Python installed successfully!
) else (
    for /f "tokens=*" %%i in ('python --version') do echo Found %%i
)
echo.

:: Remove conflicting packages
echo [2/4] Removing conflicting packages...
pip uninstall PyQt5 PyQt5-Qt5 PyQt5-sip PyQt5-Frameless-Window -y >nul 2>&1
pip uninstall PySide2 PySide6 -y >nul 2>&1
echo Done.
echo.

:: Install requirements
echo [3/4] Installing requirements...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install some requirements.
    echo Trying individual installs...
    for /f "tokens=*" %%i in (requirements.txt) do (
        pip install %%i >nul 2>&1
    )
)
echo.

:: Verify installation
echo [4/4] Verifying installation...
python -c "import PyQt6; import qfluentwidgets; import cloudscraper; import psutil; print('All packages OK!')" 2>nul
if %errorlevel% neq 0 (
    echo WARNING: Some packages may not have installed correctly.
    echo Try running: pip install -r requirements.txt
) else (
    echo All packages verified!
)

echo.
echo ============================================================
echo              Setup Complete!
echo ============================================================
echo.
echo To run ValoSwitcher:
echo   python main.py
echo.
echo To build .exe:
echo   python build.py
echo.
echo Config will be created at:
echo   Documents\ValoSwitcher\config.ini
echo ============================================================
echo.
pause
