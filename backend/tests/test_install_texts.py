"""Desktop: texty pre používateľa hovoria o inštalácii pravdu.

Od 1.0.0 si inštalátor vypýta práva správcu a program ide do Program Files
pre všetkých (``test_installer.py``). README a texty vydania na GitHube to
musia povedať a nesmú sľubovať inštaláciu bez práv správcu. Text vydania
nesie aj férové upozornenie: bez záruk, zálohovať, ceny sú odhady.
"""

import re

from tests.test_desktop_version import ROOT

README = ROOT / "README.md"
RELEASE_NOTES = sorted((ROOT / "docs" / "release-notes").glob("*.md"))
USER_TEXTS = [README, *RELEASE_NOTES]


def _text(path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_appdata_paths_keep_their_backslashes():
    """Cesty v README a textoch vydania majú spätné lomky, inak ich nikto nenájde.

    Pri úprave sa ľahko stratia: z ``%APPDATA%\\MojeKocky\\session.bin``
    ostalo ``%APPDATA%MojeKockysession.bin``.
    """
    broken = re.compile(
        r"%(?:LOCAL)?APPDATA%[A-Za-z]|MojeKocky(?:session|backups|webview|photos|logs|secret)"
    )
    for path in USER_TEXTS:
        text = path.read_text(encoding="utf-8")

        assert not broken.findall(text), path


def test_readme_names_the_remembered_login_file_in_both_languages():
    parts = README.read_text(encoding="utf-8").split("# Moje kocky Desktop (English)", 1)
    assert len(parts) == 2

    for part in parts:
        assert r"`%APPDATA%\MojeKocky\session.bin`" in part


def test_texts_say_the_installer_asks_for_administrator():
    """README a texty vydania nesľubujú inštaláciu bez práv správcu."""
    assert len(RELEASE_NOTES) >= 2
    for path in USER_TEXTS:
        text = _text(path)
        lowered = text.lower()

        for promise in (
            "práva správcu netreba",
            "len pre teba",
            "no admin rights",
            "no administrator rights",
            "just for you",
            "for your user only",
        ):
            assert promise not in lowered, (path, promise)
        assert "práva správcu" in text, path
        assert "administrator rights" in text, path
        assert "Program Files" in text, path
        assert r"%APPDATA%\MojeKocky" in text, path


def test_release_notes_carry_the_fair_warning():
    """Prvé oficiálne vydanie a každé ďalšie: bez záruk, zálohovať, ceny sú odhady."""
    for path in RELEASE_NOTES:
        text = _text(path)

        for needed in (
            "MIT",
            "„tak, ako je“",
            '"as is"',
            "BrickEconomy",
            "LEGO Group",
            r"%APPDATA%\MojeKocky",
            "investičné poradenstvo",
            "investment advice",
            "https://github.com/jakubmatisak/moje-kocky-desktop/issues",
        ):
            assert needed in text, (path, needed)


def test_privacy_version_covers_uninstall_under_another_account():
    """Zásady desktopu od 2026-09-30.3 hovoria, čo odinštalovanie s heslom iného správcu urobí.

    Text zásad desktopu je vlastný (PrivacyView, desktopové sekcie), preto
    verzia môže byť vyššia než na webe. Pri prenose config.py z webu sa
    nesmie znížiť, inak by používatelia oznámenie o zmene nevideli.
    """
    from lego_api.config import Settings

    assert Settings().privacy_version >= "2026-09-30.3"


def test_privacy_version_covers_remembered_login_in_window_storage():
    """Od 2026-09-30.5 zásady desktopu netvrdia, že appka cookies nepoužíva.

    Prihlasovacie cookie drží most a zapamätané ukladá do session.bin; tabuľka
    úložiska ho uvádza. Po zmene textu musia používatelia vidieť oznámenie.
    """
    from lego_api.config import Settings

    assert Settings().privacy_version >= "2026-09-30.5"


def test_texts_do_not_say_the_installer_speaks_only_slovak():
    """Od 1.0.1 má inštalátor, odinštalovanie aj okno pri páde štartu obidva jazyky.

    Texty starších vydaní (v1.0.0) ostávajú, ako boli: vtedy to pravda bola.
    """
    for path in (README, ROOT / "docs" / "release-notes" / "default.md"):
        text = _text(path)

        assert "(in Slovak" not in text, path
        assert "is in Slovak)" not in text, path
