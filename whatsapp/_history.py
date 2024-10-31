import sqlite3


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
                message TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                sender TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def insert_message(self, chat_id: str, sender: str, message: str):
        self.cursor.execute(
            """
            INSERT INTO messages
            (conversation_id, message, chat_id, sender)
            VALUES (?, ?, ?)
            """,
            (
                self.conversation_id,
                message,
                chat_id,
                sender,
            )
        )
        self.conn.commit()

    def get_messages(self, chat_id: str):
        self.cursor.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id=? AND chat_id=?
            """,
            (
                self.conversation_id,
                chat_id,
            )
        )
        return self.cursor.fetchall()
