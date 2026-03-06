import logging
from typing import List
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings

logger = logging.getLogger(__name__)


class TagSuggestion(BaseModel):
    tags: List[str] = Field(
        default_factory=list, description="Tags selected ONLY from allowed_tags"
    )


async def suggest_tags_from_description(
    description: str,
    allowed_tags: List[str],
) -> List[str]:
    logger.info(
        f"[suggest_tags_from_description] Suggesting tags for: {description[:50]}..."
    )

    llm = ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=getattr(settings, "OPENAI_TAG_MODEL", "gpt-4.1-mini"),
        temperature=0,
    )

    parser = PydanticOutputParser(pydantic_object=TagSuggestion)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a strict tag classifier.\n"
                "Select the most suitable tags that describe the place.\n"
                "Rules:\n"
                "- You MUST choose tags ONLY from allowed_tags.\n"
                "- Do NOT invent new tags.\n"
                "- If none apply, return an empty list.\n"
                "{format_instructions}\n",
            ),
            (
                "human",
                "allowed_tags: {allowed_tags}\n\n" "description: {description}",
            ),
        ]
    )

    chain = prompt | llm | parser

    parsed: TagSuggestion = await chain.ainvoke(
        {
            "description": description,
            "allowed_tags": allowed_tags,
            "format_instructions": parser.get_format_instructions(),
        }
    )

    # Final safety filter (extra safety)
    allowed = {t.strip().lower() for t in allowed_tags}
    out: List[str] = []
    for t in parsed.tags:
        tt = (t or "").strip().lower()
        if tt in allowed and tt not in out:
            out.append(tt)

    logger.info(f"[suggest_tags_from_description] Resulting tags: {out}")
    return out
