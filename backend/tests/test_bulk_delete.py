"""Hromadné zmazanie vlastných kusov (stránka série vo Figúrkach a detail série)."""

from httpx import AsyncClient

from tests.test_api_categories import _add
from tests.test_api_insights import JPEG, photos_dir  # noqa: F401 - fixtúra

SERIES = {"series": ["71046"]}


async def _series(sessionmaker_) -> None:
    from lego_api.models import CatalogItem, CatalogKind

    async with sessionmaker_() as session:
        session.add(
            CatalogItem(catalog_num="71046", name="Series 26", kind=CatalogKind.SET, series_size=2)
        )
        for i in (1, 2):
            session.add(
                CatalogItem(
                    catalog_num=f"71046-{i}",
                    name=f"Fig {i}",
                    kind=CatalogKind.SET,
                    parent_num="71046",
                )
            )
        session.add(CatalogItem(catalog_num="10294-1", name="Titanic", kind=CatalogKind.SET))
        await session.commit()


async def _nums(client: AsyncClient) -> list[str]:
    rows = (await client.get("/items", params={"status": "all"})).json()
    return sorted(r["catalog_num"] for r in rows)


async def test_dry_run_counts_and_deletes_nothing(auth_client: AsyncClient, sessionmaker_) -> None:
    await _series(sessionmaker_)
    for num in ("71046-1", "71046-1", "71046-2", "10294-1"):
        await _add(auth_client, num)

    response = await auth_client.post("/items/bulk-delete", params=SERIES, json={"dry_run": True})

    assert response.status_code == 200, response.text
    assert response.json() == {"items": 3, "sets": 2}
    assert len(await _nums(auth_client)) == 4


async def test_whole_series_goes_with_photos_and_other_sets_stay(
    auth_client: AsyncClient,
    sessionmaker_,
    photos_dir,  # noqa: F811
) -> None:
    await _series(sessionmaker_)
    fig = await _add(auth_client, "71046-1")
    await _add(auth_client, "71046-2")
    await _add(auth_client, "10294-1")
    uploaded = await auth_client.post(
        f"/items/{fig['id']}/photos", files={"file": ("f.jpg", JPEG, "image/jpeg")}
    )
    assert uploaded.status_code == 201
    assert list(photos_dir.iterdir())

    response = await auth_client.post("/items/bulk-delete", params=SERIES, json={})

    assert response.json() == {"items": 2, "sets": 2}
    assert await _nums(auth_client) == ["10294-1"]
    assert list(photos_dir.iterdir()) == []


async def test_only_chosen_pieces_and_never_sold_ones(
    auth_client: AsyncClient, sessionmaker_
) -> None:
    await _series(sessionmaker_)
    keep = await _add(auth_client, "71046-1")
    gone = await _add(auth_client, "71046-2")
    sold = await _add(auth_client, "71046-2")
    await auth_client.post(
        f"/items/{sold['id']}/sell", json={"sold_price_eur": "5", "sold_date": "2026-09-01"}
    )

    response = await auth_client.post(
        "/items/bulk-delete", params=SERIES, json={"catalog_nums": ["71046-2"]}
    )

    assert response.json() == {"items": 1, "sets": 1}
    rows = {r["id"] for r in (await auth_client.get("/items", params={"status": "all"})).json()}
    assert keep["id"] in rows and sold["id"] in rows and gone["id"] not in rows
