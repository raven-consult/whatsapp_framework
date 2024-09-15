from pydantic import BaseModel
from typing_extensions import Optional


class Text(BaseModel):
    preview_url: bool
    body: str


class Context(BaseModel):
    message_id: str


class Message(BaseModel):
    to: str
    type: str
    text: Optional[Text]
    messaging_product: str = "whatsapp"
    context: Optional[Context] | None = None
