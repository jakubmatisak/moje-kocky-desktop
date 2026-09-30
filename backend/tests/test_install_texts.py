"""Desktop: texty pre používateľa hovoria o inštalácii pravdu.

Od 1.0.0 si inštalátor vypýta práva správcu a program ide do Program Files
pre všetkých (``test_installer.py``). README a texty vydania na GitHube to
musia povedať a nesmú sľubovať inštaláciu bez práv správcu. Text vydania
nesie aj férové upozornenie: bez záruk, zálohovať, ceny sú odhady.
"""

from tests.test_desktop_version import ROOT

RELEASE_NOTES = sorted((ROOT / "docs" / "release-notes").glob("*.md"))
USER_TEXTS = [ROOT / "README.md", *RELEASE_NOTES]


def _text(path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


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
