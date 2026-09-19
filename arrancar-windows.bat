@echo off
setlocal
rem DC TUNER STUDIO para Windows 64-bit
rem Instala Python 3.11+ y: py -m pip install -r requirements-windows.txt
set DCTUNER_PROFILE=%DCTUNER_PROFILE%
if "%DCTUNER_PROFILE%"=="" set DCTUNER_PROFILE=megasquirt
set DCTUNER_PORT=%DCTUNER_PORT%
if "%DCTUNER_PORT%"=="" set DCTUNER_PORT=COM3
set DCTUNER_BAUD=%DCTUNER_BAUD%
if "%DCTUNER_BAUD%"=="" set DCTUNER_BAUD=115200
set DCTUNER_DATA_DIR=%DCTUNER_DATA_DIR%
if "%DCTUNER_DATA_DIR%"=="" set DCTUNER_DATA_DIR=%USERPROFILE%\DC-TUNER-STUDIO-data

echo DC TUNER STUDIO - Windows 64-bit
echo Perfil: %DCTUNER_PROFILE%  Puerto: %DCTUNER_PORT%  Baud: %DCTUNER_BAUD%
py dctuner_web\servidor.py --host 127.0.0.1 --port 8080
endlocal
