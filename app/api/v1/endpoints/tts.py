from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.tts import TTSRequest
from app.services.tts.elevenlabs_service import text_to_speech_stream

router = APIRouter(prefix="/tts", tags=["tts"])


@router.post("/speak")
async def speak(payload: TTSRequest):
    try:
        audio_stream = text_to_speech_stream(payload.text)
        return StreamingResponse(
            audio_stream,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"},
        )
    except Exception as e:
        return {"error": str(e)}


@router.get("/speak-test")
async def speak_test():
    audio_stream = text_to_speech_stream("Hello, this is a test.")
    return StreamingResponse(audio_stream, media_type="audio/mpeg")