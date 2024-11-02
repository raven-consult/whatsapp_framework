import sqlite3
import logging
from typing import Literal
from dataclasses import dataclass


logging = logging.getLogger(__name__)


MessageTypes = Literal["text", "function_call", "function_response"]


@dataclass
class Message:
    chat_id: int
    sender: str
    data: str
    id: int | None = None
    type: MessageTypes = "text"


class ConversationHistory:

    def __init__(self, db_name: str = "chat.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        logging.debug("Creating table")
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                type TEXT NOT NULL,
                sender TEXT NOT NULL,
                data TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def insert_message(self, message: Message):
        try:
            self.cursor.execute(
                """
                INSERT INTO messages
                (conversation_id, type, sender, data)
                VALUES (?, ?, ?, ?)
                """,
                (
                    message.chat_id,
                    message.type,
                    message.sender,
                    message.data,
                )
            )
            self.conn.commit()
        except Exception as e:
            logging.error(e)
            raise e

    def get_messages(self, chat_id: str):
        self.cursor.execute(
            """
            SELECT id, conversation_id, type, sender, data
            FROM messages
            WHERE conversation_id=?
            """,
            (
                chat_id,
            )
        )
        res = self.cursor.fetchall()

        return [
            Message(
                id=r[0],
                chat_id=r[1],
                type=r[2],
                sender=r[3],
                data=r[4],
            ) for r in res
        ]
