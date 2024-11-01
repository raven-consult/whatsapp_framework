import sqlite3
from dataclasses import dataclass
from typing import Literal

MessageTypes = Literal["text", "function_call", "function_response"]


@dataclass
class Message:
    chat_id: int
    sender: str
    data: str
    id: int | None = None
    type: MessageTypes = "text"


class ConversationHistory:

    def __init__(self, conversation_id: str, db_name: str = "chat.db"):
        self.conversation_id = conversation_id
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                type TEXT NOT NULL,
                sender TEXT NOT NULL,
                data TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def insert_message(self, message: Message):
        self.cursor.execute(
            """
            INSERT INTO messages
            (conversation_id, chat_id, type, sender, data)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                self.conversation_id,
                message.chat_id,
                message.type,
                message.sender,
                message.data,
            )
        )
        self.conn.commit()

    def get_messages(self, chat_id: str):
        self.cursor.execute(
            """
            SELECT id, chat_id, type, sender, data
            FROM messages
            WHERE conversation_id=? AND chat_id=?
            """,
            (
                self.conversation_id,
                chat_id,
            )
        )
        res = self.cursor.fetchall()

        return [Message(
            id=r[0],
            chat_id=r[1],
            type=r[2],
            sender=r[3],
            data=r[4],
        ) for r in res]
