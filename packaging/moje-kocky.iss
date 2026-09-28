; Inno Setup: inštalátor Moje kocky Desktop.
; Zostavenie: scripts\build.ps1 (PyInstaller do build\dist\MojeKocky, potom ISCC).
; Inštaluje sa pre aktuálneho používateľa, bez práv správcu. Údaje appky sú
; v %APPDATA%\MojeKocky a odinštalovanie ich zmaže, len keď to používateľ chce.

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{6C1B7E2A-5D43-4F7B-9B8E-4A2D6F0C9E11}
AppName=Moje kocky
AppVersion={#AppVersion}
AppPublisher=jakubmatisak
AppPublisherURL=https://github.com/jakubmatisak
DefaultDirName={localappdata}\Programs\MojeKocky
DefaultGroupName=Moje kocky
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
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

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\build\dist\MojeKocky\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Moje kocky"; Filename: "{app}\MojeKocky.exe"
Name: "{group}\{cm:UninstallProgram,Moje kocky}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Moje kocky"; Filename: "{app}\MojeKocky.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MojeKocky.exe"; Description: "{cm:LaunchProgram,Moje kocky}"; Flags: nowait postinstall skipifsilent

[Code]
const
  WebView2Key = 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2UserKey = 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function WebView2Installed(): Boolean;
var
  Version: String;
begin
  Result := (RegQueryStringValue(HKLM, WebView2Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'))
    or (RegQueryStringValue(HKCU, WebView2UserKey, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
end;

function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
begin
  Result := True;
  if not WebView2Installed() then
  begin
    if MsgBox('Moje kocky potrebujú súčasť Microsoft Edge WebView2, ktorá na tomto počítači chýba.' + #13#10 +
              'Otvoriť stránku Microsoftu na jej stiahnutie?', mbConfirmation, MB_YESNO) = IDYES then
      ShellExec('open', 'https://developer.microsoft.com/microsoft-edge/webview2/', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\MojeKocky');
    if DirExists(DataDir) then
      if MsgBox('Zmazať aj tvoje údaje (zbierku, fotky, kľúče) v ' + DataDir + '?' + #13#10 +
                'Ak ich necháš, nová inštalácia ich znova použije.', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
