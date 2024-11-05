import sqlite3
from typing import Literal
from dataclasses import dataclass
from abc import ABC, abstractmethod


class BaseInterface(ABC):

    @abstractmethod
    def get_connection(self) -> sqlite3.Connection:
        pass


@dataclass
class ConversationData:
    id: str
    customer_id: str
    start_time: int
    end_time: int | None
    intent: str | None


Sender = Literal["bot", "customer"]
MessageTypes = Literal["text", "function_call", "function_response"]


@dataclass
class ChatMessage:
    id: str
    conversation_id: int
    sender: Sender
    timestamp: int
    message: str


@dataclass
class AgentMessage:
    id: str
    data: str
    sender: str
    conversation_id: int
    type: MessageTypes = "text"
