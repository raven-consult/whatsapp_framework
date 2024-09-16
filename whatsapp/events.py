from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

MessageType = Literal[
    "audio",
    "button",
    "document",
    "reaction",
    "text",
    "image",
    "interactive",
    "order",
    "sticker",
    "system",  # for customer number change messages
    "unknown",
    "video"
]


class Text(BaseModel):
    body: str


class Audio(BaseModel):
    id: str
    sha256: str
    voice: bool
    mime_type: str


class Video(BaseModel):
    id: str
    sha256: str
    mime_type: str


class Image(BaseModel):
    id: str
    sha256: str
    mime_type: str


class Document(BaseModel):
    id: str
    sha256: str
    filename: str
    mime_type: str


class MessageEvent(BaseModel):
    id: str
    timestamp: str
    type: MessageType
    file: Path | None = None
    from_: str = Field(alias="from")
    text: Optional[Text] | None = None
    image: Optional[Image] | None = None
    audio: Optional[Audio] | None = None
    video: Optional[Video] | None = None
    document: Optional[Document] | None = None


class Profile(BaseModel):
    name: str


class Contact(BaseModel):
    wa_id: str
    profile: Profile


class Metadata(BaseModel):
    phone_number_id: str
    display_phone_number: str


class Origin(BaseModel):
    type: str


class Conversation(BaseModel):
    id: str
    origin: Origin
    expiration_timestamp: str | None = None


class Pricing(BaseModel):
    billable: bool
    category: str
    pricing_model: str


class Status(BaseModel):
    id: str
    status: str
    timestamp: str
    recipient_id: str
    pricing: Pricing | None = None
    conversation: Conversation | None = None


class Value(BaseModel):
    metadata: Metadata
    messaging_product: str = "whatsapp"
    statuses: Optional[List[Status]] | None = None
    contacts: Optional[List[Contact]] | None = None
    messages: Optional[List[MessageEvent]] | None = None


class Change(BaseModel):
    field: str
    value: Value


class Entry(BaseModel):
    id: str
    changes: List[Change]


class WhatsappEvent(BaseModel):
    object: str
    entry: List[Entry]


class Message(BaseModel):
    to: str
    type: MessageType
    message: MessageEvent
    contacts: List[Contact]
