@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY_CMD=py -3.14"
set "VENV=.venv_pc314"

echo ============================================================
echo   DONA ELINA - CONSTRUCCION DEL PROGRAMA PARA WINDOWS
echo   Python 3.14.x + PyInstaller
echo ============================================================
echo.

%PY_CMD% -c "import sys; print('Python detectado:', sys.version)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se encontro Python 3.14.
    echo Instala Python 3.14.7 y vuelve a ejecutar este archivo.
    pause
    exit /b 1
)

if not exist "%VENV%\Scripts\python.exe" (
    echo [1/6] Creando entorno aislado para Python 3.14...
    %PY_CMD% -m venv "%VENV%"
    if errorlevel 1 goto :error
)

call "%VENV%\Scripts\activate.bat"
if errorlevel 1 goto :error

echo [2/6] Actualizando pip...
python -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [3/6] Instalando dependencias...
python -m pip install -r requirements_pc_314.txt
if errorlevel 1 goto :error

echo [4/6] Verificando sintaxis del proyecto...
python -m compileall -q app.py ui db servicios aplicar_cantidades_salida.py prueba_planificacion.py
if errorlevel 1 goto :error

echo [5/6] Generando el ejecutable...
if exist "build_pc314" rmdir /s /q "build_pc314"
if exist "dist" rmdir /s /q "dist"
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build_pc314 "POS_DONA_ELINA_PC_314.spec"
if errorlevel 1 goto :error

if not exist "dist\POS_Dona_Elina\POS_Dona_Elina.exe" (
    echo [ERROR] PyInstaller termino, pero no se encontro el EXE esperado.
    goto :error
)

rem La configuracion SQL se mantiene como archivo externo.
rem Se copia de forma explicita para que el paquete de distribucion
rem siempre contenga config.ini, aunque PyInstaller no lo haya copiado.
if exist "dist\POS_Dona_Elina\config.ini" del /q "dist\POS_Dona_Elina\config.ini" >nul 2>&1
copy /Y "config.ini" "dist\POS_Dona_Elina\config.ini" >nul
if errorlevel 1 (
    echo [ERROR] No se pudo copiar config.ini a dist.
    goto :error
)
if exist "dist\POS_Dona_Elina\_internal\config.ini" (
    del /q "dist\POS_Dona_Elina\_internal\config.ini" >nul 2>&1
)
if exist "dist\POS_Dona_Elina\_internal\config.ini" (
    echo [ERROR] config.ini quedo dentro de _internal.
    goto :error
)

echo [6/6] Preparando paquete para las otras PC...
if exist "ENTREGA_PC" rmdir /s /q "ENTREGA_PC"
mkdir "ENTREGA_PC"
xcopy "dist\POS_Dona_Elina" "ENTREGA_PC\POS_Dona_Elina" /E /I /Y >nul
if errorlevel 1 goto :error

copy /Y "INSTALAR_POS_DONA_ELINA.bat" "ENTREGA_PC\INSTALAR_POS_DONA_ELINA.bat" >nul
copy /Y "DESINSTALAR_POS_DONA_ELINA.bat" "ENTREGA_PC\DESINSTALAR_POS_DONA_ELINA.bat" >nul
copy /Y "LEEME_DISTRIBUCION_PC.txt" "ENTREGA_PC\LEEME_DISTRIBUCION_PC.txt" >nul

if not exist "ENTREGA_PC\POS_Dona_Elina\POS_Dona_Elina.exe" (
    echo [ERROR] Falta el ejecutable en ENTREGA_PC.
    goto :error
)

if not exist "ENTREGA_PC\POS_Dona_Elina\config.ini" (
    echo [ERROR] Falta config.ini en ENTREGA_PC.
    goto :error
)

echo.
echo ============================================================
echo CONSTRUCCION FINALIZADA CORRECTAMENTE
echo ============================================================
echo.
echo El programa quedo en:
echo   dist\POS_Dona_Elina\POS_Dona_Elina.exe
echo.
echo Para las otras computadoras, entrega solamente la carpeta:
echo   ENTREGA_PC
echo.
echo En cada PC se ejecuta una sola vez:
echo   INSTALAR_POS_DONA_ELINA.bat
echo.
echo Ese instalador crea el acceso directo en el Escritorio.
echo No requiere Python en las otras PC.
echo.
pause
exit /b 0

:error
echo.
echo [ERROR] La construccion no se pudo completar.
echo Revisa el mensaje anterior y conserva esta carpeta para diagnostico.
pause
exit /b 1
