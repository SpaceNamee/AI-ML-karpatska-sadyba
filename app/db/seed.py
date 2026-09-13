"""One-off seed of real property data, transcribed from `docs/about.md`.

Run with:  uv run python -m app.db.seed

Idempotent: does nothing if any cottage already exists, so re-running it after
`docker compose up` never duplicates or wipes data.
"""

import asyncio

from sqlalchemy import func, select

from app.db.models.bedroom import Bedroom
from app.db.models.cottage import Amenity, AmenityCategory, Cottage, CottageView
from app.db.session import SessionFactory


def _amenity(slug: str, name: str, category: AmenityCategory) -> Amenity:
    return Amenity(slug=slug, name=name, category=category, is_free=True)


def _build_amenities() -> dict[str, Amenity]:
    # Built once, then referenced by key so a shared amenity (e.g. "wifi" on all
    # three cottages, "terrace" on two of them) is a single row linked several
    # times in `cottage_amenities` — not several rows racing the unique slug.
    return {
        "wifi": _amenity("wifi", "Wi-Fi на всій території", AmenityCategory.COMFORT),
        "parking": _amenity("parking", "Приватна парковка", AmenityCategory.OUTDOOR),
        "pool": _amenity("pool", "Басейн з підігрівом", AmenityCategory.OUTDOOR),
        "bbq_area": _amenity("bbq-area", "Мангал / барбекю", AmenityCategory.OUTDOOR),
        "playground": _amenity("playground", "Дитячий майданчик", AmenityCategory.OUTDOOR),
        "sports_field": _amenity("sports-field", "Спортивне поле", AmenityCategory.OUTDOOR),
        "kitchen": _amenity(
            "kitchen-equipped", "Повністю обладнана кухня", AmenityCategory.KITCHEN
        ),
        "washer": _amenity("washing-machine", "Пральна машина", AmenityCategory.COMFORT),
        "tv": _amenity("satellite-tv", "Супутникове ТБ", AmenityCategory.COMFORT),
        "co_detector": _amenity("co-detector", "Датчик чадного газу", AmenityCategory.SAFETY),
        "fireplace": _amenity("fireplace", "Камін", AmenityCategory.COMFORT),
        "underfloor_heating": _amenity(
            "underfloor-heating", "Підлога з підігрівом", AmenityCategory.COMFORT
        ),
        "private_gazebo": _amenity("private-gazebo", "Власна альтанка", AmenityCategory.OUTDOOR),
        "terrace": _amenity("terrace", "Тераса з видом на гори", AmenityCategory.OUTDOOR),
        "wardrobe": _amenity("wardrobe", "Шафа / гардероб", AmenityCategory.COMFORT),
        "balcony": _amenity("balcony", "Балкон з видом на гори", AmenityCategory.OUTDOOR),
    }


def _build_cottages(a: dict[str, Amenity]) -> list[Cottage]:
    common = [
        a["wifi"],
        a["parking"],
        a["pool"],
        a["bbq_area"],
        a["playground"],
        a["sports_field"],
        a["kitchen"],
        a["washer"],
        a["tv"],
        a["co_detector"],
    ]

    cottage_1 = Cottage(
        slug="cottage-1",
        name="Котедж 1",
        area_sqm=260,
        max_guests=16,
        base_guests=10,
        bathrooms=3,
        view=CottageView.MOUNTAINS,
        description=(
            "На першому поверсі двомісна та чотиримісна кімнати, великий зал з "
            "каміном, кухня та два санвузли (один з душем). На другому поверсі "
            "дві двомісні та дві трьомісні кімнати, кухня, санвузол з душем + "
            "балкон з кухні. Велика альтанка, що належить тільки цьому котеджу."
        ),
        bedrooms=[
            Bedroom(position=1, label="Спальня 1", double_beds=1),
            Bedroom(position=2, label="Спальня 2", sofa_beds=2),
            Bedroom(position=3, label="Спальня 3", double_beds=1),
            Bedroom(position=4, label="Спальня 4", double_beds=1),
            Bedroom(position=5, label="Спальня 5", single_beds=2),
            Bedroom(position=6, label="Спальня 6", single_beds=1, sofa_beds=1),
            Bedroom(position=7, label="Вітальня", is_living_room=True, sofa_beds=1),
        ],
        amenities=[
            *common,
            a["fireplace"],
            a["underfloor_heating"],
            a["private_gazebo"],
        ],
    )

    cottage_2 = Cottage(
        slug="cottage-2",
        name="Котедж 2",
        area_sqm=260,
        max_guests=18,
        base_guests=14,
        bathrooms=4,
        view=CottageView.POOL_AND_MOUNTAINS,
        description=(
            "На першому поверсі три двомісні кімнати, кухня, два санвузли (один "
            "з душем). На другому поверсі дві двомісні та дві чотиримісні "
            "кімнати, два санвузли (один з душем), кухня. Прибудинкова альтанка."
        ),
        bedrooms=[
            Bedroom(position=1, label="Спальня 1", double_beds=1),
            Bedroom(position=2, label="Спальня 2", double_beds=1),
            Bedroom(position=3, label="Спальня 3", double_beds=1),
            Bedroom(position=4, label="Спальня 4", double_beds=1, sofa_beds=1),
            Bedroom(position=5, label="Спальня 5", double_beds=1, sofa_beds=1),
            Bedroom(position=6, label="Спальня 6", double_beds=1),
            Bedroom(position=7, label="Спальня 7", double_beds=1),
        ],
        amenities=[*common, a["terrace"], a["wardrobe"]],
    )

    cottage_3 = Cottage(
        slug="cottage-3",
        name="Котедж 3",
        area_sqm=120,
        max_guests=15,
        base_guests=14,
        bathrooms=4,
        view=CottageView.MOUNTAINS,
        description=(
            "1-й поверх: кухня, два санвузли, дві двомісні кімнати та двомісна "
            "кімната з додатковим розкладним кріслом. 2-й поверх: дві двомісні "
            "кімнати з додатковими диванами, санвузли у кожній кімнаті."
        ),
        bedrooms=[
            Bedroom(position=1, label="Спальня 1", double_beds=1),
            Bedroom(position=2, label="Спальня 2", double_beds=1),
            Bedroom(position=3, label="Спальня 3", single_beds=1, double_beds=1),
            Bedroom(position=4, label="Спальня 4", double_beds=1, sofa_beds=1),
            Bedroom(position=5, label="Спальня 5", double_beds=1, sofa_beds=1),
        ],
        amenities=[*common, a["terrace"], a["balcony"]],
    )

    return [cottage_1, cottage_2, cottage_3]


async def seed() -> None:
    async with SessionFactory() as session:
        existing = await session.scalar(select(func.count()).select_from(Cottage))
        if existing:
            print(f"Already seeded ({existing} cottages) — nothing to do.")
            return

        amenities = _build_amenities()
        session.add_all(_build_cottages(amenities))
        await session.commit()
        print("Seeded 3 cottages.")


if __name__ == "__main__":
    asyncio.run(seed())
