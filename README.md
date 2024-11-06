# Whatsapp Framework

**Whatsapp Framework** helps you quickly build and deploy whatsapp chatbots in python.


## Get started

```bash
pip install whatsapp-framework
```

## Example Usage

Here's a basic example of how to use Whatsapp Framework:

```python
from datetime import datetime
from whatsapp import Conversation, instruction


class TimeCheckerBot(Conversation):
    token = "<whatsapp_admin_token>"
    whatsapp_number = "<whatsapp_number>"

    system_message = (
        "You are helpful conversation assistant for casual chat."
    )

    @instruction
    def check_time(self):
        current_time = datetime.now().strftime('%H:%M:%S')
        return f"The current time is {current_time}"

def main():
    chat_handler = RestaurantAttendantConversation(
        debug=True, start_proxy=True,
        gemini_model_name="models/gemini-1.5-flash",
    )
    chat_handler.start(5000)


if __name__ == "__main__":
    main()
```

## License

Whatsapp Framework is licensed under the [MIT License](LICENSE). See the [LICENSE](LICENSE) file for details.

## Contact

If you have any questions or need support, please open an issue on [GitHub Issues](https://github.com/raven-consult/whatsapp_framework/issues) or contact us at [support@ravenconsulting.site](mailto:support@ravenconsulting.site).
