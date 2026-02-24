from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def embed_text(text: str) -> list[float]:
    text = (text or "").strip()
    if not text:
        return []

    resp = await client.embeddings.create(
        model=settings.OPENAI_EMBED_MODEL,  # text-embedding-3-small -> 1536 dims
        input=text,
    )
    return resp.data[0].embedding