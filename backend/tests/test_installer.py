"""Desktop: inštalátor pre všetkých používateľov a prechod zo starej inštalácie.

Od 1.0.0 si inštalátor vypýta práva správcu a program ide do Program Files
pre všetkých; údaje má každý používateľ vo vlastnom ``%APPDATA%\\MojeKocky``.
Staršie verzie (0.1.x) boli len pre jedného používateľa
v ``%LOCALAPPDATA%\\Programs\\MojeKocky``. Inštalátor ich odstráni sám, bez
starého odinštalátora (ten sa pýta, či zmazať aj údaje), a údajov sa nedotkne.

Odinštalovanie sa pýta len na údaje účtu, pod ktorým beží, a keď to nie je
ten, kto sedí pri počítači (heslo iného správcu), nemaže nič.

Logiku v Pascale (``packaging/old-install.iss``, ``packaging/uninstall-data.iss``)
skúša malý testovací inštalátor: v ``InitializeSetup`` zavolá funkcie
s cestami v dočasnom priečinku, zapíše výsledok a skončí, takže nič
neinštaluje. Skutočný kľúč v registri ani skutočné priečinky používateľa
test nepozná.
"""

import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

from tests.test_desktop_version import ROOT, _iscc

PACKAGING = ROOT / "packaging"
ISS = PACKAGING / "moje-kocky.iss"
OLD_INSTALL = PACKAGING / "old-install.iss"
UNINSTALL_DATA = PACKAGING / "uninstall-data.iss"
INCLUDES = (OLD_INSTALL, UNINSTALL_DATA)
APP_ID = "{6C1B7E2A-5D43-4F7B-9B8E-4A2D6F0C9E11}"
RUNNING = "Zavri Moje kocky a spusti inštaláciu znova."
LEFTOVERS = "sa nepodarilo celý zmazať"

needs_iscc = pytest.mark.skipif(
    sys.platform != "win32" or _iscc() is None,
    reason="Inno Setup (ISCC.exe) nie je nainštalovaný",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _sections(text: str) -> dict[str, list[str]]:
    """Riadky skriptu podľa sekcií, bez komentárov a prázdnych riadkov."""
    sections: dict[str, list[str]] = {}
    current = ""
    for raw in text.splitlines():
        line = raw.strip()
        header = re.fullmatch(r"\[(\w+)\]", line)
        if header:
            current = header.group(1)
            sections.setdefault(current, [])
        elif line and not line.startswith(";"):
            sections.setdefault(current, []).append(line)
    return sections


def _setup() -> dict[str, str]:
    lines = _sections(_text(ISS))["Setup"]
    return dict(line.split("=", 1) for line in lines)


def _code() -> str:
    """[Code] hlavného skriptu v jednom riadku (medzery zjednotené)."""
    code = _text(ISS).split("[Code]", 1)[1]
    return " ".join(code.split())


# --- skript: pre všetkých, s právami správcu ------------------------------------


def test_installer_asks_for_administrator():
    """Windows ukáže otázku UAC; inštalácia len pre seba sa vybrať nedá."""
    setup = _setup()

    assert setup["PrivilegesRequired"] == "admin"
    assert "PrivilegesRequiredOverridesAllowed" not in setup


def test_installs_into_program_files_under_the_same_app_id():
    setup = _setup()

    assert setup["DefaultDirName"] == r"{autopf}\MojeKocky"
    # {autopf} je 64-bitové Program Files, len keď inštalátor beží v 64-bitovom režime.
    assert setup["ArchitecturesInstallIn64BitMode"] == "x64compatible"
    # To isté AppId: Windows aj Inno Setup berú novú verziu ako aktualizáciu.
    assert setup["AppId"] == "{" + APP_ID
    assert setup["DefaultGroupName"] == "Moje kocky"
    assert setup["UninstallDisplayIcon"] == r"{app}\MojeKocky.exe"


def test_shortcuts_are_for_every_user():
    icons = _sections(_text(ISS))["Icons"]
    names = [re.match(r'Name: "([^"]+)"', line).group(1) for line in icons]

    assert names, icons
    assert all(name.startswith(("{group}\\", "{autodesktop}\\")) for name in names), names
    assert r"{autodesktop}\Moje kocky" in names


def test_installer_sections_do_not_touch_user_areas():
    """Inštalácia pre všetkých nemá čo robiť v profile toho, kto ju spustil.

    Údaje v %APPDATA% si appka zakladá sama. Profil používateľa berie len
    [Code] pri odstránení starej inštalácie a pri odinštalovaní.
    """
    sections = _sections(_text(ISS))
    lines = [line for name, body in sections.items() if name != "Code" for line in body]

    assert not [line for line in lines if "{user" in line or "HKCU" in line]


def test_program_started_after_install_runs_as_the_user():
    """Po inštalácii sa appka spustí pod účtom, ktorý inštalátor otvoril, nie ako správca.

    Inak by si údaje založila v %APPDATA% účtu správcu.
    """
    (run,) = _sections(_text(ISS))["Run"]

    assert "postinstall" in run
    assert "runasoriginaluser" in run
    assert "runascurrentuser" not in run


def test_scripts_are_utf8_with_bom():
    """Bez BOM by Inno Setup čítal diakritiku v hláškach zle."""
    for path in (ISS, *INCLUDES):
        assert path.read_bytes().startswith(b"\xef\xbb\xbf"), path


def test_webview2_page_opens_as_the_original_user():
    """Stránka Microsoftu sa otvorí v prehliadači toho, kto inštalátor spustil.

    Setup beží so zvýšenými právami, pri hesle iného správcu pod jeho účtom.
    Obyčajný ShellExec by spustil prehliadač ako správca, s jeho profilom
    a jeho priečinkom Stiahnuté.
    """
    code = _code()

    assert (
        "ShellExecAsOriginalUser('open', 'https://developer.microsoft.com/microsoft-edge/webview2/',"
        in code
    )
    assert not re.search(r"\bShellExec\(", code)


# --- skript: prechod zo starej inštalácie a odinštalovanie ----------------------


def test_old_install_key_belongs_to_the_same_app_id():
    key = re.search(r"OldUninstallKey\s*=\s*'([^']+)'", _text(OLD_INSTALL)).group(1)

    assert key == rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_ID}_is1"


