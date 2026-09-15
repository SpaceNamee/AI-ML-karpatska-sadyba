"""GET /cottages against a real Postgres row — proves the full
router -> service -> repository -> SQLAlchemy -> Postgres path, not just the
service layer against a fake (that's tests/unit/test_catalog_service.py).
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.bedroom import Bedroom
from app.db.models.cottage import Cottage, CottageView


async def test_list_cottages_includes_a_freshly_inserted_row(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    db_session.add(
        Cottage(
            slug="integration-cottage",
            name="Integration Test Cottage",
            area_sqm=150,
            max_guests=8,
            base_guests=4,
            bathrooms=2,
            view=CottageView.MOUNTAINS,
        )
    )
    await db_session.commit()

    response = await api_client.get("/api/v1/cottages")

    assert response.status_code == 200
    slugs = [cottage["slug"] for cottage in response.json()]
    assert "integration-cottage" in slugs


async def test_get_cottage_by_slug_returns_bedrooms_and_amenities_eager_loaded(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    db_session.add(
        Cottage(
            slug="integration-cottage-2",
            name="Another Cottage",
            area_sqm=90,
            max_guests=6,
            base_guests=3,
            bathrooms=1,
            view=CottageView.POOL_AND_MOUNTAINS,
            bedrooms=[Bedroom(position=1, label="Спальня 1", double_beds=1)],
        )
    )
    await db_session.commit()

    response = await api_client.get("/api/v1/cottages/integration-cottage-2")

    assert response.status_code == 200
    body = response.json()
    assert body["view"] == "pool_and_mountains"
    assert len(body["bedrooms"]) == 1
    assert body["amenities"] == []


async def test_get_cottage_by_unknown_slug_returns_404(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/cottages/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Cottage 'does-not-exist' not found"}
