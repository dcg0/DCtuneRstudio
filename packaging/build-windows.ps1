$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
python -m pip install --user pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name DC-Tuner-Studio --add-data "assets;assets" dc_tuner_studio.py protocols.py
Write-Host "Created dist\\DC-Tuner-Studio.exe"