def test_prepare_to_install_removes_the_old_install_of_this_user():
    code = _code()
    included = re.search(r'#include "([^"]+)"', _text(ISS).split("[Code]", 1)[1]).group(1)

    assert included == OLD_INSTALL.name
    assert "function PrepareToInstall(var NeedsRestart: Boolean): String;" in code
    assert (
        "FindOldInstall(OldUninstallKey, ExpandConstant('{localappdata}\\Programs\\MojeKocky'),"
        " ExpandConstant('{app}'), OldDir)" in code
    )
    assert (
        "RemoveOldInstall(OldUninstallKey, OldDir, ExpandConstant('{userappdata}'),"
        " ExpandConstant('{userprograms}\\Moje kocky'),"
        " ExpandConstant('{userdesktop}\\Moje kocky.lnk'))" in code
    )


def test_uninstall_asks_before_deleting_data_and_defaults_to_no():
    code = _code()
    included = re.findall(r'#include "([^"]+)"', _text(ISS).split("[Code]", 1)[1])
    uninstall = code.split("procedure CurUninstallStepChanged", 1)[1]

    assert UNINSTALL_DATA.name in included
    assert "usPostUninstall" in uninstall
    assert "DataDir := ExpandConstant('{userappdata}\\MojeKocky');" in uninstall
    # Druhé tlačidlo (Nie) je predvolené, v tichom režime s /SUPPRESSMSGBOXES tiež Nie.
    assert (
        "SuppressibleMsgBox(DeleteDataQuestion(RunAs, DataDir), mbConfirmation,"
        " MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES" in uninstall
    )
    assert re.findall(r"DelTree\((\w+)", uninstall) == ["DataDir"]
    assert "tvoje údaje" not in code


def test_uninstall_elevated_by_another_account_does_not_ask():
    """Na bežnom účte s heslom iného správcu je {userappdata} profil toho správcu.

    Otázka by sa týkala cudzej zbierky, preto sa nekladie a nič sa nemaže;
    hláška povie, kde ostali údaje toho, kto sedí pri počítači.
    """
    uninstall = _code().split("procedure CurUninstallStepChanged", 1)[1]

    assert "RunAs := GetUserNameString;" in uninstall
    assert "SessionUser := SessionUserName();" in uninstall
    elevated = uninstall.index("if OtherAccountElevated(RunAs, SessionUser) then")
    notice = uninstall.index(
        "SuppressibleMsgBox(OtherAccountNotice(RunAs, SessionUser), mbInformation, MB_OK, IDOK);"
    )
    asked = uninstall.index("else if DirExists(DataDir) then")
    assert elevated < notice < asked < uninstall.index("DelTree(")


