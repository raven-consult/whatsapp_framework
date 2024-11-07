import sqlite3
import logging
from typing import List

from whatsapp._types import (
    Sender,
    ChatMessage,
    AgentMessage,
    ConversationData,
)

logger = logging.getLogger(__name__)


class BaseDatastore:
    def create_tables(self):
        raise NotImplementedError

    def create_conversation(self, customer_id: str, start_time: int) -> ConversationData:
        raise NotImplementedError

    def end_conversation(self, customer_id: str, timestamp: int):
        raise NotImplementedError

    def add_chat_message(self, conversation_id: str, sender: str, timestamp: int, message: str):
        raise NotImplementedError

    def add_agent_message(self, conversation_id: str, type: str, sender: Sender, data: str):
        raise NotImplementedError

    def get_chat_messages(self) -> List[ChatMessage]:
        raise NotImplementedError

    def get_agent_messages(self, conversation_id: str) -> List[AgentMessage]:
        raise NotImplementedError

    def get_current_conversation(self, customer_id: str) -> ConversationData:
        raise NotImplementedError


class SQLiteDatastore(BaseDatastore):

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()

        self.create_tables()

    def create_tables(self):
        logging.debug("Creating tables...")
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                start_time INTEGER NOT NULL, -- Unix timestamp
                end_time INTEGER, -- Unix timestamp
                intent TEXT
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                type TEXT NOT NULL,
                sender TEXT NOT NULL,
                data TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                timestamp INTEGER NOT NULL, -- Unix timestamp
                message TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
            """
        )
        self.conn.commit()

    def create_conversation(self, customer_id, start_time):
        self.cursor.execute(
            """
            INSERT INTO conversations
            (customer_id, start_time)
            VALUES (?, ?)
            """,
            (customer_id, start_time,)
        )
        self.conn.commit()
        conversation_id = str(self.cursor.lastrowid)
        if not conversation_id:
            raise ValueError("Failed to start conversation with customer")

        return ConversationData(
            id=conversation_id,
            customer_id=customer_id,
            start_time=start_time,
            end_time=None,
            intent=None,
        )

    def get_current_conversation(self, customer_id):
        self.cursor.execute(
            """
            SELECT id, customer_id, start_time, end_time, intent
            FROM conversations
            WHERE customer_id=? AND end_time IS NULL
            ORDER BY start_time DESC
            LIMIT 1
            """,
            (customer_id,)
        )
        res = self.cursor.fetchone()

        return ConversationData(
            id=res[0],
            customer_id=res[1],
            start_time=res[2],
            end_time=res[3],
            intent=res[4],
        ) if res else None

    def end_conversation(self, customer_id: str, timestamp: int):
        self.cursor.execute(
            """
            UPDATE conversations
            SET end_time=?
            WHERE customer_id=? AND end_time IS NULL
            """,
            (timestamp, customer_id)
        )
        self.conn.commit()

    def add_chat_message(self, conversation_id: str, sender: str, timestamp: int, message: str):
        self.cursor.execute(
            """
            INSERT INTO chat_messages
            (conversation_id, sender, timestamp, message)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, sender, timestamp, message)
        )
        self.conn.commit()

    def add_agent_message(self, conversation_id: str, type: str, sender: Sender, data: str):
        self.cursor.execute(
            """
            INSERT INTO agent_messages
            (conversation_id, type, sender, data)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, type, sender, data)
        )
        self.conn.commit()

    def get_chat_messages(self, conversation_id: str):
        self.cursor.execute(
            """
            SELECT id, conversation_id, sender, timestamp, message
            FROM chat_messages
            WHERE conversation_id=?
            """,
            (conversation_id,)
        )
        res = self.cursor.fetchall()

        return [
            ChatMessage(
                id=r[0],
                conversation_id=r[1],
                sender=r[2],
                timestamp=r[3],
                message=r[4],
            ) for r in res
        ]

    def get_agent_messages(self, conversation_id: str):
        self.cursor.execute(
            """
            SELECT id, conversation_id, type, sender, data
            FROM agent_messages
            WHERE conversation_id=?
            """,
            (conversation_id,)
        )
        res = self.cursor.fetchall()

        return [
            AgentMessage(
                id=r[0],
                conversation_id=r[1],
                type=r[2],
                sender=r[3],
                data=r[4],
            ) for r in res
        ]
