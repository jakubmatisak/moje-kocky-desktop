// Čie údaje sa pri odinštalovaní ponúknu na zmazanie.
//
// Program je pre všetkých, údaje má každý používateľ vlastné
// v %APPDATA%\MojeKocky. Odinštalovanie beží s právami správcu, teda pod
// účtom, ktorého heslo niekto zadal pri otázke UAC. Na vlastnom účte
// správcu je to ten, kto sedí pri počítači. Na bežnom účte s heslom iného
// správcu je to ten správca a {userappdata} je jeho profil: otázka by sa
// týkala cudzej zbierky (a DelTree by s ňou zmazal aj secret.key a zálohy),
// kým údaje toho, kto odinštaluje, by ostali bez otázky. Vtedy sa preto
// nemaže nič a hláška povie, kde údaje ostali.
//
// Kto sedí pri počítači, povie používateľ relácie Windows
// (WTSQuerySessionInformation, WTSUserName): zvýšenie práv reláciu nemení,
// účet procesu áno. Setup aj odinštalátor sú 32-bitové, ukazovateľ je
// preto Cardinal. Funkcie skúša tests/test_installer.py testovacím
// inštalátorom.
// Komentáre sú cez //, lebo komentár v zložených zátvorkách by skončil pri
// prvej konštante ako {app}.

const
  WTSUserName = 5;
  WTSCurrentSession = -1;

function WTSQuerySessionInformationW(Server: Cardinal; SessionId: Integer; InfoClass: Integer; var Buffer: Cardinal; var BytesReturned: Cardinal): Boolean;
  external 'WTSQuerySessionInformationW@wtsapi32.dll stdcall delayload';
procedure WTSFreeMemory(Memory: Cardinal);
  external 'WTSFreeMemory@wtsapi32.dll stdcall delayload';
function lstrlenW(Text: Cardinal): Integer;
  external 'lstrlenW@kernel32.dll stdcall';
function lstrcpynW(Target: String; Source: Cardinal; MaxLength: Integer): Cardinal;
  external 'lstrcpynW@kernel32.dll stdcall';

// Meno používateľa relácie Windows (ten, kto sedí pri počítači), alebo
// prázdny text, keď sa nedá zistiť.
function SessionUserName(): String;
var
  Buffer, Size: Cardinal;
  Len: Integer;
begin
  Result := '';
  Buffer := 0;
  Size := 0;
  try
    if WTSQuerySessionInformationW(0, WTSCurrentSession, WTSUserName, Buffer, Size) and (Buffer <> 0) then
    begin
      Len := lstrlenW(Buffer);
      if Len > 0 then
      begin
        SetLength(Result, Len);
        lstrcpynW(Result, Buffer, Len + 1);
      end;
      WTSFreeMemory(Buffer);
    end;
  except
    Log('Používateľa relácie Windows sa nepodarilo zistiť: ' + GetExceptionMessage);
    Result := '';
  end;
end;

// Beží odinštalovanie pod iným účtom, než je používateľ pri počítači?
// Keď sa používateľa relácie nepodarí zistiť, neráta sa to: otázka potom
// menuje účet, ktorého údaje by sa zmazali.
function OtherAccountElevated(const RunAs, SessionUser: String): Boolean;
begin
  Result := (Trim(SessionUser) <> '') and (CompareText(Trim(RunAs), Trim(SessionUser)) <> 0);
end;

function DeleteDataQuestion(const Account, DataDir: String): String;
begin
  Result := 'Zmazať aj údaje Moje kocky (zbierku, fotky, kľúče) používateľa Windows „' + Account + '“ v priečinku ' + DataDir + '?' + #13#10 +
    'Údaje ostatných používateľov počítača ostanú. Ak ich necháš, nová inštalácia ich znova použije.';
end;

function OtherAccountNotice(const RunAs, SessionUser: String): String;
begin
  Result := 'Odinštalovanie bežalo pod účtom správcu „' + RunAs + '“, nie pod tvojím („' + SessionUser + '“), preto údaje Moje kocky nemazalo nikomu.' + #13#10 +
    'Tvoje údaje (zbierka, fotky, kľúče) ostali v priečinku %APPDATA%\MojeKocky tvojho účtu. Keď ich už nechceš, zmaž ho sám; ak ho necháš, nová inštalácia ich znova použije.';
end;
