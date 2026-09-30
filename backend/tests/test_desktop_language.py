"""Desktop: okná so správou mimo okna appky hovoria jazykom Windows.

Keď appka nenabehne (alebo už beží), ukáže okno Windows so správou skôr,
než by poznala jazyk účtu: databáza nemusí ísť otvoriť. Jazyk preto berie
z jazyka rozhrania Windows, ako Inno Setup pri výbere jazyka inštalátora:
slovenské Windows po slovensky, ostatné po anglicky. Mimo Windows (a keď
Windows neodpovie) po slovensky.
"""

import sys

import pytest

from lego_desktop import main as desktop_main


@pytest.mark.parametrize(
    ("lang_id", "expected"),
    [
        (0x041B, "sk"),  # slovenčina (Slovensko)
        (0x0409, "en"),  # angličtina (USA)
        (0x0809, "en"),  # angličtina (Spojené kráľovstvo)
        (0x0405, "en"),  # čeština: appka po česky nevie
        (0x0407, "en"),  # nemčina
    ],
)
def test_ui_language_follows_windows(monkeypatch, lang_id, expected):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(desktop_main, "_windows_ui_language_id", lambda: lang_id)

    assert desktop_main.ui_language() == expected


def test_ui_language_is_slovak_when_windows_does_not_answer(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(desktop_main, "_windows_ui_language_id", lambda: None)

    assert desktop_main.ui_language() == "sk"


def test_ui_language_is_slovak_off_windows(monkeypatch):
    def not_asked() -> int:
        raise AssertionError("mimo Windows sa jazyk Windows nezisťuje")

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(desktop_main, "_windows_ui_language_id", not_asked)

    assert desktop_main.ui_language() == "sk"


@pytest.mark.skipif(sys.platform != "win32", reason="jazyk rozhrania len vo Windows")
def test_windows_answers_with_a_language_id():
    lang_id = desktop_main._windows_ui_language_id()

    assert isinstance(lang_id, int)
    assert lang_id > 0


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("sk", "Moje kocky už bežia. Pozri sa na panel úloh."),
        ("en", "Moje kocky is already running. Look for it on the taskbar."),
    ],
)
def test_already_running_message_follows_the_language(monkeypatch, language, expected):
    shown: list[str] = []
    monkeypatch.setattr(desktop_main, "_message_box", lambda text, flags: shown.append(text))
    monkeypatch.setattr(desktop_main, "ui_language", lambda: language)

    desktop_main._already_running()

    assert shown == [expected]
