import os
import logging
from queue import Queue
from pathlib import Path
from typing import Literal
from datetime import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

import requests
from pyngrok import ngrok
from werkzeug import Request, Response
from werkzeug.serving import make_server

from whatsapp._types import BaseInterface
from whatsapp.utils import mime_to_extension
from whatsapp.reply_message import Message as ReplyMessage
from whatsapp.events import Change, WhatsappEvent, Message


logger = logging.getLogger(__name__)

TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "")
NGROK_AUTH_TOKEN = os.environ.get("NGROK_AUTH_TOKEN", "")


@dataclass
class ConversationData:
    id: int
    customer_id: str
    start_time: int
    end_time: int | None
    intent: str | None


Sender = Literal["bot", "customer"]


@dataclass
class ConversationMessage:
    id: int
    conversation_id: int
    sender: Sender
    timestamp: int
    message: str


class ConversationHandler(BaseInterface, ABC):
    queue: Queue[Message] = Queue()
    url = "https://graph.facebook.com/v20.0"

    token: str = TOKEN
    whatsapp_number: str = WHATSAPP_NUMBER

    def __init__(
            self,
            start_proxy=True,
            media_root: str = "media",
            webhook_initialize_string="token",
    ):
        self.media_root = media_root
        self.start_proxy = start_proxy
        self.webhook_initialize_string = webhook_initialize_string
        self.create_whatsapp_conversation_tables()

        if not self.whatsapp_number:
            raise ValueError(
                "whatsapp_number is required but not defined in class")
        if not self.token:
            raise ValueError("token is required but not defined in class")

    def _handle_new_message(self):
        logger.debug("Listening for new messages...")
        while True:
            message = self.queue.get(block=True)
            self.on_message(message)

    @abstractmethod
    def on_message(self, message: Message):
        pass

    def create_whatsapp_conversation_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        logging.debug("Creating tables...")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS whatsapp_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                start_time INTEGER NOT NULL, -- Unix timestamp
                end_time INTEGER, -- Unix timestamp
                intent TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS whatsapp_conversations_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                timestamp INTEGER NOT NULL, -- Unix timestamp
                message TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES whatsapp_conversations (id)
            )
            """
        )
        conn.commit()

    def get_current_conversation(self, customer_id: str):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, start_time, end_time, intent
            FROM whatsapp_conversations
            WHERE customer_id=? AND end_time IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (customer_id,)
        )
        res = cursor.fetchone()

        if res:
            return ConversationData(
                id=res[0],
                customer_id=customer_id,
                start_time=res[1],
                end_time=res[2],
                intent=res[3],
            )
        return None

    def start_conversation(self, customer_id: str, start_time: int):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO whatsapp_conversations
                (customer_id, start_time)
                VALUES (?, ?)
                """,
                (
                    customer_id,
                    start_time,
                )
            )
            conn.commit()
            conversation_id = cursor.lastrowid
            if not conversation_id:
                raise ValueError("Failed to start conversation with customer")

            return ConversationData(
                id=conversation_id,
                customer_id=customer_id,
                start_time=start_time,
                end_time=None,
                intent=None,
            )
        except Exception as e:
            logging.error(e)
            raise e

    def add_message(self, conversation_id: int, sender: Sender, timestamp: int, message: str):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO whatsapp_conversations_messages
                (conversation_id, sender, timestamp, message)
                VALUES (?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    sender,
                    timestamp,
                    message,
                )
            )
            conn.commit()
            conversation_message_id = cursor.lastrowid

            if not conversation_message_id:
                raise ValueError("Failed to add message to conversation")

            return ConversationMessage(
                id=conversation_message_id,
                conversation_id=conversation_id,
                sender=sender,
                timestamp=timestamp,
                message=message,
            )
        except Exception as e:
            logging.error(e)
            raise e

    def end_conversation(self, conversation_id: int, end_time: int, intent: str):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE whatsapp_conversations
                SET end_time=?, intent=?
                WHERE id=?
                """,
                (
                    end_time,
                    intent,
                    conversation_id,
                )
            )
            conn.commit()
            res = cursor.execute(
                """
                SELECT id, customer_id, start_time, end_time, intent
                FROM whatsapp_conversations
                WHERE id=?
                """,
                (conversation_id,)
            ).fetchone()

            return ConversationData(
                id=res[0],
                customer_id=res[1],
                start_time=res[2],
                end_time=res[3],
                intent=res[4],
            )
        except Exception as e:
            logging.error(e)
            raise e

    def _handle_text_message(self, change: Change, queue: Queue):

        if change.field == "messages":
            if change.value.messages:
                for message in change.value.messages:
                    logger.debug("Received text message: %s", message)
                    data = Message(
                        message=message,
                        to=message.from_,
                        type=message.type,
                        contacts=change.value.contacts if change.value.contacts else [],
                    )

                    conversation = self.get_current_conversation(
                        message.from_)
                    if not conversation:
                        conversation = self.start_conversation(
                            message.from_,
                            int(datetime.now().timestamp()),
                        )

                    val = message.text.body if message.text else ""
                    self.add_message(
                        conversation.id,
                        "customer",
                        int(message.timestamp),
                        val,
                    )
                    queue.put(data)

    def _handle_media_message(self, change: Change, queue: Queue):
        if change.field == "messages":
            if change.value.messages:
                for message in change.value.messages:
                    logger.debug("Received media message: %s", message)
                    if message.type in ["image", "audio", "video", "document"]:
                        data = getattr(message, message.type)
                        logger.debug("Downloading media...")
                        mime_type = data.mime_type.split(";")[0]
                        file = self._download_media(data.id, mime_type)
                        message.file = file

                        data = Message(
                            message=message,
                            to=message.from_,
                            type=message.type,
                            contacts=change.value.contacts if change.value.contacts else [],
                        )

                        # TODO: Storage of media messages
                        conversation = self.get_current_conversation(
                            message.from_)
                        if not conversation:
                            conversation = self.start_conversation(
                                message.from_,
                                int(datetime.now().timestamp()),
                            )

                        queue.put(data)

    def _handle_status_message(self, change: Change, queue: Queue):
        if change.field == "messages":
            if change.value.statuses:
                # Ignore for now
                pass

    def _handle_verification(self, request: Request, webhook_initialize_string: str):
        hub_mode = request.args.get("hub.mode", "")
        hub_challenge = request.args.get("hub.challenge", "")
        hub_verify_token = request.args.get("hub.verify_token", "")

        if hub_mode == "subscribe" and hub_verify_token == webhook_initialize_string:
            return Response(hub_challenge, 200)
        else:
            return Response("Verification failed", 403)

    def create_server(self, q: Queue, host: str, port: int) -> None:
        logging.info("Creating server...")

        @Request.application
        def app(request: Request) -> Response:
            if request.method == "GET":
                logger.debug("Handling verification...")
                return self._handle_verification(
                    request, self.webhook_initialize_string)
            elif request.method == "POST":
                try:
                    data = request.get_json()
                    data = WhatsappEvent(**data)
                    data = data.entry[0]

                    for change in data.changes:
                        self._handle_text_message(change, q)
                        self._handle_media_message(change, q)
                        self._handle_status_message(change, q)
                    return Response("Received", 200)

                except Exception as e:
                    logger.error("Error: %s", e)
                    return Response("Error", 500)
                finally:
                    pass
            return Response("", 200)

        logging.debug("Starting server...")

        if self.start_proxy:
            self._setup_ngrok(port)

        server = make_server(
            host, port, app,
            threaded=True, processes=1
        )
        server.serve_forever()

    def _setup_ngrok(self, port: int):
        ngrok.set_auth_token(NGROK_AUTH_TOKEN)

        public_url = ngrok.connect(str(port))
        logger.info(
            f" * %s", public_url)
        logger.info(" * Use %s as the webhook verify token",
                    self.webhook_initialize_string)

    def _download_media(self, media_id: str, mime_type: str):
        response = requests.get(
            f"{self.url}/{media_id}",
            headers={
                "Authorization": f"Bearer {self.token}"
            },
        )

        url = response.json()["url"]
        filename = Path(f"{self.media_root}") / \
            f"{media_id}{mime_to_extension[mime_type]}"
        filename.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {self.token}"
            }
        )

        with open(filename, "wb") as file:
            file.write(response.content)

        return filename

    def _upload_media(self, phone_number_id: str, filename: str, mime_type: str):
        response = requests.post(
            f"{self.url}/{phone_number_id}/media",
            headers={
                "Authorization": f"Bearer {self.token}"
            },
            data={
                "type": mime_type,
                "messaging_product": "whatsapp",
            },
            files={
                "file": (filename, open(filename, "rb"), mime_type)
            }
        )

        data = response.json()
        logger.debug("Media uploaded: %s", data)
        return data["id"]

    def send(self, message: ReplyMessage):
        if message.type in ["audio", "video", "document", "image", "sticker"]:
            media = getattr(message, message.type)
            filename_id = self._upload_media(
                self.whatsapp_number, media.file, media.mime_type)
            media.id = filename_id

            del media.file
            del media.mime_type
            setattr(message, message.type, media)

        conversation = self.get_current_conversation(message.to)
        if not conversation:
            raise ValueError("No active conversation found")

        timestamp = int(datetime.now().timestamp())
        data = message.text.body if message.text else ""
        self.add_message(
            conversation.id,
            "bot",
            timestamp,
            data,
        )

        response = requests.post(
            f"{self.url}/{self.whatsapp_number}/messages",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}"
            },
            json=message.model_dump()
        )

        logger.debug("Message sent: %s", message)
        logger.debug("Response: %s", response.json())
        return True

    def start(self, port: int = 5000, host="localhost"):
        with ThreadPoolExecutor() as executor:
            executor.submit(self._handle_new_message)
            executor.submit(lambda: self.create_server(self.queue, host, port))
