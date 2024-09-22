from whatsapp.chat import ChatHandler
from whatsapp.events import Message
from whatsapp.reply_message import Message as ReplyMessage, Text


class SimpleChatHandler(ChatHandler):
    token = "<whatsapp_access_token>"
    whatsapp_number = "<whatsapp_phone_number>"

    def on_message(self, message: Message):
        message_type = message.type
        file = message.message.file
        name = message.contacts[0].profile.name

        req = ReplyMessage(
            type="text",
            to=message.to,
            text=Text(
                preview_url=False,
                body=f"""
Hello, {name}!

I received a {message_type} from you.
I've saved it as {file}.
"""
            ),
        )
        self.send(req)


def main():
    chat_handler = SimpleChatHandler(debug=True, start_proxy=False)
    chat_handler.start(5000)


if __name__ == "__main__":
    main()