# --- kompilácia celého skriptu ------------------------------------------------------


@needs_iscc
def test_full_installer_script_compiles(tmp_path):
    """Celý skript (aj [Code] a include) prejde cez ISCC bez chýb a varovaní.

    Program a licencie nahradia malé súbory v rovnakom rozložení ako
    po PyInstaller, skript sa kompiluje z kópie priečinka packaging.
    """
    packaging = tmp_path / "packaging"
    packaging.mkdir()
    for name in ("moje-kocky.iss", "old-install.iss", "uninstall-data.iss", "icon.ico"):
        shutil.copy2(PACKAGING / name, packaging / name)
    shutil.copy2(ROOT / "LICENSE", tmp_path / "LICENSE")
    program = tmp_path / "build" / "dist" / "MojeKocky"
    program.mkdir(parents=True)
    (program / "MojeKocky.exe").write_bytes(b"MZ")
    (tmp_path / "build" / "THIRD-PARTY-NOTICES.txt").write_text("x", encoding="utf-8")

    result = subprocess.run(
        [
            str(_iscc()),
            f"/O{tmp_path / 'out'}",
            "/FMojeKocky-Setup-test",
            str(packaging / ISS.name),
        ],
        capture_output=True,
        timeout=300,
    )
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")

    assert result.returncode == 0, output
    assert (tmp_path / "out" / "MojeKocky-Setup-test.exe").is_file()
    assert "Warning" not in output, output


# --- logika prechodu v testovacom inštalátore ------------------------------------

HARNESS = """[Setup]
AppName=Moje kocky test prechodu
AppVersion=1
CreateAppDir=no
Uninstallable=no
PrivilegesRequired=lowest
OutputDir={out}
OutputBaseFilename=harness

[Code]
#include "old-install.iss"
#include "uninstall-data.iss"

function Flag(Value: Boolean): String;
begin
  if Value then Result := '1' else Result := '0';
end;

// Vstup: prvý riadok scenár, ďalej jeho argumenty, posledný riadok bodka.
function InitializeSetup(): Boolean;
var
  Args, Output: TArrayOfString;
  Dir: String;
  I: Integer;
begin
  Result := False;
  if not LoadStringsFromFile(ExpandConstant('{{param:TIN}}'), Args) then Exit;
  if Args[0] = 'guard' then
  begin
    SetArrayLength(Output, (GetArrayLength(Args) - 2) div 2);
    for I := 0 to GetArrayLength(Output) - 1 do
      Output[I] := Flag(IsOldProgramDir(Args[1 + 2 * I], Args[2 + 2 * I]));
  end
  else if Args[0] = 'find' then
  begin
    SetArrayLength(Output, 2);
    Output[0] := Flag(FindOldInstall(Args[1], Args[2], Args[3], Dir));
    Output[1] := Dir;
  end
  else if Args[0] = 'migrate' then
  begin
    SetArrayLength(Output, 1);
    Output[0] := RemoveOldInstall(Args[1], Args[2], Args[3], Args[4], Args[5]);
  end
  else if Args[0] = 'session' then
  begin
    SetArrayLength(Output, 2);
    Output[0] := SessionUserName();
    Output[1] := GetUserNameString;
  end
  else if Args[0] = 'other' then
  begin
    SetArrayLength(Output, (GetArrayLength(Args) - 2) div 2);
    for I := 0 to GetArrayLength(Output) - 1 do
      Output[I] := Flag(OtherAccountElevated(Args[1 + 2 * I], Args[2 + 2 * I]));
  end
  else if Args[0] = 'question' then
  begin
    SetArrayLength(Output, 1);
    Output[0] := DeleteDataQuestion(Args[1], Args[2]);
  end
  else if Args[0] = 'notice' then
  begin
    SetArrayLength(Output, 1);
    Output[0] := OtherAccountNotice(Args[1], Args[2]);
  end;
  SaveStringsToUTF8File(ExpandConstant('{{param:TOUT}}'), Output, False);
end;
"""


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    """Skompilovaný testovací inštalátor; ``run(scenár, *argumenty)`` vráti jeho výstup."""
    if sys.platform != "win32" or _iscc() is None:
        pytest.skip("Inno Setup (ISCC.exe) nie je nainštalovaný")
    folder = tmp_path_factory.mktemp("harness")
    for include in INCLUDES:
        shutil.copy2(include, folder / include.name)
    script = folder / "harness.iss"
    script.write_text(HARNESS.format(out=folder), encoding="utf-8-sig")
    subprocess.run([str(_iscc()), "/Q", str(script)], capture_output=True, timeout=300, check=True)
    setup = folder / "harness.exe"
    runs = iter(range(1_000_000))

    def run(scenario: str, *args: str) -> str:
        n = next(runs)
        given, answer = folder / f"in-{n}.txt", folder / f"out-{n}.txt"
        given.write_text("\n".join([scenario, *args, "."]), encoding="utf-8-sig")
        subprocess.run(
            [
                str(setup),
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
                f"/TIN={given}",
                f"/TOUT={answer}",
            ],
            capture_output=True,
            timeout=120,
        )
        assert answer.is_file(), "testovací inštalátor nič nezapísal"
        return answer.read_text(encoding="utf-8-sig").rstrip("\r\n")

    return run


