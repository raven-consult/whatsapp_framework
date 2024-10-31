from functools import wraps
from contextlib import contextmanager


def instruction(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("Instruction: ", func.__name__)
        return func(*args, **kwargs)
    return wrapper


class Conversation(object):
    def __init__(self) -> None:
        pass

    @contextmanager
    def start_chat(self, chat_id: str):
        def handler(message: str):
            if message == "end":
                return "Goodbye"
            return "Hello"

        try:
            print("Chat started")
            yield handler
        finally:
            print("Chat ended")

    def get_chat(self, chat_id: str):
        def handler(message: str):
            return "Hello"

        return handler


class EchoConversation(Conversation):

    @instruction
    def search_the_web(self, message: str) -> str:
        return "I can help you with that. What would you like me to search for?"


conversation = EchoConversation()

with conversation.start_chat("hello") as chat:
    while True:
        message = input("Enter your message: ")
        response = chat(message)

        print(response)

        if response == "Goodbye":
            break
