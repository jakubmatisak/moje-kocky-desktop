"""Kúpený set vypadne z Chcem, nech sa pridal odkiaľkoľvek.

Pravidlo je na serveri pri každom pridaní kusu (`POST /items`, `/items/bulk`
aj import), nie v jednom dialógu. Odpoveď nesie pôvodnú položku Chcem, aby
sa dala tlačidlom Späť vrátiť aj s cieľovou cenou, poznámkou a dátumom.
"""

from httpx import AsyncClient

from lego_api.models import CatalogItem, CatalogKind, CollectionItem, ItemStatus
from lego_api.services.wishlist import drop_bought


async def _seed(session) -> None:
    session.add(CatalogItem(catalog_num="10294-1", name="Titanic", kind=CatalogKind.SET))
    session.add(CatalogItem(catalog_num="21318-1", name="Tree House", kind=CatalogKind.SET))
    session.add(
        CatalogItem(
            catalog_num="71046",
            name="Series 26 Minifigures",
            kind=CatalogKind.SET,
            theme="Series 26 Minifigures",
            series_size=12,
        )
    )
    for index in (1, 3, 7):
        session.add(
            CatalogItem(
                catalog_num=f"71046-{index}",
                name=f"Figúrka {index}",
                kind=CatalogKind.MINIFIG,
                parent_num="71046",
                theme="Series 26 Minifigures",
            )
        )
    await session.commit()


async def _wish(client: AsyncClient, num: str, **extra) -> dict:
    """Pridá do Chcem a vráti položku tak, ako ju vracia zoznam (uložený dátum)."""
    response = await client.post("/wishlist", json={"catalog_num": num, **extra})
    assert response.status_code == 201, response.text
    rows = (await client.get("/wishlist")).json()
    return next(r for r in rows if r["catalog_num"] == num)


async def _wished(client: AsyncClient, **kwargs) -> set[str]:
    response = await client.get("/wishlist", **kwargs)
    assert response.status_code == 200, response.text
    return {w["catalog_num"] for w in response.json()}


async def _add(client: AsyncClient, num: str, **extra) -> list[dict]:
    response = await client.post("/items", json={"catalog_num": num, **extra})
    assert response.status_code == 201, response.text
    return response.json()


async def test_added_piece_leaves_wishlist_and_answer_carries_the_wish(
    auth_client: AsyncClient, session
) -> None:
    """Pridať set (číslom aj skenom) je POST /items: set z Chcem zmizne."""
    await _seed(session)
    wish = await _wish(auth_client, "10294-1", target_price_eur="450", note="Na Vianoce")
    await _wish(auth_client, "21318-1")

    first, second = await _add(auth_client, "10294-1", quantity=2)

    assert await _wished(auth_client) == {"21318-1"}
    # Dva kusy naraz vyradili jednu položku, raz: nesie ju prvý kus.
    assert first["removed_from_wishlist"] == {
        "catalog_num": "10294-1",
        "name": "Titanic",
        "target_price_eur": "450.00",
        "note": "Na Vianoce",
        "created_at": wish["created_at"],
    }
    assert second["removed_from_wishlist"] is None


async def test_piece_without_wish_says_nothing(auth_client: AsyncClient, session) -> None:
    await _seed(session)
    await _wish(auth_client, "21318-1")

    [item] = await _add(auth_client, "10294-1")

    assert item["removed_from_wishlist"] is None
    assert await _wished(auth_client) == {"21318-1"}


async def test_other_accounts_wishlist_stays(
    auth_client: AsyncClient, client: AsyncClient, session
) -> None:
    await _seed(session)
    await _wish(auth_client, "10294-1")
    other = await client.post(
        "/auth/register",
        json={"email": "druhy@example.com", "password": "druhe-heslo-123", "accept_privacy": True},
    )
    theirs = {"Authorization": f"Bearer {other.json()['access_token']}"}
    response = await client.post("/wishlist", json={"catalog_num": "10294-1"}, headers=theirs)
    assert response.status_code == 201, response.text

    # Kúpil druhý účet: môj Chcem sa nemení.
    response = await client.post("/items", json={"catalog_num": "10294-1"}, headers=theirs)
    assert response.status_code == 201, response.text
    assert response.json()[0]["removed_from_wishlist"]["catalog_num"] == "10294-1"
    assert await _wished(client, headers=theirs) == set()
    assert await _wished(auth_client) == {"10294-1"}


