@echo off
setlocal

rem Check for Python

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Requirement Python not found.
    
    set python_install_link=https://www.python.org/downloads/
    echo This script will now automatically download the installer, please execute it before continuing! If this fails, download and install manually from "%python_install_link%"
    set "installer_path=%script_dir%pythoninstaller.exe"

    powershell Invoke-WebRequest https://starrynightsmp.net/groupxyz/python-3.12.1-amd64.exe -OutFile "%installer_path%"

    echo Press any button to continue

    pause
)

rem Script

echo checking modules...

pip show keyboard >nul 2>&1
if %errorlevel% neq 0 (
    pip install keyboard
)
pip show comtypes >nul 2>&1
if %errorlevel% neq 0 (
    pip install comtypes
)
pip show pycaw >nul 2>&1
if %errorlevel% neq 0 (
    pip install pycaw
)
pip show colorama >nul 2>&1
if %errorlevel% neq 0 (
    pip install colorama
)
pip show packaging >nul 2>&1
if %errorlevel% neq 0 (
    pip install packaging
)
pip show customtkinter >nul 2>&1
if %errorlevel% neq 0 (
    pip install customtkinter
)

echo Finished checking modules
echo Please run hotkey_application.pyw to start the application, you can close this window now!

pause

endlocal