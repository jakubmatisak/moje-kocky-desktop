"""Moje figúrky: kusy figúrok zo sérií s tými istými filtrami ako Zbierka.

Figúrky posielajú ``figures_only=true``, zrkadlo ``sets_only`` Zbierky:
figúrky zo sérií aj nerozbalené sáčky, žiadne samostatné sety.
"""

from httpx import AsyncClient

from tests.test_collection_sets_only import _seed

FIGURES = {"figures_only": "true"}


async def test_figures_section_lists_series_figures_and_bags(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    await _seed(auth_client, sessionmaker_)

    shown = (await auth_client.get("/items", params={"status": "all", **FIGURES})).json()

    assert sorted(i["catalog_num"] for i in shown) == ["42233-1", "71051", "71051-1", "71051-2"]


async def test_figures_section_totals_are_my_figures(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    """Riadok Kúpené · Hodnota · Zisk vo Figúrkach ráta len figúrky."""
    await _seed(auth_client, sessionmaker_)

    facets = (await auth_client.get("/items/facets", params={"status": "owned", **FIGURES})).json()

    totals = facets["totals"]
    assert totals["owned"] == 3
    assert totals["purchase"] == "12.00"
    # Sáčok pod holým číslom série cenu nemá, figúrky áno.
    assert totals["market_value"] == "18.00"
    assert facets["hidden_figures"] == 0


async def test_box_filter_finds_where_a_figure_is_stored(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    ids = await _seed(auth_client, sessionmaker_)
    moved = await auth_client.patch(
        f"/items/{ids['figure']}", json={"location": "Povala", "box": "krabica 3"}
    )
    assert moved.status_code == 200, moved.text

    shown = (
        await auth_client.get("/items", params={**FIGURES, "box": "Povala · krabica 3"})
    ).json()

    assert [i["id"] for i in shown] == [ids["figure"]]


async def test_figures_panel_offers_only_figure_themes(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    """Téma len so setmi (Icons) vo Figúrkach nie je, ako téma len s figúrkami v Zbierke."""
    await _seed(auth_client, sessionmaker_)

    facets = (await auth_client.get("/items/facets", params={"status": "all", **FIGURES})).json()

    themes = {o["value"] for o in facets["theme"]}
    assert "Icons" not in themes
    assert "Collectible Minifigures" in themes