async def test_series_figure_leaves_only_itself(auth_client: AsyncClient, session) -> None:
    """Figúrka zo série vyradí seba; sáčok pod holým číslom vyradí sériu."""
    await _seed(session)
    await _wish(auth_client, "71046-3")
    await _wish(auth_client, "71046-1")
    await _wish(auth_client, "71046")

    [figure] = await _add(auth_client, "71046-3")
    assert figure["removed_from_wishlist"]["catalog_num"] == "71046-3"
    assert await _wished(auth_client) == {"71046-1", "71046"}

    [bag] = await _add(auth_client, "71046")
    assert (bag["catalog_num"], bag["unidentified"]) == ("71046", True)
    assert bag["removed_from_wishlist"]["catalog_num"] == "71046"
    assert await _wished(auth_client) == {"71046-1"}


async def test_whole_series_at_once_drops_each_figure_once(
    auth_client: AsyncClient, session
) -> None:
    """„Mám všetky“ a séria v Pridať set idú cez /items/bulk, pravidlo platí aj tam."""
    await _seed(session)
    await _wish(auth_client, "71046-1", target_price_eur="4")
    await _wish(auth_client, "71046-3")
    await _wish(auth_client, "21318-1")

    response = await auth_client.post(
        "/items/bulk",
        json={
            "members": [
                {"catalog_num": "71046-1", "quantity": 2},
                {"catalog_num": "71046-3", "quantity": 1},
                {"catalog_num": "71046-7", "quantity": 1},
            ],
            "price_variant": "sealed",
        },
    )
    assert response.status_code == 201, response.text

    assert await _wished(auth_client) == {"21318-1"}
    carried = [
        (item["catalog_num"], (item["removed_from_wishlist"] or {}).get("target_price_eur", "-"))
        for item in response.json()
    ]
    assert carried == [
        ("71046-1", "4.00"),
        ("71046-1", "-"),
        ("71046-3", None),
        ("71046-7", "-"),
    ]


async def test_wish_comes_back_with_its_original_data(auth_client: AsyncClient, session) -> None:
    """Späť v oznámení: POST /wishlist s tým, čo prišlo v odpovedi, aj s dátumom."""
    await _seed(session)
    wish = await _wish(auth_client, "10294-1", target_price_eur="450", note="Na Vianoce")
    later = await _wish(auth_client, "21318-1")
    [item] = await _add(auth_client, "10294-1")
    removed = item["removed_from_wishlist"]

    response = await auth_client.post(
        "/wishlist",
        json={
            "catalog_num": removed["catalog_num"],
            "target_price_eur": removed["target_price_eur"],
            "note": removed["note"],
            "created_at": removed["created_at"],
        },
    )
    assert response.status_code == 201, response.text

    rows = (await auth_client.get("/wishlist", params={"sort": "added"})).json()
    back = next(r for r in rows if r["catalog_num"] == "10294-1")
    assert (back["target_price_eur"], back["note"], back["created_at"]) == (
        "450.00",
        "Na Vianoce",
        wish["created_at"],
    )
    # Pôvodný dátum: medzi Chcem ostane na svojom mieste, nie navrchu.
    assert [r["catalog_num"] for r in rows] == [later["catalog_num"], "10294-1"]


async def test_sold_piece_keeps_the_wish(auth_client: AsyncClient, session) -> None:
    """Dodatočne zapísaný predaj neznamená, že set už nechcem; rezervovaný kus ešte mám."""
    await _seed(session)
    await _wish(auth_client, "10294-1")
    await _wish(auth_client, "21318-1")
    me = (await auth_client.get("/auth/me")).json()

    sold = CollectionItem(user_id=me["id"], catalog_num="10294-1", status=ItemStatus.SOLD)
    reserved = CollectionItem(user_id=me["id"], catalog_num="21318-1", status=ItemStatus.RESERVED)
    dropped = await drop_bought(session, me["id"], [sold, reserved])
    await session.commit()

    assert set(dropped) == {"21318-1"}
    assert await _wished(auth_client) == {"10294-1"}


async def test_selling_later_does_not_touch_the_wishlist(auth_client: AsyncClient, session) -> None:
    """Predaj existujúceho kusu nie je pridanie; Chcem, kam set medzitým pribudol, ostane."""
    await _seed(session)
    [item] = await _add(auth_client, "10294-1")
    await _wish(auth_client, "10294-1")

    response = await auth_client.post(
        f"/items/{item['id']}/sell", json={"sold_price_eur": "700", "sold_date": "2026-09-01"}
    )
    assert response.status_code == 200, response.text
    assert await _wished(auth_client) == {"10294-1"}
