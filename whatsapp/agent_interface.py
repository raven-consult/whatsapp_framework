import os
import logging
from functools import wraps
from dataclasses import dataclass
from contextlib import contextmanager
from typing import Iterable, List, Literal

import google.generativeai as genai
from google.generativeai.types.model_types import json
from google.protobuf.json_format import MessageToJson, MessageToDict
from google.generativeai.types import GenerateContentResponse, StrictContentType

from whatsapp._types import BaseInterface


logger = logging.getLogger(__name__)

MessageTypes = Literal["text", "function_call", "function_response"]


@dataclass
class Message:
    chat_id: int
    sender: str
    data: str
    id: int | None = None
    type: MessageTypes = "text"


def instruction(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Instruction: {func.__name__}")
        return func(*args, **kwargs)

    wrapper._is_instruction = True  # type: ignore
    return wrapper


class AgentInterface(BaseInterface):
    system_message = ""

    def __init__(
            self,
            gemini_model_name: str = "models/gemini-1.5-flash",
            gemini_api_key: str = os.environ.get("GEMINI_API_KEY", ""),
    ):
        self.model_name = gemini_model_name
        self.instructions = self.get_all_instructions()

        genai.configure(api_key=gemini_api_key)
        self.create_table()

    def model(self, config=None):
        return genai.GenerativeModel(
            tools=self.instructions,
            model_name=self.model_name,
            system_instruction=self.system_message,
        )

    def _setup_history_data(self, history_data: List[Message]) -> Iterable[StrictContentType]:
        """Converts conversation history into a structured format for the model."""

        history = []
        for message in history_data:
            role = "user" if message.sender == "user" else "model"
            if message.type == "text":
                history.append(
                    {"role": role, "parts": [genai.protos.Part(text=message.data)]})
            elif message.type == "function_call":
                function_call = json.loads(message.data)["functionCall"]
                history.append({
                    "role": role,
                    "parts": [genai.protos.Part(function_call=genai.protos.FunctionCall(
                        name=function_call["name"], args=function_call["args"]
                    ))]
                })
            elif message.type == "function_response":
                function_responses = json.loads(message.data)
                parts = [
                    genai.protos.Part(function_response=genai.protos.FunctionResponse(
                        name=resp["functionResponse"]["name"], response=resp["functionResponse"]["response"]
                    )) for resp in function_responses
                ]
                history.append({"role": role, "parts": parts})
        return history

    def create_table(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        logging.debug("Creating table")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                type TEXT NOT NULL,
                sender TEXT NOT NULL,
                data TEXT NOT NULL
            )
            """
        )
        conn.commit()

    def insert_message(self, message: Message):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO messages
                (conversation_id, type, sender, data)
                VALUES (?, ?, ?, ?)
                """,
                (
                    message.chat_id,
                    message.type,
                    message.sender,
                    message.data,
                )
            )
            conn.commit()
        except Exception as e:
            logging.error(e)
            raise e

    def get_messages(self, chat_id: str):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, conversation_id, type, sender, data
            FROM messages
            WHERE conversation_id=?
            """,
            (chat_id,),
        )
        res = cursor.fetchall()

        return [
            Message(
                id=r[0],
                chat_id=r[1],
                type=r[2],
                sender=r[3],
                data=r[4],
            ) for r in res
        ]

    def handler(self, chat_id, message: str):
        model = self.model()
        history_data = self.get_messages(chat_id)
        history = self._setup_history_data(history_data)
        session = model.start_chat(history=history)

        self.insert_message(
            Message(
                type="text",
                data=message,
                sender="user",
                chat_id=chat_id,
            )
        )

        response = ""
        end_loop = False
        function_call_response = None

        while not end_loop:
            if function_call_response:
                res = session.send_message(function_call_response)
            else:
                res = session.send_message(message)

            fns, response, end_loop = self._process_response(chat_id, res)

            if any(fn.name == "end_chat" for fn in fns):
                break

            function_call_response = []
            for fn in fns:
                res_part = self._call_function(fn)
                function_call_response.append(res_part)

            if function_call_response:
                # Save responses to history
                responses_json = [MessageToDict(r._pb)
                                  for r in function_call_response]  # type: ignore
                self.insert_message(
                    Message(
                        sender="user",
                        chat_id=chat_id,
                        type="function_response",
                        data=json.dumps(responses_json)
                    )
                )

        return response

    def _call_function(self, fn):
        # Call the function and get the response
        func = getattr(self, fn.name)
        res = func(**fn.args)

        # Build the response parts.
        res_part = genai.protos.Part(function_response=genai.protos.FunctionResponse(
            name=fn.name, response={"result": res}))

        return res_part

    def _process_response(self, chat_id: int, res: GenerateContentResponse):
        fns = []
        response = ""
        end_loop = False

        for part in res.parts:
            if part.function_call:
                fn = part.function_call
                args = ", ".join(f"{key}={val}" for key,
                                 val in fn.args.items())
                logger.debug(
                    f"Model declare a function call: {fn.name}({args})")
                fns.append(fn)
                response = MessageToJson(part._pb)

                self.insert_message(
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
                self.insert_message(
                    Message(
                        type="text",
                        sender="bot",
                        data=response,
                        chat_id=chat_id,
                    )
                )
        return fns, response, end_loop

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