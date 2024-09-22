from pydantic import BaseModel
from typing_extensions import Optional

from whatsapp.events import MessageType


class Text(BaseModel):
    preview_url: bool
    body: str


class Audio(BaseModel):
    file: str
    mime_type: str
    id: str | None = None
    link: str | None = None


class Video(BaseModel):
    file: str
    mime_type: str
    id: str | None = None
    link: str | None = None
    caption: str | None = None


class Document(BaseModel):
    file: str
    mime_type: str
    id: str | None = None
    link: str | None = None
    caption: str | None = None
    filename: str | None = None


class Image(BaseModel):
    file: str
    mime_type: str
    id: str | None = None
    link: str | None = None
    caption: str | None = None


class Context(BaseModel):
    message_id: str


class Sticker(BaseModel):
    file: str
    mime_type: str
    id: str | None = None
    link: str | None = None


class Message(BaseModel):
    to: str
    type: MessageType
    text: Text | None = None
    audio: Audio | None = None
    video: Video | None = None
    image: Image | None = None
    document: Document | None = None
    messaging_product: str = "whatsapp"
    context: Optional[Context] | None = None
