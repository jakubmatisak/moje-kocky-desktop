// Prechod zo starej inštalácie pre jedného používateľa (verzie 0.1.x).
//
// Tie boli v %LOCALAPPDATA%\Programs\MojeKocky s kľúčom odinštalovania v HKCU.
// Od 1.0.0 je program v Program Files pre všetkých (kľúč v HKLM), takže stará
// inštalácia by ostala vedľa novej: dvakrát v ponuke Štart aj v zozname
// aplikácií. Starý odinštalátor sa nespúšťa, lebo sa pýta, či zmazať aj údaje
// (a v tichom režime by sa spýtal tiež). Odstráni sa priamo: priečinok
// programu, kľúč v HKCU a staré skratky. Údaje v %APPDATA%\MojeKocky (zbierka,
// zálohy, secret.key) ostávajú, na tie nesiaha nič z tohto súboru.
//
// Funkcie berú cesty a kľúč ako parametre, nie ako konštanty, aby ich
// tests/test_installer.py skúšal na dočasných priečinkoch. Hlavný skript
// (moje-kocky.iss, PrepareToInstall) im dá cesty používateľa, pod ktorým
// inštalátor po otázke UAC beží. Obmedzenie: keď bežný používateľ zadá heslo
// iného účtu správcu, sú to HKCU a profil toho správcu, takže stará
// inštalácia bežného používateľa ostane; odinštaluje si ju sám (údaje nechá).
// Komentáre sú cez //, lebo komentár v zložených zátvorkách by skončil pri
// prvej konštante ako {app}.

const
  OldUninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{6C1B7E2A-5D43-4F7B-9B8E-4A2D6F0C9E11}_is1';
  OldProgramDirEnd = '\programs\mojekocky';
  // Ako dopadlo mazanie priečinka starého programu (RemoveOldProgramDir).
  OldDirGone = 0;
  OldDirRunning = 1;
  OldDirLeftovers = 2;
  OldDirRefused = 3;

function NormalPath(const Path: String): String;
begin
  Result := AnsiLowercase(RemoveBackslash(Trim(Path)));
end;

function PathEndsWith(const Path, Suffix: String): Boolean;
begin
  Result := (Length(Path) >= Length(Suffix))
    and (Copy(Path, Length(Path) - Length(Suffix) + 1, Length(Suffix)) = Suffix);
end;

function PathIsUnder(const Path, Parent: String): Boolean;
begin
  Result := Copy(Path, 1, Length(Parent) + 1) = Parent + '\';
end;

// Poistka pred mazaním: len úplná cesta s písmenom disku, ktorá končí
// \Programs\MojeKocky, bez „..“ a lomiek, a ktorá nie je priečinkom s údajmi
// používateľa (UserAppData = %APPDATA%), nie je v ňom ani ho neobsahuje.
function IsOldProgramDir(const Dir, UserAppData: String): Boolean;
var
  D, Data: String;
