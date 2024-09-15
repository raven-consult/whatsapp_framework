from typing import List, Optional
from pydantic import BaseModel, Field


class Text(BaseModel):
    body: str


class MessageEvent(BaseModel):
    id: str
    type: str
    timestamp: str
    text: Optional[Text]
    from_: str = Field(alias="from")


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
    conversation: Conversation
    id: str
    status: str
    timestamp: str
    pricing: Pricing
    recipient_id: str


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
