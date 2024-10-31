from functools import wraps
from contextlib import contextmanager

import os
import google.generativeai as genai

from whatsapp._history import ConversationHistory


def instruction(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("Instruction: ", func.__name__)
        return func(*args, **kwargs)

    wrapper._is_instruction = True  # type: ignore
    return wrapper


class Conversation(object):
    def __init__(
            self,
            conversation_id: str,
            system_message="",
            gemini_model_name: str = "gemini-1.5-flash",
            gemini_api_key: str = os.environ.get("GEMINI_API_KEY", ""),
    ):
        self.model_name = gemini_model_name
        self.system_message = system_message
        genai.configure(api_key=gemini_api_key)
        self.instructions = self.get_all_instructions()
        self.history = ConversationHistory(conversation_id)

    def model(self):
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }

        return genai.GenerativeModel(
            tools=self.instructions,
            model_name=self.model_name,
            generation_config=generation_config,  # type: ignore
            system_instruction=self.system_message,
        )

    def handler(self, chat_id, message: str):
        response = "Hello"
        if message == "end":
            response = "Goodbye"
        self.history.insert_message(chat_id, "user", message)
        self.history.insert_message(chat_id, "bot", response)
        return response

    def get_all_instructions(self):
        instructions = []
        for attr in dir(self):
            is_callable = callable(getattr(self, attr))
            is_instruction = getattr(
                getattr(self, attr), "_is_instruction", False)

            if is_callable and is_instruction:
                print("Instruction: ", attr)
                instructions.append(attr)

        return instructions

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
