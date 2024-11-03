# Whatsapp Framework

**Whatsapp Framework** simplifies building and deploying whatsapp based applications.

## Installation

```bash
pip install whatsapp-framework
```

## Example Usage

Here's a basic example of how to use Whatsapp Framework:

```python
from whatsapp.events import Message
from whatsapp.chat import ChatHandler
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
    chat_handler.start()


if __name__ == "__main__":
    main()
```

## License

Whatsapp Framework is licensed under the
[MIT License](https://github.com/raven-consult/whatsapp-framework/blob/master/LICENSE).
See the [LICENSE](https://github.com/raven-consult/whatsapp-framework/blob/master/LICENSE)
file for details.

## Contact

If you have any questions or need support, please open an issue on [GitHub Issues](https://github.com/raven-consult/whatsapp_framework/issues) or contact us at [support@ravenconsulting.site](mailto:support@ravenconsulting.site).
