@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo ==============================================
echo Salud PLC - Inicio compatible con Python 3.15
echo ==============================================
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creando entorno virtual...
  py -3.15 -m venv .venv
  if errorlevel 1 (
    echo No se encontro py -3.15; intentando con Python predeterminado...
    py -m venv .venv
  )
  if errorlevel 1 (
    echo ERROR: No se pudo crear el entorno virtual. Comprueba py -0p
    pause
    exit /b 1
  )
)
echo.
echo [2/3] Instalando / verificando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo ERROR: pip no pudo actualizarse.
  pause
  exit /b 1
)
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
