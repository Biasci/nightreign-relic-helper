@echo off
rem Crea dist\NightreignRelicHelper\NightreignRelicHelper.exe (non serve Python per avviarlo).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" python -m venv .venv || exit /b 1
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt pyinstaller || exit /b 1
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed ^
    --name NightreignRelicHelper ^
    --paths app ^
    --add-data "app\ui;app\ui" ^
    --add-data "data;data" ^
    --add-data "research;research" ^
    app\main.py || exit /b 1
echo.
echo Fatto: dist\NightreignRelicHelper\NightreignRelicHelper.exe
