from whatsapp.chat import ChatHandler
from whatsapp.events import MessageEvent
from whatsapp.reply_message import Message, Text


class SimpleChatHandler(ChatHandler):
    token = "<whatsapp_access_token>"
    whatsapp_number = "<whatsapp_phone_number>"

    def on_message(self, message: MessageEvent):
        req = Message(
            type="text",
            to=message.from_,
            text=Text(
                preview_url=False,
                body="Hello, World!"
            ),
        )
        self.send(req)


def main():
    chat_handler = SimpleChatHandler(debug=False, start_proxy=False)
    chat_handler.start()


if __name__ == "__main__":
    main()
