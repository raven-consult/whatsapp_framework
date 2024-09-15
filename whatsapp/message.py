from typing import Literal
from typing_extensions import TypedDict

from pydantic import BaseModel


class Language(TypedDict):
    code: str


class Template(BaseModel):
    name: str
    language: Language


class Message(BaseModel):
    to: str
    template: Template
    type: Literal["template"]
    messaging_product: Literal["whatsapp"] = "whatsapp"
