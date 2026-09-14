"""Seed a small set of real FAQ documents into the knowledge base.

Run with:  uv run python -m app.db.seed_kb

This goes through KnowledgeBaseService.ingest_upload — the exact same path a
real admin upload takes — so it writes files under `settings.storage_dir` and
enqueues each document for the ARQ worker. **Run it wherever your worker also
reads files from**: on the host if you run the app/worker on the host, or via
`docker compose exec api uv run python -m app.db.seed_kb` if you use the
compose stack (so the file lands in the `uploads_data` volume the worker
shares, not just the api container's local disk).

Idempotent: does nothing if the knowledge base already has any document.
Content transcribed from docs/about.md, split by topic the way a host would
naturally upload it over time — one big FAQ blob would leave nothing for
retrieval ranking to actually discriminate between.
"""

import asyncio

from sqlalchemy import func, select

from app.core.config import settings
from app.db.models.kb import KbDocument
from app.db.session import SessionFactory
from app.jobs.queue import ArqIngestQueue
from app.repositories.document_repository import DocumentRepository
from app.services.knowledge_base_service import KnowledgeBaseService

_DOCUMENTS = [
    (
        "Правила проживання",
        "rules.txt",
        (
            "Заїзд можливий з 15:00, просимо попередити господаря про орієнтовний "
            "час заїзду. Виїзд — до 11:00. Тихі години діють з 00:00 до 05:00.\n\n"
            "Куріння заборонено в усіх котеджах — усі три будиночки для некурців. "
            "Діти дозволені будь-якого віку, але дитячі ліжечка господар не надає. "
            "Домашні тварини можливі за попереднім запитом, можлива додаткова "
            "плата за прибирання після тварин.\n\n"
            "Оплата готівкою на місці; передоплата банківським переказом "
            "обов'язкова. Бронювання підтверджується завдатком 3000 грн, після "
            "чого господар зв'язується для узгодження деталей заїзду."
        ),
    ),
    (
        "Зручності та платні послуги",
        "amenities.txt",
        (
            "На території садиби безкоштовно: підігрітий басейн з підсвіткою "
            "вночі (сезонно, працює влітку та на початку осені), приватна "
            "парковка без резервування, Wi-Fi на всій території, дитячий "
            "майданчик, спортивне поле зі своїм інвентарем, місце для пікніка, "
            "мангал з казаном і сковорідкою.\n\n"
            "За окрему плату: сауна і чан, риболовля на ставку на території "
            "(безкоштовно ловити, платно забрати спіймане), прокат квадроциклів, "
            "трансфер з/до вокзалу, дрова для мангалу, замовлення обідів у номер "
            "за попереднім дзвінком.\n\n"
            "Безпека: вогнегасники, відеоспостереження в зонах загального "
            "користування, вхід із ключем, цілодобова охорона, датчики чадного "
            "газу в кожному котеджі."
        ),
    ),
    (
        "Гірськолижні комплекси поблизу",
        "skiing.txt",
        (
            "Найближчий до нас — «Плай», приблизно 5 кілометрів від садиби. "
            "База розташована на висоті близько 600 метрів, підйомники "
            "піднімають до 1600 метрів. Шість спусків довжиною до 1200 метрів, "
            "є сині, червоні та чорні траси, а також навчальна зона. Працює "
            "спа-центр і заклади харчування, комплекс діє і взимку, і влітку.\n\n"
            "«Звенів» у селі Орявчик, приблизно 15–20 кілометрів — невеликий "
            "курорт, гарний варіант для родин і початківців, є окрема зона для "
            "сноутюбінгу.\n\n"
            "«Динамо-Тростян» у селі Славсько, приблизно 20 кілометрів — одна з "
            "найвідоміших баз Славська на горі Тростян, підходить впевненим "
            "лижникам завдяки довгим трасам.\n\n"
            "«Захар Беркут» у селі Волосянка, приблизно 25–30 кілометрів — "
            "сучасний комплекс із найдовшою в Україні двокрісельною канатною "
            "дорогою."
        ),
    ),
    (
        "Водоспади та визначні місця",
        "attractions.txt",
        (
            "У Сколівських Бескидах поблизу є кілька водоспадів. Кам'янка — "
            "найпопулярніший і найдоступніший, приблизно 40 кілометрів, до "
            "нього веде рівна дорога, тому добре підходить для відпочинку з "
            "дітьми. Гуркало на Великій Річці, приблизно 50 кілометрів. "
            "Крушельницький — невисокий, але мальовничий, дорога до нього "
            "гірша. Сопіт — найвищий із цієї четвірки, вода стрімко збігає "
            "скелею у простору чашу.\n\n"
            "Фортеця Тустань у селі Урич, приблизно 50 кілометрів — "
            "середньовічна наскельна фортеця-град, що захищала кордони "
            "Галицько-Волинського князівства. Одне із семи чудес України.\n\n"
            "Гора Парашка, приблизно 30 кілометрів — найвища вершина "
            "Сколівських Бескидів, 1268 метрів, з металевим хрестом на "
            "вершині.\n\n"
            "Контакти для бронювання: +38 098 773 31 03, +38 068 968 80 55, "
            "+38 098 904 33 32. Квадроцикли й трансфер: +38 068 101 45 45. "
            "Замовлення харчування: +38 097 052 36 78."
        ),
    ),
]


async def seed_kb() -> None:
    async with SessionFactory() as session:
        existing = await session.scalar(select(func.count()).select_from(KbDocument))
        if existing:
            print(f"Knowledge base already has {existing} document(s) — nothing to do.")
            return

        service = KnowledgeBaseService(
            DocumentRepository(session),
            settings.storage_dir,
            settings.max_upload_size_bytes,
            ArqIngestQueue(),
        )
        for title, filename, text in _DOCUMENTS:
            await service.ingest_upload(
                filename=filename, content=text.encode("utf-8"), title=title
            )

        print(f"Seeded {len(_DOCUMENTS)} knowledge-base documents; a running worker embeds them.")


if __name__ == "__main__":
    asyncio.run(seed_kb())
