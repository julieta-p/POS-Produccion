@echo off
setlocal EnableExtensions
set "DEST=%LOCALAPPDATA%\DonaElinaPOS"
set "SHORTCUT=%USERPROFILE%\Desktop\POS Doña Elina.lnk"

if exist "%SHORTCUT%" del /q "%SHORTCUT%"
if exist "%DEST%" rmdir /s /q "%DEST%"

echo POS Doña Elina fue desinstalado para este usuario.
pause
