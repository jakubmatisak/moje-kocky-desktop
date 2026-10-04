; Inno Setup: inštalátor Moje kocky Desktop.
; Zostavenie: scripts\build.ps1 (PyInstaller do build\dist\MojeKocky, potom ISCC).
; Inštalátor si vypýta práva správcu (Windows ukáže otázku UAC) a program ide
; do Program Files pre všetkých používateľov počítača. Údaje má každý používateľ
; vlastné v %APPDATA%\MojeKocky; založí si ich appka sama, inštalátor na ne
; nesiaha a odinštalovanie ich zmaže, len keď to používateľ chce (pozri
; uninstall-data.iss).
; Staršiu inštaláciu len pre jedného používateľa (0.1.x v %LOCALAPPDATA%)
; odstráni PrepareToInstall, pozri old-install.iss.

; Verzia je verzia appky (backend/pyproject.toml); build.ps1 inú nepustí.
#ifndef AppVersion
  #define AppVersion "1.3.0"
#endif
; Vlastnosti → Podrobnosti súboru chcú len čísla (1.0.0rc1 → 1.0.0.0);
; build.ps1 ich berie z packaging\version_info.py, tie isté ako MojeKocky.exe.
#ifndef AppFileVersion
  #define AppFileVersion AppVersion
#endif

[Setup]
AppId={{6C1B7E2A-5D43-4F7B-9B8E-4A2D6F0C9E11}
AppName=Moje kocky
AppVersion={#AppVersion}
VersionInfoVersion={#AppFileVersion}
VersionInfoTextVersion={#AppVersion}
VersionInfoProductTextVersion={#AppVersion}
AppPublisher=jakubmatisak
AppPublisherURL=https://github.com/jakubmatisak
; {autopf} je v 64-bitovom režime (ArchitecturesInstallIn64BitMode) C:\Program Files.
DefaultDirName={autopf}\MojeKocky
DefaultGroupName=Moje kocky
DisableProgramGroupPage=yes
; Bez PrivilegesRequiredOverridesAllowed: inštalácia len pre seba sa vybrať nedá.
PrivilegesRequired=admin
OutputDir=..\build\installer
OutputBaseFilename=MojeKocky-Setup-{#AppVersion}
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\MojeKocky.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
CloseApplications=yes

[Languages]
Name: "slovak"; MessagesFile: "compiler:Languages\Slovak.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

; Vlastné texty v oboch jazykoch (CustomMessages); inde v skripte nie je
; žiadny text pre používateľa, len záznamy do denníka.
#include "messages.iss"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\build\dist\MojeKocky\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Licencie MIT, BSD a Apache chcú svoj text pri šírenom programe (packaging\notices.py).
Source: "..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "..\build\THIRD-PARTY-NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Moje kocky"; Filename: "{app}\MojeKocky.exe"
Name: "{group}\{cm:UninstallProgram,Moje kocky}"; Filename: "{uninstallexe}"
Name: "{group}\{cm:ThirdPartyNotices}"; Filename: "{app}\THIRD-PARTY-NOTICES.txt"
Name: "{autodesktop}\Moje kocky"; Filename: "{app}\MojeKocky.exe"; Tasks: desktopicon

[Run]
; Pod účtom, ktorý inštalátor spustil, nie ako správca: appka si údaje založí
; v jeho %APPDATA%.
Filename: "{app}\MojeKocky.exe"; Description: "{cm:LaunchProgram,Moje kocky}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
; Úlohy automatickej obnovy cien všetkých používateľov (lego_desktop.scheduler);
; keď nie sú, chyba nevadí.
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -Command ""Get-ScheduledTask -TaskPath '\Moje kocky\' -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false"""; Flags: runhidden; RunOnceId: "DeletePriceRefreshTasks"

[Code]
#include "old-install.iss"
#include "uninstall-data.iss"

const
  WebView2Key = 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2UserKey = 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

// WebView2 pre všetkých (HKLM) alebo len pre používateľa (HKCU). HKCU je účtu,
// pod ktorým Setup po otázke UAC beží: pri hesle iného správcu na bežnom
// účte je to HKCU správcu, takže WebView2 nainštalovaný len pre bežného
// používateľa sa nenájde a inštalátor zbytočne ponúkne stiahnutie. Vo
// Windows 10/11 býva WebView2 pre všetkých, preto sa to ďalej nerieši.
function WebView2Installed(): Boolean;
var
  Version: String;
begin
  Result := (RegQueryStringValue(HKLM, WebView2Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'))
    or (RegQueryStringValue(HKCU, WebView2UserKey, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
end;

// Stránka sa otvorí v prehliadači toho, kto inštalátor spustil
// (ShellExecAsOriginalUser), nie ako správca: Setup beží so zvýšenými
// právami a pri hesle iného správcu pod jeho účtom, s jeho profilom
// a priečinkom Stiahnuté.
function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
begin
  Result := True;
  if not WebView2Installed() then
  begin
    if MsgBox(CustomMessage('WebView2Missing'), mbConfirmation, MB_YESNO) = IDYES then
      ShellExecAsOriginalUser('open', 'https://developer.microsoft.com/microsoft-edge/webview2/', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
  end;
end;

// Starú inštaláciu len pre tohto používateľa (0.1.x) odstráni pred kopírovaním
// súborov; keď to nejde, inštalácia skončí s hláškou (čo vtedy ostane, popisuje
// RemoveOldInstall).
// {localappdata}, {userappdata} a HKCU sú účtu, pod ktorým inštalátor po otázke
// UAC beží (obmedzenie popisuje old-install.iss).
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  OldDir: String;
begin
  Result := '';
  if FindOldInstall(OldUninstallKey, ExpandConstant('{localappdata}\Programs\MojeKocky'), ExpandConstant('{app}'), OldDir) then
    Result := RemoveOldInstall(OldUninstallKey, OldDir, ExpandConstant('{userappdata}'), ExpandConstant('{userprograms}\Moje kocky'), ExpandConstant('{userdesktop}\Moje kocky.lnk'));
end;

// Program je pre všetkých, údaje má každý používateľ vlastné. {userappdata} je
// profil účtu, pod ktorým odinštalovanie beží (po otázke UAC); údaje ostatných
// používateľov ostanú. Keď to nie je ten, kto sedí pri počítači (bežný účet
// s heslom iného správcu), nemaže sa nič a hláška povie, kde údaje ostali
// (uninstall-data.iss). Otázka menuje účet a jeho priečinok, predvolená
// odpoveď je Nie, aj v tichom režime s /SUPPRESSMSGBOXES.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir, RunAs, SessionUser: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\MojeKocky');
    RunAs := GetUserNameString;
    SessionUser := SessionUserName();
    if OtherAccountElevated(RunAs, SessionUser) then
    begin
      Log('Odinštalovanie beží pod účtom ' + RunAs + ', pri počítači je ' + SessionUser + ': údaje sa nemažú.');
      SuppressibleMsgBox(OtherAccountNotice(RunAs, SessionUser), mbInformation, MB_OK, IDOK);
    end
    else if DirExists(DataDir) then
      if SuppressibleMsgBox(DeleteDataQuestion(RunAs, DataDir), mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
