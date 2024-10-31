from functools import wraps
from contextlib import contextmanager

import os
import google.generativeai as genai
from google.protobuf.json_format import MessageToJson, MessageToDict

from whatsapp._history import Message, ConversationHistory


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
            system_message: str | None = None,
            gemini_model_name: str = "models/gemini-1.5-flash",
            gemini_api_key: str = os.environ.get("GEMINI_API_KEY", ""),
    ):
        self.model_name = gemini_model_name
        self.system_message = system_message
        genai.configure(api_key=gemini_api_key)
        self.instructions = self.get_all_instructions()
        self.history = ConversationHistory(conversation_id)

    def model(self):
        generation_config = {
            "top_k": 64,
            "top_p": 0.95,
            "temperature": 1,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }

        return genai.GenerativeModel(
            tools=self.instructions,
            model_name=self.model_name,
            system_instruction=self.system_message,
        )

    def handler(self, chat_id, message: str):
        model = self.model()
        history = self.history.get_messages(chat_id)

        response = ""
        if message == "end":
            response = "Goodbye"

        session = model.start_chat(
            history=[
                {
                    "role": "user" if m.sender == "user" else "model",
                    "parts": [m.message],
                } for m in history
            ]
        )

        self.history.insert_message(
            Message(
                chat_id=chat_id,
                sender="user",
                message=message,
            )
        )

        responses = None
        end_loop = False
        while not end_loop:
            if responses:
                res = session.send_message(responses)
            else:
                res = session.send_message(message)

            fns = []
            for part in res.parts:
                if part.function_call:
                    fn = part.function_call
                    args = ", ".join(f"{key}={val}" for key,
                                     val in fn.args.items())
                    print(f"{fn.name}({args})")
                    fns.append(fn)
                    response = MessageToJson(part._pb)

                    self.history.insert_message(
                        Message(
                            chat_id=chat_id,
                            sender="bot",
                            message=response,
                        )
                    )
                else:
                    response = part.text
                    end_loop = True
                    self.history.insert_message(
                        Message(
                            chat_id=chat_id,
                            sender="bot",
                            message=response,
                        )
                    )

            if any(fn.name == "end_chat" for fn in fns):
                break

            responses = []

            for fn in fns:
                func = getattr(self, fn.name)
                res = func(**fn.args)

                # Build the response parts.
                res_part = genai.protos.Part(function_response=genai.protos.FunctionResponse(
                    name=fn.name, response={"result": res}))

                responses.append(res_part)

            message_json = [MessageToDict(r._pb)
                            for r in responses]  # type: ignore

            self.history.insert_message(
                Message(
                    sender="user",
                    chat_id=chat_id,
                    message=str(message_json)
                )
            )

        return response

    def get_all_instructions(self):
        instructions = []
        for attr in dir(self):
            is_callable = callable(getattr(self, attr))
            is_instruction = getattr(
                getattr(self, attr), "_is_instruction", False)

            if is_callable and is_instruction:
                print("Instruction: ", attr)
                func = getattr(self, attr)
                instructions.append(func)

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
