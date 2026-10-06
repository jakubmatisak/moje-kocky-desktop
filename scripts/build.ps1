# Zostavenie Moje kocky Desktop: frontend, PyInstaller a inštalátor (Inno Setup).
# Použitie:  powershell -ExecutionPolicy Bypass -File scripts\build.ps1 [-Version 1.4.0]
# Súbor je v UTF-8 s BOM, inak by Windows PowerShell 5.1 pokazil diakritiku.
param([string]$Version = "1.4.0")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# Verzia inštalátora je verzia appky. Appka podľa nej pri štarte novej verzie
# zálohuje databázu; inštalátor 1.0.1 s appkou 1.0.0 by aktualizáciu bez
# migrácie nezálohoval. Kontrola ide pred zostavením, nech nič nezačne.
$pyproject = Join-Path $root "backend\pyproject.toml"
$appVersion = (Select-String -Path $pyproject -Pattern '^version = "(.+)"$' | Select-Object -First 1).Matches[0].Groups[1].Value
if ($Version -ne $appVersion) {
  throw "Verzia $Version sa nezhoduje s verziou appky $appVersion v backend\pyproject.toml. Zvýš ju tam (potom uv lock a verziu vo frontend\package.json aj package-lock.json) alebo zostav s -Version $appVersion."
}

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
# Podrobnosti súboru inštalátora chcú len čísla (1.0.0rc1 -> 1.0.0.0), tie isté ako MojeKocky.exe.
$fileVersion = uv run python ..\packaging\version_info.py $Version | Select-Object -Last 1
if ($LASTEXITCODE -ne 0 -or -not $fileVersion) { throw "Číselná verzia pre inštalátor sa nezistila" }
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
& $iscc "/DAppVersion=$Version" "/DAppFileVersion=$fileVersion" (Join-Path $root "packaging\moje-kocky.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup zlyhal" }
Write-Host "Hotovo: build\installer\MojeKocky-Setup-$Version.exe"
