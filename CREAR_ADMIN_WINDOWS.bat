@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo No se encontro el entorno virtual. Ejecuta primero INICIAR_WINDOWS.bat.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m app.crear_admin
pause
