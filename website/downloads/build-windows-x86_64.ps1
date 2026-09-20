$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$PythonBits = python -c "import struct; print(struct.calcsize('P') * 8)"
if ($PythonBits.Trim() -ne '64') { throw "Use Python x86_64 de 64 bits para construir DC Tuner Studio." }
python -m pip install --user pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name DC-Tuner-Studio --add-data "assets;assets" --add-data "docs;docs" --add-data "THIRD_PARTY_NOTICES.md;." dc_tuner_studio.py protocols.py ini_loader.py platform_support.py
Write-Host "Created dist\\DC-Tuner-Studio.exe"
