import logging
from queue import Queue
from pathlib import Path
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

import requests
from pyngrok import ngrok
from werkzeug import Request, Response
from werkzeug.serving import make_server

from whatsapp.utils import mime_to_extension
from whatsapp.reply_message import Message as ReplyMessage
from whatsapp._handle_verfication import handle_verification
from whatsapp.events import Change, MessageEvent, WhatsappEvent, Message


logger = logging.getLogger(__name__)


class ChatHandler(ABC):
    queue: Queue[Message] = Queue()
    url = "https://graph.facebook.com/v20.0"

    token: str
    whatsapp_number: str

    def __init__(
            self,
            port=5000,
            start_proxy=True,
            media_root: str = "media",
            webhook_initialize_string="token",
    ):
        self.port = port
        self.media_root = media_root
        self.start_proxy = start_proxy
        self.webhook_initialize_string = webhook_initialize_string

        if not self.whatsapp_number:
            raise ValueError("whatsapp_number is required")
        if not self.token:
            raise ValueError("token is required")

    def _handle_new_message(self):
        while True:
            message = self.queue.get(block=True)
            logger.debug(f"Received message: %s", message)

            self.on_message(message)

    @abstractmethod
    def on_message(self, message: Message):
        pass

    def _handle_text_message(self, change: Change, queue: Queue):
        if change.field == "messages":
            if change.value.messages:
                for message in change.value.messages:
                    logger.debug("Received message: %s", message)
                    data = Message(
                        message=message,
                        to=message.from_,
                        type=message.type,
                        contacts=change.value.contacts if change.value.contacts else [],
                    )
                    queue.put(data)

    def _handle_media_message(self, change: Change, queue: Queue):
        if change.field == "messages":
            if change.value.messages:
                for message in change.value.messages:
                    logger.debug("Received message: %s", message)
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
                    queue.put(data)

    def _handle_status_message(self, change: Change, queue: Queue):
        if change.field == "messages":
            if change.value.statuses:
                # Ignore for now
                pass

    def create_server(self, q: Queue, host: str, port: int) -> None:
        @Request.application
        def app(request: Request) -> Response:
            if request.method == "GET":
                handle_verification(request, self.webhook_initialize_string)
            elif request.method == "POST":
                try:
                    logger.debug("################################")
                    data = request.get_json()
                    logger.debug("Data: %s", data)

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
                    logger.debug("################################")
                    logger.debug("")
            return Response("", 200)

        if self.start_proxy:
            public_url = ngrok.connect(str(port))
            logger.info(
                f" * ngrok tunnel %s -> %s", public_url, f"http://{host}:{port}")
            logger.info(" * Use %s as the webhook verify token",
                        self.webhook_initialize_string)

        server = make_server(host, port, app)
        server.serve_forever()

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

    def start(self, host="localhost", port=5000):
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(self._handle_new_message)
            executor.submit(lambda: self.create_server(self.queue, host, port))
