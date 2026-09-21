@echo off
setlocal
rem DCtuneRstudio — Windows 32/64 bits, solo ECU real.
set "ROOT=%~dp0"
if "%DCTUNER_PORT%"=="" set "DCTUNER_PORT=COM3"
if "%DCTUNER_BAUD%"=="" set "DCTUNER_BAUD=115200"
if "%DCTUNER_PROFILE%"=="" set "DCTUNER_PROFILE=megasquirt"
if "%DCTUNER_WEB_PORT%"=="" set "DCTUNER_WEB_PORT=8080"
set "DCTUNER_HOST=127.0.0.1"
set "PYTHONUTF8=1"
cd /d "%ROOT%dctuner_web"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 servidor.py --host "%DCTUNER_HOST%" --port "%DCTUNER_WEB_PORT%" --serie
) else (
  python servidor.py --host "%DCTUNER_HOST%" --port "%DCTUNER_WEB_PORT%" --serie
)
endlocal
