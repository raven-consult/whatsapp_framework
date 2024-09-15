# Whatsapp Framework

**Whatsapp Framework** framework simplifies building and deploying whatsapp based applications.

## Installation

```bash
pip install whatsapp-framework
```

## Example Usage

Here's a basic example of how to use Whatsapp Framework:

```python
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
    chat_handler = SimpleChatHandler()
    chat_handler.start()


if __name__ == "__main__":
    main()
```

## License

Whatsapp Framework is licensed under the [MIT License](LICENSE). See the [LICENSE](LICENSE) file for details.

## Contact

If you have any questions or need support, please open an issue on [GitHub Issues](https://github.com/raven-consult/whatsapp_framework/issues) or contact us at [support@ravenconsulting.site](mailto:support@ravenconsulting.site).
