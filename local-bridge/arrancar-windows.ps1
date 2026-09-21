# DCtuneRstudio — Windows 32/64 bits, solo ECU real.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:DCTUNER_PORT = if ($env:DCTUNER_PORT) { $env:DCTUNER_PORT } else { 'COM3' }
$env:DCTUNER_BAUD = if ($env:DCTUNER_BAUD) { $env:DCTUNER_BAUD } else { '115200' }
$env:DCTUNER_PROFILE = if ($env:DCTUNER_PROFILE) { $env:DCTUNER_PROFILE } else { 'megasquirt' }
$env:DCTUNER_WEB_PORT = if ($env:DCTUNER_WEB_PORT) { $env:DCTUNER_WEB_PORT } else { '8080' }
$env:DCTUNER_HOST = '127.0.0.1'
$env:PYTHONUTF8 = '1'
$python = (Get-Command py -ErrorAction SilentlyContinue)
if ($python) { & py -3 "$Root\dctuner_web\servidor.py" --host $env:DCTUNER_HOST --port $env:DCTUNER_WEB_PORT --serie }
else { & python "$Root\dctuner_web\servidor.py" --host $env:DCTUNER_HOST --port $env:DCTUNER_WEB_PORT --serie }
