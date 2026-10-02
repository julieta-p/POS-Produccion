@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "SRC=%~dp0POS_Dona_Elina"
set "DEST=%LOCALAPPDATA%\DonaElinaPOS"
set "EXE=%DEST%\POS_Dona_Elina.exe"
set "SHORTCUT=%USERPROFILE%\Desktop\POS Doña Elina.lnk"

if not exist "%SRC%\POS_Dona_Elina.exe" (
    echo [ERROR] No se encuentra el programa en:
    echo %SRC%
    pause
    exit /b 1
)

echo Instalando POS Doña Elina para este usuario...
if not exist "%DEST%" mkdir "%DEST%"

rem Copiar todo EXCEPTO config.ini para no sobrescribir una configuracion existente.
robocopy "%SRC%" "%DEST%" /E /XF config.ini /R:1 /W:1 >nul
if errorlevel 8 (
    echo [ERROR] No se pudo copiar el programa.
    pause
    exit /b 1
)

if not exist "%DEST%\config.ini" copy /Y "%SRC%\config.ini" "%DEST%\config.ini" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\POS Doña Elina.lnk'); $sc.TargetPath = '%EXE%'; $sc.WorkingDirectory = '%DEST%'; $sc.IconLocation = '%DEST%\assets\dona_elina.ico,0'; $sc.Description = 'POS Doña Elina'; $sc.Save()"

if errorlevel 1 (
    echo [ERROR] No se pudo crear el acceso directo.
    pause
    exit /b 1
)

echo.
echo =============================================
echo INSTALACION COMPLETADA
echo =============================================
echo Se creo el acceso directo:
echo   POS Doña Elina
 echo.
echo La aplicacion se encuentra en:
echo   %DEST%
echo.
echo IMPORTANTE: esta instalacion no modifica la estructura de SQL Server.
echo.
choice /C SN /N /M "Deseas abrir POS Doña Elina ahora? [S/N]: "
if errorlevel 2 exit /b 0
start "" "%EXE%"
exit /b 0
