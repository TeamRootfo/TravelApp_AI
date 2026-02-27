from pydantic import BaseModel


class TTSRequest(BaseModel):
    location_name: str
    user_id: str = "user"
    session_id: str = "default"