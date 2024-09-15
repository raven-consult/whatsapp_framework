from pprint import pprint
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

import requests
import multiprocessing
from pyngrok import ngrok
from werkzeug import Request, Response, run_simple

from whatsapp.reply_message import Message
from whatsapp.events import MessageEvent, WhatsappEvent


class ChatHandler(ABC):
    queue = multiprocessing.Queue()
    url = "https://graph.facebook.com/v20.0"

    token: str
    whatsapp_number: str

    def __init__(self, port=5000, start_proxy=True, webhook_initialize_string="token", debug=True):
        self.port = port
        self.debug = debug
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
    def on_message(self, message: MessageEvent):
        pass

    def create_server(self, q: multiprocessing.Queue) -> None:
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
                                    q.put(message)
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

    def send(self, message: Message):
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