def _fake_key() -> str:
    """Kľúč v HKCU, ktorý neexistuje (skutočný kľúč starej inštalácie test nepozná)."""
    key = rf"Software\MojeKocky-test-{uuid.uuid4().hex}\neexistuje"
    assert APP_ID not in key
    return key


class Profile:
    """Profil používateľa v dočasnom priečinku, so starou inštaláciou a údajmi."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.appdata = root / "AppData" / "Roaming"
        self.program = root / "AppData" / "Local" / "Programs" / "MojeKocky"
        self.data = self.appdata / "MojeKocky"
        self.start_menu = self.appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        self.group = self.start_menu / "Moje kocky"
        self.desktop = root / "Desktop"
        self.desktop_link = self.desktop / "Moje kocky.lnk"

        (self.program / "_internal").mkdir(parents=True)
        for name in ("MojeKocky.exe", "unins000.exe", "unins000.dat", "LICENSE.txt"):
            (self.program / name).write_bytes(b"MZ")
        (self.program / "_internal" / "python313.dll").write_bytes(b"MZ")
        (self.data / "backups").mkdir(parents=True)
        (self.data / "lego.db").write_bytes(b"SQLite format 3\x00")
        (self.data / "secret.key").write_text("k" * 64, encoding="ascii")
        (self.data / "backups" / "lego-20260930-080000-v0.1.2-abc.db").write_bytes(b"x")
        self.group.mkdir(parents=True)
        for name in ("Moje kocky.lnk", "Odinštalovať Moje kocky.lnk", "Licencie.lnk"):
            (self.group / name).write_bytes(b"L")
        (self.start_menu / "Iný program.lnk").write_bytes(b"L")
        self.desktop.mkdir()
        self.desktop_link.write_bytes(b"L")
        (self.desktop / "Iný program.lnk").write_bytes(b"L")

    def files(self, folder: Path) -> set[str]:
        return {str(p.relative_to(folder)) for p in folder.rglob("*")}

    def migrate(self, run, old_dir: Path | str | None = None) -> str:
        return run(
            "migrate",
            _fake_key(),
            str(self.program if old_dir is None else old_dir),
            str(self.appdata),
            str(self.group),
            str(self.desktop_link),
        )


JANA = r"C:\Users\Jana\AppData"
JAN = r"C:\Users\Ján Š\AppData"
GUARD_CASES = [
    # (priečinok na zmazanie, %APPDATA%, smie sa zmazať)
    (JANA + r"\Local\Programs\MojeKocky", JANA + r"\Roaming", True),
    (JANA + r"\Local\Programs\MojeKocky" + "\\", JANA + r"\Roaming", True),
    (JANA.lower() + r"\local\programs\mojekocky", JANA + r"\Roaming", True),
    (JAN + r"\Local\Programs\MojeKocky", JAN + r"\Roaming", True),
    # Údaje, ich nadradený priečinok a čokoľvek pod %APPDATA% nikdy.
    (JANA + r"\Roaming\MojeKocky", JANA + r"\Roaming", False),
    (JANA + r"\Roaming", JANA + r"\Roaming", False),
    (JANA + r"\Roaming\Programs\MojeKocky", JANA + r"\Roaming", False),
    (JANA.lower() + r"\roaming\programs\mojekocky", JANA + r"\Roaming", False),
    (JAN + r"\Roaming\Programs\MojeKocky", JAN + r"\Roaming", False),
    (r"C:\X\Programs\MojeKocky", r"C:\X\Programs\MojeKocky\Roaming", False),
    # Iný priečinok než program starej verzie.
    (r"C:\Program Files\MojeKocky", JANA + r"\Roaming", False),
    (JANA + r"\Local\Programs\MojeKockyX", JANA + r"\Roaming", False),
    (r"D:\Hry\MojeKocky", JANA + r"\Roaming", False),
    (JANA + r"\Roaming\MojeKocky\..\Programs\MojeKocky", JANA + r"\Roaming", False),
    ((JANA + r"\Local\Programs\MojeKocky").replace("\\", "/"), JANA + r"\Roaming", False),
    (r"Programs\MojeKocky", JANA + r"\Roaming", False),
    ("", JANA + r"\Roaming", False),
    # Bez známeho %APPDATA% sa nemaže nič.
    (JANA + r"\Local\Programs\MojeKocky", "", False),
]


def test_guard_allows_only_the_old_program_folder(harness):
    args = [value for case in GUARD_CASES for value in case[:2]]

    answer = harness("guard", *args).splitlines()

    assert answer == ["1" if case[2] else "0" for case in GUARD_CASES]


def test_without_uninstall_key_the_default_folder_is_the_old_install(harness, tmp_path):
    profile = Profile(tmp_path)
    other_app = tmp_path / "Program Files" / "MojeKocky"

    assert harness("find", _fake_key(), str(profile.program), str(other_app)).splitlines() == [
        "1",
        str(profile.program),
    ]
    # Priečinok, do ktorého ide nová inštalácia, nie je stará inštalácia.
    assert harness("find", _fake_key(), str(profile.program), str(profile.program)) == "0"
    shutil.rmtree(profile.program)
    assert harness("find", _fake_key(), str(profile.program), str(other_app)) == "0"


def test_migration_removes_program_and_shortcuts_but_keeps_data(harness, tmp_path):
    profile = Profile(tmp_path)
    data = profile.files(profile.data)

    assert profile.migrate(harness) == ""

    assert not profile.program.exists()
    assert profile.program.parent.is_dir()
    assert not profile.group.exists()
    assert not profile.desktop_link.exists()
    assert (profile.start_menu / "Iný program.lnk").is_file()
    assert (profile.desktop / "Iný program.lnk").is_file()
    assert profile.files(profile.data) == data
    assert (profile.data / "lego.db").read_bytes() == b"SQLite format 3\x00"


def test_migration_keeps_start_menu_folder_with_foreign_files(harness, tmp_path):
    profile = Profile(tmp_path)
    (profile.group / "moja poznamka.txt").write_text("x", encoding="utf-8")

    assert profile.migrate(harness) == ""

    assert profile.files(profile.group) == {"moja poznamka.txt"}


@pytest.mark.skipif(sys.platform != "win32", reason="bežiaci program len vo Windows")
def test_migration_keeps_everything_while_the_old_program_runs(harness, tmp_path):
    """Bežiaci starý program sa nedá zmazať; inštalácia skončí skôr, než niečo zmaže."""
    profile = Profile(tmp_path)
    ping = Path(os.environ["SYSTEMROOT"]) / "System32" / "PING.EXE"
    shutil.copy2(ping, profile.program / "MojeKocky.exe")
    program = profile.files(profile.program)
    group = profile.files(profile.group)
    running = subprocess.Popen(
        [str(profile.program / "MojeKocky.exe"), "-n", "60", "127.0.0.1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.5)
        assert running.poll() is None

        answer = profile.migrate(harness)
    finally:
        running.kill()
        running.wait(timeout=30)

    assert RUNNING in answer
    assert profile.files(profile.program) == program
    assert profile.files(profile.group) == group
    assert profile.desktop_link.is_file()


def test_migration_refuses_a_folder_it_does_not_recognise(harness, tmp_path):
    """Starú verziu v inom priečinku inštalátor nemaže; povie, ako ju odinštalovať."""
    profile = Profile(tmp_path)
    custom = tmp_path / "Hry" / "MojeKocky"
    shutil.copytree(profile.program, custom)
    under_appdata = profile.appdata / "Programs" / "MojeKocky"
    shutil.copytree(profile.program, under_appdata)

    for folder in (custom, under_appdata, profile.data):
        before = profile.files(folder)

        answer = profile.migrate(harness, folder)

        assert str(folder) in answer
        assert "Odinštaluj" in answer
        assert profile.files(folder) == before
        assert profile.group.is_dir()
        assert profile.desktop_link.is_file()


def test_migration_without_program_folder_removes_shortcuts(harness, tmp_path):
    """Kľúč ostal, priečinok už nie: stačí upratať skratky."""
    profile = Profile(tmp_path)
    shutil.rmtree(profile.program)

    assert profile.migrate(harness, "") == ""

    assert not profile.group.exists()
    assert not profile.desktop_link.exists()
    assert (profile.data / "lego.db").is_file()


@pytest.mark.skipif(sys.platform != "win32", reason="zamknutý súbor len vo Windows")
def test_migration_reports_a_folder_it_could_not_delete_completely(harness, tmp_path):
    """Program nebeží, ale súbor v _internal drží iný proces (antivírus, konzola).

    DelTree zmaže, čo môže, a hláška to povie tak, ako to je: nie „je ešte
    otvorená“. Údaje ostanú, skratky tiež a opakovaná inštalácia mazanie
    dokončí.
    """
    profile = Profile(tmp_path)
    data = profile.files(profile.data)

    # open() v Pythone nepovoľuje zmazanie, kým je súbor otvorený.
    with open(profile.program / "_internal" / "python313.dll", "rb"):
        answer = profile.migrate(harness)

    assert LEFTOVERS in answer
    assert RUNNING not in answer
    assert str(profile.program) in answer
    assert profile.files(profile.data) == data
    assert profile.group.is_dir()
    assert profile.desktop_link.is_file()

    assert profile.migrate(harness) == ""
    assert not profile.program.exists()
    assert not profile.group.exists()
    assert profile.files(profile.data) == data


# --- odinštalovanie: čie údaje ---------------------------------------------------

OTHER_ACCOUNT_CASES = [
    # (účet, pod ktorým odinštalovanie beží, používateľ relácie, je to iný účet)
    ("Jana", "Jana", False),
    ("jana", "JANA", False),
    ("Rodič", "Dieťa", True),
    ("Administrator", "Jana", True),
    # Používateľa relácie sa nepodarilo zistiť: otázka s menom účtu.
    ("Administrator", "", False),
]


@pytest.mark.skipif(sys.platform != "win32", reason="relácia Windows len vo Windows")
def test_session_user_is_the_user_at_the_computer(harness):
    """Bez zvýšenia práv iným účtom je používateľ relácie ten, pod kým proces beží."""
    session, run_as = harness("session").splitlines()

    assert session
    assert session.lower() == run_as.lower() == os.environ["USERNAME"].lower()


def test_another_account_is_told_apart_from_the_user_at_the_computer(harness):
    args = [value for case in OTHER_ACCOUNT_CASES for value in case[:2]]

    answer = harness("other", *args).splitlines()

    assert answer == ["1" if case[2] else "0" for case in OTHER_ACCOUNT_CASES]


def test_uninstall_question_names_the_account_and_its_folder(harness):
    """Otázka nehovorí „tvoje“: povie, čí priečinok to je a že ostatní o nič neprídu."""
    folder = r"C:\Users\Ján Š\AppData\Roaming\MojeKocky"

    question = harness("question", "Ján Š", folder)

    assert "používateľa Windows „Ján Š“" in question
    assert folder in question
    assert "Údaje ostatných používateľov počítača ostanú." in question
    assert "tvoje" not in question.lower()


def test_uninstall_under_another_account_says_nothing_was_deleted(harness):
    notice = harness("notice", "Rodič", "Dieťa")

    assert "„Rodič“" in notice
    assert "„Dieťa“" in notice
    assert "nemazalo nikomu" in notice
    assert r"%APPDATA%\MojeKocky" in notice
