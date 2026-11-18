@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo Configurando PostgreSQL - ES3 Salud PLC
echo ========================================
if not exist ".venv\Scripts\python.exe" (
  echo Creando entorno virtual de Python...
  py -3.13 -m venv .venv 2>nul
  if errorlevel 1 py -3.12 -m venv .venv 2>nul
  if errorlevel 1 py -3.11 -m venv .venv 2>nul
  if errorlevel 1 py -3 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" goto entorno_invalido
".venv\Scripts\python.exe" -c "import sys" >nul 2>&1
if errorlevel 1 goto entorno_invalido
".venv\Scripts\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m ensurepip --upgrade
  if errorlevel 1 goto entorno_invalido
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
exit /b 0

:entorno_invalido
echo.
echo ERROR: Python no se pudo iniciar desde .venv.
echo Si existe la carpeta .venv, renombrala en PowerShell:
echo   Rename-Item -Path ".venv" -NewName ".venv_anterior"
echo Vuelve a ejecutar este archivo y conserva .env e instance.
echo Para ver Python instalado, usa: py -0p
pause
exit /b 1
