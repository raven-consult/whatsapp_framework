import os
import logging
from concurrent.futures import ThreadPoolExecutor

import google.generativeai as genai

from whatsapp.events import Message
from whatsapp._history import ConversationHistory
from whatsapp.agent_interface import AgentInterface
from whatsapp.conversation_handler import ConversationHandler
from whatsapp.reply_message import Message as ReplyMessage, Text


logger = logging.getLogger("whatsapp")

TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "")


class Conversation(AgentInterface, ConversationHandler):
    def __init__(
            self,
            port=5000,
            debug=False,
            start_proxy=True,
            media_root: str = "media",
            webhook_initialize_string="token",
            gemini_model_name: str = "models/gemini-1.5-flash",
            gemini_api_key: str = os.environ.get("GEMINI_API_KEY", ""),
    ):
        self.port = port
        self.media_root = media_root
        self.start_proxy = start_proxy
        self.webhook_initialize_string = webhook_initialize_string

        self.model_name = gemini_model_name
        self.history = ConversationHistory()
        genai.configure(api_key=gemini_api_key)
        self.instructions = self.get_all_instructions()

        if debug:
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)
            logger.setLevel(logging.DEBUG)

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