begin
  D := NormalPath(Dir);
  Data := NormalPath(UserAppData);
  Result := (Length(D) > 3) and (Copy(D, 2, 2) = ':\')
    and PathEndsWith(D, OldProgramDirEnd)
    and (Pos('\..', D) = 0) and (Pos('/', D) = 0)
    and (Length(Data) > 3)
    and (D <> Data)
    and not PathIsUnder(D, Data)
    and not PathIsUnder(Data, D);
end;

// Zmaže priečinok starého programu. Najprv MojeKocky.exe: bežiaci program
// Windows zmazať nedovolí, a vtedy sa nezmaže nič iné (OldDirRunning).
// Premenovanie priečinka to nepozná, to Windows dovolí aj s bežiacim
// programom. Keď potom DelTree niečo nezmaže (súbor drží otvorený iný
// proces: antivírus, konzola či Prieskumník v priečinku), program je už
// preč a ostane len zvyšok (OldDirLeftovers).
function RemoveOldProgramDir(const Dir, UserAppData: String): Integer;
var
  D: String;
begin
  Result := OldDirRefused;
  if not IsOldProgramDir(Dir, UserAppData) then
    Exit;
  D := RemoveBackslash(Trim(Dir));
  if DirExists(D) then
  begin
    if FileExists(D + '\MojeKocky.exe') and not DeleteFile(D + '\MojeKocky.exe') then
    begin
      Log('Stará inštalácia beží, MojeKocky.exe sa nedá zmazať: ' + D);
      Result := OldDirRunning;
      Exit;
    end;
    DelTree(D, True, True, True);
  end;
  if DirExists(D) then
  begin
    Log('Priečinok starej inštalácie sa nepodarilo celý zmazať: ' + D);
    Result := OldDirLeftovers;
  end
  else
    Result := OldDirGone;
end;

// Skratky starej inštalácie: ponuka Štart (priečinok Moje kocky, zmaže sa, len
// keď v ňom nič iné neostalo) a ikona na ploche. Inde nič.
procedure DeleteOldShortcuts(const StartMenuDir, DesktopLink: String);
var
  Found: TFindRec;
  Dir: String;
begin
  Dir := RemoveBackslash(Trim(StartMenuDir));
  if PathEndsWith(NormalPath(Dir), '\moje kocky') then
  begin
    if FindFirst(Dir + '\*.lnk', Found) then
    begin
      try
        repeat
          DeleteFile(Dir + '\' + Found.Name);
        until not FindNext(Found);
      finally
        FindClose(Found);
      end;
    end;
    RemoveDir(Dir);
  end;
  if PathEndsWith(NormalPath(DesktopLink), '\moje kocky.lnk') then
    DeleteFile(DesktopLink);
end;

function SamePath(const A, B: String): Boolean;
begin
  Result := NormalPath(A) = NormalPath(B);
end;

// Je tu stará inštalácia? Kľúč v HKCU (priečinok z InstallLocation), a keď
// kľúč chýba, predvolený priečinok, ak existuje a nie je to priečinok novej
// inštalácie (AppDir). Dir = priečinok programu, prázdny, keď ho kľúč nepozná.
function FindOldInstall(const UninstallKey, DefaultDir, AppDir: String; var Dir: String): Boolean;
var
  Location: String;
begin
  Dir := '';
  Result := RegKeyExists(HKCU, UninstallKey);
  if Result then
  begin
    if RegQueryStringValue(HKCU, UninstallKey, 'InstallLocation', Location) and (Trim(Location) <> '') then
      Dir := RemoveBackslash(Trim(Location))
    else if RegQueryStringValue(HKCU, UninstallKey, 'Inno Setup: App Path', Location) then
      Dir := RemoveBackslash(Trim(Location));
  end
  else if DirExists(DefaultDir) and not SamePath(DefaultDir, AppDir) then
  begin
    Dir := RemoveBackslash(Trim(DefaultDir));
    Result := True;
  end;
end;

// Odstráni starú inštaláciu: priečinok programu, kľúč odinštalovania a skratky.
// Vráti prázdny text, alebo hlášku, pre ktorú inštalácia nepokračuje. Pri
// cudzom priečinku a bežiacom programe nie je zmazané nič. Keď z priečinka
// ostal zvyšok, kľúč a skratky ostanú tiež: opakovaná inštalácia podľa nich
// starú inštaláciu nájde a mazanie dokončí. Údaje v UserAppData ostávajú vždy.
function RemoveOldInstall(const UninstallKey, OldDir, UserAppData, StartMenuDir, DesktopLink: String): String;
var
  Removed: Integer;
begin
  Result := '';
  if (Trim(OldDir) <> '') and DirExists(OldDir) then
  begin
    if not IsOldProgramDir(OldDir, UserAppData) then
    begin
      Log('Stará inštalácia je v nečakanom priečinku, nemaže sa: ' + OldDir);
      Result := 'Staršia verzia Moje kocky je v priečinku ' + OldDir + ', ktorý inštalátor sám nezmaže.' + #13#10 +
        'Odinštaluj ju v Nastaveniach → Aplikácie (otázku, či zmazať aj údaje, zamietni; zbierka ostane) a spusti inštaláciu znova.';
      Exit;
    end;
    Removed := RemoveOldProgramDir(OldDir, UserAppData);
    if Removed = OldDirLeftovers then
    begin
      Result := 'Priečinok staršej verzie ' + OldDir + ' sa nepodarilo celý zmazať, niečo v ňom ešte používa iný program.' + #13#10 +
        'Zavri programy, ktoré ho môžu používať (aj okno Prieskumníka alebo príkazového riadka v ňom), a spusti inštaláciu znova.';
      Exit;
    end;
    if Removed <> OldDirGone then
    begin
      Result := 'Zavri Moje kocky a spusti inštaláciu znova.' + #13#10 +
        'Staršia verzia z priečinka ' + OldDir + ' je ešte otvorená.';
      Exit;
    end;
    Log('Stará inštalácia odstránená: ' + OldDir);
  end;
  if RegKeyExists(HKCU, UninstallKey) then
    RegDeleteKeyIncludingSubkeys(HKCU, UninstallKey);
  DeleteOldShortcuts(StartMenuDir, DesktopLink);
end;
