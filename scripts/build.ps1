# Zostavenie Moje kocky Desktop: frontend, PyInstaller a inštalátor (Inno Setup).
# Použitie:  powershell -ExecutionPolicy Bypass -File scripts\build.ps1 [-Version 0.1.0]
param([string]$Version = "0.1.0")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "1/3 Frontend (režim desktop)"
Push-Location (Join-Path $root "frontend")
npm run build-desktop
if ($LASTEXITCODE -ne 0) { throw "Zostavenie frontendu zlyhalo" }
Pop-Location

Write-Host "2/3 Program (PyInstaller) a licencie tretích strán"
Push-Location (Join-Path $root "backend")
uv run python ..\packaging\notices.py ..\build\THIRD-PARTY-NOTICES.txt
if ($LASTEXITCODE -ne 0) { throw "Zoznam licencií sa nevytvoril" }
uv run pyinstaller --noconfirm --clean --distpath ..\build\dist --workpath ..\build\work ..\packaging\moje-kocky.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller zlyhal" }
Pop-Location

Write-Host "3/3 Inštalátor (Inno Setup)"
$iscc = @(
  (Get-Command iscc -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
  "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $iscc) {
  Write-Warning "Inno Setup (ISCC.exe) sa nenašiel. Program je v build\dist\MojeKocky, inštalátor sa nezostavil."
  exit 0
}
& $iscc "/DAppVersion=$Version" (Join-Path $root "packaging\moje-kocky.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup zlyhal" }
Write-Host "Hotovo: build\installer\MojeKocky-Setup-$Version.exe"
