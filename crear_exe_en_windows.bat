@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo     BLOSSOM - CREADOR DE EXE WINDOWS
echo ============================================
python --version >nul 2>&1
if errorlevel 1 (
 echo No se encuentra Python. Este archivo SOLO se usa en el equipo de desarrollo.
 echo Puedes utilizar GitHub Actions para compilar en la nube.
 pause
 exit /b 1
)
python -m pip install --upgrade pip
if errorlevel 1 goto error
python -m pip install pyinstaller pytest -r requirements.txt
if errorlevel 1 goto error
python -m pytest -q
if errorlevel 1 goto error
python -m PyInstaller --noconfirm --clean --onefile --windowed --name BLOSSOM --add-data "assets/logo.png;assets" app.py
if errorlevel 1 goto error
echo.
echo LISTO: dist\BLOSSOM.exe
echo Copia solamente ese EXE a la laptop que usara el negocio.
pause
exit /b 0
:error
echo Ocurrio un error en las pruebas o en la compilacion.
pause
exit /b 1
