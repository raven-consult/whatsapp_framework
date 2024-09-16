from queue import Queue
from pathlib import Path
from pprint import pprint
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

import requests
import multiprocessing
from pyngrok import ngrok
from werkzeug import Request, Response, run_simple

from whatsapp.reply_message import Message as ReplyMessage
from whatsapp.events import MessageEvent, WhatsappEvent, Message


mime_to_extension = {
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "text/calendar": ".ics",
    "application/zip": ".zip",
    "application/x-rar-compressed": ".rar",
    "application/x-tar": ".tar",
    "application/x-7z-compressed": ".7z",
    "application/x-xz": ".xz",
    "application/gzip": ".gz",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.oasis.opendocument.text": ".odt",
    "application/vnd.oasis.opendocument.spreadsheet": ".ods",
    "application/vnd.oasis.opendocument.presentation": ".odp",
    "application/vnd.oasis.opendocument.graphics": ".odg",
    "application/vnd.oasis.opendocument.formula": ".odf",
    "application/vnd.ms-outlook": ".msg",
    "application/vnd.ms-publisher": ".pub",
    "application/vnd.visio": ".vsd",
    "application/vnd.visio2013": ".vsdx",
    "application/vnd.ms-access": ".mdb",
    "application/vnd.oasis.opendocument.database": ".odb",
    "application/vnd.oasis.opendocument.chart": ".odc",
    "video/mp4": ".mp4",
    "video/3gpp": ".3gp",
    "video/quicktime": ".mov",
    "video/x-msvideo": ".avi",
    "video/x-ms-wmv": ".wmv",
    "video/x-flv": ".flv",
    "application/pdf": ".pdf",
}


class ChatHandler(ABC):
    queue: Queue[Message] = Queue()
    url = "https://graph.facebook.com/v20.0"

    token: str
    whatsapp_number: str

    def __init__(self, port=5000, start_proxy=True, media_root: str = "media", webhook_initialize_string="token", debug=True):
        self.port = port
        self.debug = debug
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
            print("Received message:", message) if self.debug else None

            self.on_message(message)

    @abstractmethod
    def on_message(self, message: Message):
        pass

    def create_server(self, q: Queue) -> None:
        @Request.application
        def app(request: Request) -> Response:
            if request.method == "GET":
                hub_mode = request.args.get("hub.mode", "")
                hub_challenge = request.args.get("hub.challenge", "")
                hub_verify_token = request.args.get("hub.verify_token", "")

                if hub_mode == "subscribe" and hub_verify_token == "token":
                    return Response(hub_challenge, 200)
            elif request.method == "POST":
                try:
                    print("################################") if self.debug else None
                    data = request.get_json()
                    pprint(data) if self.debug else None

                    data = WhatsappEvent(**data)
                    data = data.entry[0]

                    for change in data.changes:
                        if change.field == "messages":
                            if change.value.statuses:
                                # Ignore for now
                                pass

                            if change.value.messages:
                                for message in change.value.messages:
                                    print("Received message:",
                                          message) if self.debug else None
                                    if message.type in ["image", "audio", "video", "document"]:
                                        data = getattr(message, message.type)
                                        print("Downloading media...",
                                              ) if self.debug else None
                                        mime_type = data.mime_type.split(";")[
                                            0]
                                        file = self._download_media(
                                            data.id, mime_type)
                                        message.file = file
                                    data = Message(
                                        message=message,
                                        to=message.from_,
                                        type=message.type,
                                        contacts=change.value.contacts if change.value.contacts else [],
                                    )
                                    q.put(data)
                    return Response("Received", 200)
                except Exception as e:
                    print(e)
                    return Response("Error", 500)
                finally:
                    print("################################") if self.debug else None
                    print() if self.debug else None
            return Response("", 200)

        if self.start_proxy:
            public_url = ngrok.connect("5000")
            print(
                f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:5000\"")
            print(" * Use " + self.webhook_initialize_string +
                  " as the webhook verify token")

        run_simple("localhost", 5000, app, use_reloader=False,
                   use_debugger=False, use_evalex=False)

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

    def send(self, message: ReplyMessage):
        response = requests.post(
            f"{self.url}/{self.whatsapp_number}/messages",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}"
            },
            json=message.model_dump()
        )
        print("Message sent:", message) if self.debug else None
        print("Response:", response.json()) if self.debug else None
        return True

    def start(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(self._handle_new_message)
            executor.submit(lambda: self.create_server(self.queue))
