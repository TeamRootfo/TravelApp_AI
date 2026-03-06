# from google.adk.agents import Agent
# from google.adk.runners import Runner
# from google.adk.sessions import InMemorySessionService
# from google.adk.tools import google_search
# from google.genai import types
# from google.adk.models.lite_llm import LiteLlm

# APP_NAME = "travel_story_agent"


# root_agent = Agent(
#     name="tour_storyteller",
#     model=LiteLlm(model="openai/gpt-4.1-mini", temperature=0.2),
#     description="Creates tourist-friendly stories about a location using Google Search grounding.",
#     instruction=(
#         "You are a professional tourist storyteller.\n"
#         "Use Google Search grounding when needed.\n"
#         "Write a vivid, friendly, factual narration for first-time travelers.\n"
#         "Keep it 45–90 seconds when spoken. Avoid unsafe claims.\n"
#         "Return ONLY the narration text (no markdown, no bullets)."
#     ),
#     tools=[google_search],
# )

# _session_service = InMemorySessionService()
# _runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=_session_service)


# async def generate_location_story(location_name: str, user_id: str = "user", session_id: str = "default") -> str:
#     # Create session if not exists
#     try:
#         session=await _session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
#         if session is None:
#             await _session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
#     except Exception as e:
#         print(f"Creating new session for user_id='{user_id}', session_id='{session_id}',error: {e}")


#     prompt = (
#         f"Create a tourist narration about: {location_name}.\n"
#         "Include: why it's famous, what to see/do, best time to visit, and 1–2 cultural tips.\n"
#         "Be accurate and grounded."
#     )
#     content = types.Content(role="user", parts=[types.Part(text=prompt)])

#     events = _runner.run_async(user_id=user_id, session_id=session_id, new_message=content)

#     final_text = ""
#     async for event in events:
#         if event.is_final_response():
#             # ADK Googe Search example reads final response from event.content.parts[0].text :contentReference[oaicite:6]{index=6}
#             final_text = (event.content.parts[0].text or "").strip()

#     return final_text

import logging
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.models.lite_llm import LiteLlm
from app.core.config import settings
from app.services.story_teller import tools
from app.services.story_teller.prompts import STORY_AGENT_PROMPT
from app.services.story_teller.tools import fetch_wikipedia_summary
from app.services.story_teller.prompts import STORY_AGENT_PROMPT
from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

APP_NAME = "travel_story_agent"
fetch_wikipedia_summary_tool = FunctionTool(func=fetch_wikipedia_summary)

root_agent = Agent(
    name="tour_storyteller",
    model=LiteLlm(
        model="openai/gpt-4.1-mini", temperature=0.2, api_key=settings.OPENAI_API_KEY
    ),
    description="Creates tourist-friendly stories about a location.",
    instruction=STORY_AGENT_PROMPT,
    tools=[fetch_wikipedia_summary_tool],
)

_session_service = InMemorySessionService()
_runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=_session_service)


async def generate_location_story(
    location_name: str, user_id: str = "api", session_id: str = None
) -> str:
    logger.info(
        f"[generate_location_story] Generating story for: {location_name} (user: {user_id})"
    )
    # Stateless: new session each call (best for APIs)
    if session_id is None:
        session_id = f"story:{location_name}"

    session = await _session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        await _session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

    prompt = (
        f"Create a tourist narration about: {location_name}.\n"
        "Include: what it is, what to see/do, best time to visit (general), and 1–2 respectful cultural tips.\n"
        "Make it immersive but cautious about uncertain facts.\n"
    )
    content = types.Content(role="user", parts=[types.Part(text=prompt)])

    events = _runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    )

    final_text = ""
    async for event in events:
        calls = (
            event.get_function_calls() if hasattr(event, "get_function_calls") else None
        )
        if calls:
            for call in calls:
                logger.info(
                    f"[generate_location_story] TOOL CALLED: {call.name} with args: {call.args}"
                )

        # 2) Tool response(s)
        responses = (
            event.get_function_responses()
            if hasattr(event, "get_function_responses")
            else None
        )
        if responses:
            for resp in responses:
                logger.info(
                    f"[generate_location_story] TOOL RESULT for {resp.name}: {resp.response}"
                )

        if event.is_final_response():
            final_text = (event.content.parts[0].text or "").strip()

    logger.info(
        f"[generate_location_story] Completed story generation. Length: {len(final_text)}"
    )
    return final_text
