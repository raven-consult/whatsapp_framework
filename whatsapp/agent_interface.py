import os
import logging
from typing import Iterable
from functools import wraps
from contextlib import contextmanager

import google.generativeai as genai
from google.generativeai.types.model_types import json
from google.generativeai.types import StrictContentType
from google.protobuf.json_format import MessageToJson, MessageToDict

from whatsapp._history import Message, ConversationHistory

logger = logging.getLogger(__name__)


def instruction(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Instruction: {func.__name__}")
        return func(*args, **kwargs)

    wrapper._is_instruction = True  # type: ignore
    return wrapper


class AgentInterface(object):
    system_message = ""

    def __init__(
            self,
            gemini_model_name: str = "models/gemini-1.5-flash",
            gemini_api_key: str = os.environ.get("GEMINI_API_KEY", ""),
    ):
        self.model_name = gemini_model_name
        genai.configure(api_key=gemini_api_key)
        self.instructions = self.get_all_instructions()
        self.history = ConversationHistory("djdk")

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
        history_data = self.history.get_messages(chat_id)

        response = ""
        history: Iterable[StrictContentType] = []

        for m in history_data:
            if m.type == "text":
                history.append({
                    "role": "user" if m.sender == "user" else "model",
                    "parts": [genai.protos.Part(text=m.data)],
                })
            elif m.type == "function_call":
                function_call = json.loads(m.data)["functionCall"]
                history.append({
                    "role": "user" if m.sender == "user" else "model",
                    "parts": [genai.protos.Part(function_call=genai.protos.FunctionCall(
                        name=function_call["name"], args=function_call["args"]))]
                })
            elif m.type == "function_response":
                function_response = json.loads(m.data)
                history.append({
                    "role": "user" if m.sender == "user" else "model",
                    "parts": [genai.protos.Part(function_response=genai.protos.FunctionResponse(
                        name=f["functionResponse"]["name"], response=f["functionResponse"]["response"])) for f in function_response]
                })

        session = model.start_chat(history=history)
        self.history.insert_message(
            Message(
                type="text",
                data=message,
                sender="user",
                chat_id=chat_id,
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
                    logger.debug(f"Function call: {fn.name}({args})")
                    fns.append(fn)
                    response = MessageToJson(part._pb)

                    self.history.insert_message(
                        Message(
                            sender="bot",
                            data=response,
                            chat_id=chat_id,
                            type="function_call",
                        )
                    )
                else:
                    response = part.text
                    end_loop = True
                    self.history.insert_message(
                        Message(
                            type="text",
                            sender="bot",
                            data=response,
                            chat_id=chat_id,
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

            if responses:
                message_json = [MessageToDict(r._pb)
                                for r in responses]  # type: ignore
                self.history.insert_message(
                    Message(
                        sender="user",
                        chat_id=chat_id,
                        type="function_response",
                        data=json.dumps(message_json)
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
                logger.debug(f"Instruction: {attr}")
                func = getattr(self, attr)
                instructions.append(func)

        return instructions

    @contextmanager
    def start_chat(self, chat_id: str):
        handler = self.get_chat(chat_id)

        try:
            logger.debug("Chat started")
            yield handler
        finally:
            logger.debug("Chat ended")

    def get_chat(self, chat_id: str):
        def chat(message: str):
            return self.handler(chat_id, message)

        return chat
