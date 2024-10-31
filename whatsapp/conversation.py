from functools import wraps
from contextlib import contextmanager

from whatsapp._history import ConversationHistory


def instruction(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("Instruction: ", func.__name__)
        return func(*args, **kwargs)
    return wrapper


class Conversation(object):
    def __init__(self, conversation_id: str):
        self.history = ConversationHistory(conversation_id)

    def handler(self, chat_id, message: str):
        response = "Hello"
        if message == "end":
            response = "Goodbye"
        self.history.insert_message(chat_id, "user", message)
        self.history.insert_message(chat_id, "bot", response)
        return response

    @contextmanager
    def start_chat(self, chat_id: str):
        handler = self.get_chat(chat_id)

        try:
            print("Chat started")
            yield handler
        finally:
            print("Chat ended")

    def get_chat(self, chat_id: str):
        def chat(message: str):
            return self.handler(chat_id, message)

        return chat
