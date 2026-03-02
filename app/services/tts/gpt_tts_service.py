from io import BytesIO
from typing import IO, Optional

from openai import OpenAI

from app.core.config import settings

# Make sure you have settings.OPENAI_API_KEY set
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def text_to_speech_stream(text: str) -> Optional[IO[bytes]]:
    try:
        audio_stream = BytesIO()

        # Streaming response (chunked transfer) :contentReference[oaicite:1]{index=1}
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="cedar",
            input=text,
            response_format="mp3",
            instructions="Speak in a cheerful and positive tone.",
        ) as response:
            # Write streamed bytes into memory
            for chunk in response.iter_bytes():
                if chunk:
                    audio_stream.write(chunk)

        audio_stream.seek(0)
        return audio_stream

    except Exception as e:
        print(f"Error generating speech: {e}")
        return None
