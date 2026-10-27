@echo off
rem Avvia Nightreign Relic Helper. Al primo avvio prepara l'ambiente Python.
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Prima configurazione in corso...
    python -m venv .venv || goto :nopython
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :error
)
start "" ".venv\Scripts\pythonw.exe" app\main.py
exit /b

:nopython
echo Python non trovato. Installalo da https://www.python.org e riprova.
pause
exit /b 1

:error
echo Installazione delle dipendenze non riuscita.
pause
exit /b 1
