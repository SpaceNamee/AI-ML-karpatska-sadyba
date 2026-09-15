"""POST /query against a real embedding + a real pgvector similarity search.

Uses the real embedding model (already loaded and cached from Day 7/8/9 work)
rather than a hand-crafted fake vector — a fake vector could pass while the
real cosine_distance() query, join, or column type were all subtly wrong.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import embed_texts, get_shared_model
from app.db.models.kb import KbChunk, KbDocument


async def test_query_ranks_the_semantically_matching_chunk_first(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    model = await get_shared_model()
    relevant_text = "Заїзд можливий з 15:00, виїзд до 11:00."
    unrelated_text = "Найближчий гірськолижний курорт за 5 кілометрів від садиби."
    relevant_vector, unrelated_vector = embed_texts(model, [relevant_text, unrelated_text])

    document = KbDocument(
        title="Integration test doc",
        original_filename="t.txt",
        stored_path="unused-in-this-test",
        content_type="text/plain",
    )
    document.chunks.append(KbChunk(position=0, content=relevant_text, embedding=relevant_vector))
    document.chunks.append(KbChunk(position=1, content=unrelated_text, embedding=unrelated_vector))
    db_session.add(document)
    await db_session.commit()

    response = await api_client.post(
        "/api/v1/query", json={"query": "о котрій годині заїзд?", "limit": 5}
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert results  # the real model found *something*
    assert results[0]["snippet"] == relevant_text
    assert results[0]["document_id"] == document.id


async def test_query_is_public_and_needs_no_token(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/v1/query", json={"query": "будь-яке питання"})

    assert response.status_code == 200
