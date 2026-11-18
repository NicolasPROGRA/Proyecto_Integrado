@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo ==============================================
echo Salud PLC - Evaluacion ES3 con PostgreSQL
echo ==============================================
if not exist ".env" (
  echo Primero configura tu BD con CONFIGURAR_POSTGRESQL_WINDOWS.bat
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creando entorno virtual...
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
  echo Preparando el instalador de dependencias de Python...
  ".venv\Scripts\python.exe" -m ensurepip --upgrade
  if errorlevel 1 goto pip_invalido
)
echo.
echo [2/3] Instalando / verificando dependencias...
".venv\Scripts\python.exe" -m pip install --prefer-binary -r requirements.txt
if errorlevel 1 (
  echo ERROR: Fallo la instalacion. Copia las ultimas lineas del error.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, sqlalchemy, pydantic, argon2; print('Dependencias principales comprobadas.')"
if errorlevel 1 (
  echo ERROR: Falta alguna biblioteca o es incompatible.
  pause
  exit /b 1
)
echo.
echo Comprobando PostgreSQL y 14 tablas...
".venv\Scripts\python.exe" -m app.verificar_postgres
if errorlevel 1 (
  echo ERROR: PostgreSQL no esta preparado. Ejecuta CONFIGURAR_POSTGRESQL_WINDOWS.bat
  pause
  exit /b 1
)
echo.
echo [3/3] Iniciando servidor...
echo Abre http://127.0.0.1:8000 en el navegador.
echo Para crear administrador usa CREAR_ADMIN_WINDOWS.bat en otra terminal.
echo Presiona Ctrl+C para salir.
echo.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 (
  echo ERROR al iniciar el servidor.
  pause
  exit /b 1
)
pause
exit /b 0

:entorno_invalido
echo.
echo ERROR: El entorno virtual .venv esta incompleto o apunta a otro Python.
echo En PowerShell, dentro de la carpeta del proyecto, ejecuta:
echo   Rename-Item -Path ".venv" -NewName ".venv_anterior"
echo Despues vuelve a ejecutar INICIAR_WINDOWS.bat.
echo Si no existe .venv, revisa las versiones disponibles con: py -0p
echo No borres .env ni la carpeta instance.
pause
exit /b 1

:pip_invalido
echo ERROR: Python se encontro, pero no fue posible preparar pip.
echo Ejecuta: ".venv\Scripts\python.exe" -m ensurepip --upgrade
pause
exit /b 1
