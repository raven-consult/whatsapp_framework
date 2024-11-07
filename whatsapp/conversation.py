import os
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from whatsapp.events import Message
from whatsapp.agent_interface import AgentInterface
from whatsapp.conversation_handler import ConversationHandler
from whatsapp.reply_message import Message as ReplyMessage, Text


logger = logging.getLogger("whatsapp")


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
            logger.setLevel(logging.DEBUG)

    def on_message(self, message: Message):
        chat_id = message.to

        # TODO: Storage of media messages
        text = (
            message.message.text.body
            if message.message.text
            else ""
        )

        # conversation = self.datastore.get_current_conversation(chat_id)
        conversation = self.datastore.get_current_conversation(message.to)
        if not conversation:
            conversation = self.datastore.create_conversation(
                message.to,
                int(datetime.now().timestamp()),
            )

        self.datastore.add_chat_message(
            conversation.id,
            "customer",
            int(message.message.timestamp),
            text,
        )

        res, is_ended = self.handler(conversation, text)
        timestamp = int(datetime.now().timestamp())
        self.datastore.add_chat_message(
            conversation.id,
            "bot",
            timestamp,
            res,
        )

        reply = ReplyMessage(
            text=Text(
                body=res,
                preview_url=False,
            ),
            to=chat_id,
            type="text",
        )
        self.send(reply)

        if is_ended:
            self.datastore.end_conversation(chat_id, timestamp)

    def start(self, port: int = 5000, host="localhost"):
        logger.info("Starting conversation handler")
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(self._handle_new_message)
            executor.submit(lambda: self.create_server(self.queue, host, port))
