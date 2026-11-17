@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo Configurando PostgreSQL - ES3 Salud PLC
echo ========================================
if not exist ".venv\Scripts\python.exe" (
  py -3.13 -m venv .venv 2>nul
  if errorlevel 1 py -3.12 -m venv .venv 2>nul
  if errorlevel 1 py -m venv .venv
  if errorlevel 1 (
    echo ERROR: necesitas instalar Python 3.12 o 3.13.
    pause
    exit /b 1
  )
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: no fue posible instalar dependencias.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m app.configurar_postgres
if errorlevel 1 (
  echo Configuracion sin terminar. Revisa los mensajes anteriores.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m app.verificar_postgres
pause
