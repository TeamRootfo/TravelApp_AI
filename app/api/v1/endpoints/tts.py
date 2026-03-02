from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.models.tts import TTSRequest
from app.services.story_teller.story_agent import generate_location_story
from app.services.tts.gpt_tts_service import text_to_speech_stream

router = APIRouter(prefix="/tts", tags=["tts"])


@router.post("/speak")
async def speak(payload: TTSRequest):
    try:
        # generate_location_story is async; await it
        story_text = await generate_location_story(payload.location_name, payload.user_id, payload.session_id)
        print(f"Generated story text: {story_text}")
        if not story_text:
            return {"error": "No story generated"}

        # text_to_speech_stream is blocking; run it in a threadpool
        audio_stream = await run_in_threadpool(text_to_speech_stream, story_text)
        if audio_stream is None:
            return {"error": "TTS generation failed"}

        return StreamingResponse(
            audio_stream,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"},
        )
    except Exception as e:
        return {"error": str(e)}


@router.get("/speak-test")
async def speak_test():
    audio_stream = await run_in_threadpool(text_to_speech_stream, "Welcome to Sigiriya, one of Sri Lanka’s most captivating ancient wonders. Imagine climbing a massive rock fortress rising dramatically from the lush jungle, a place that once served as a royal palace and stronghold. As you ascend, you’ll encounter stunning frescoes painted on the rock face, delicate and vibrant, offering a glimpse into the artistry of a bygone era. Don’t miss the Mirror Wall, once so polished it reflected the king’s image, now adorned with centuries-old inscriptions and poems. At the summit, you’ll be rewarded with breathtaking panoramic views of the surrounding landscape, a perfect spot to pause and soak in the history and natural beauty. The best time to visit is during the cooler, drier months when the climb is more comfortable and the skies clearer. Remember to dress modestly out of respect for this cultural heritage site, and be mindful of your footing as some paths can be steep and uneven. Sigiriya is not just a climb; it’s a journey through time, culture, and nature all in one unforgettable experience")
    if audio_stream is None:
        return {"error": "TTS generation failed"}
    return StreamingResponse(audio_stream, media_type="audio/mpeg")