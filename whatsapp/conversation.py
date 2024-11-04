import os
import sqlite3
import logging
from concurrent.futures import ThreadPoolExecutor

from whatsapp.events import Message
from whatsapp.agent_interface import AgentInterface
from whatsapp.conversation_handler import ConversationHandler
from whatsapp.reply_message import Message as ReplyMessage, Text


logger = logging.getLogger("whatsapp")

TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "")


class Conversation(AgentInterface, ConversationHandler):
    def __init__(
            self,
            debug=False,
            start_proxy=True,
            media_root: str = "media",
            webhook_initialize_string="token",
            gemini_model_name: str = "models/gemini-1.5-flash",
            gemini_api_key: str = os.environ.get("GEMINI_API_KEY", ""),
    ):
        AgentInterface.__init__(
            self,
            gemini_model_name,
            gemini_api_key
        )
        ConversationHandler.__init__(
            self,
            start_proxy,
            media_root,
            webhook_initialize_string,
        )

        if debug:
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)
            logger.setLevel(logging.DEBUG)

    def get_connection(self):
        return sqlite3.connect("conversation.db")

    def on_message(self, message: Message):
        chat_id = message.to
        text = (
            message.message.text.body
            if message.message.text
            else ""
        )

        res = self.handler(chat_id, text)
        data = Text(
            body=res,
            preview_url=False,
        )
        reply = ReplyMessage(
            text=data,
            to=chat_id,
            type="text",
        )
        self.send(reply)

    def start(self, port: int = 5000, host="localhost"):
        logger.info("Starting conversation handler")
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(self._handle_new_message)
            executor.submit(lambda: self.create_server(self.queue, host, port))
