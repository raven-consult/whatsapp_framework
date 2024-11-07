import os
import inspect
import logging
from functools import wraps
from typing import Tuple, Callable, Iterable, List

import google.generativeai as genai
from google.generativeai.types.model_types import json
from google.protobuf.json_format import MessageToJson, MessageToDict
from google.generativeai.types import GenerateContentResponse, StrictContentType

from whatsapp._datastore import BaseDatastore
from whatsapp._types import BaseInterface, AgentMessage, ConversationData


logger = logging.getLogger(__name__)


def instruction(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Instruction: {func.__name__}")
        return func(*args, **kwargs)

    wrapper._is_instruction = True  # type: ignore
    return wrapper


class AgentInterface(BaseInterface):
    system_message = ""
    datastore: BaseDatastore

    def __init__(
            self,
            gemini_model_name: str = "models/gemini-1.5-flash",
            gemini_api_key: str = os.environ.get("GEMINI_API_KEY", ""),
    ):
        self.model_name = gemini_model_name
        self.instructions = self.get_all_instructions()

        genai.configure(api_key=gemini_api_key)

    def model(self, config=None):
        additional_messages = [
            "\n",
            "Always try to use the tools and minimize use of your own knowledge.",
            "When you have fulfilled a customer request. Please end the chat with <END />",
            "\n",
        ]

        function_definitions = [
            "You have access to the following tools:"
        ]
        functions = self.get_all_instructions()
        for func in functions:
            sig = inspect.signature(func)
            name = func.__name__
            docs = (func.__doc__ or "").strip().replace("\n", " ")
            return_type = sig.return_annotation.__name__

            args = ""
            for arg in sig.parameters.values():
                arg_name = arg.name
                arg_type = arg.annotation.__name__
                args += f"{arg_name}: {arg_type}, "

            function_definitions.append(
                f"{name}({args}) -> {return_type}: {docs}"
            )
        system_instruction = "\n".join(
            [self.system_message]
            + function_definitions
            + additional_messages
        )

        return genai.GenerativeModel(
            tools=self.instructions,
            model_name=self.model_name,
            system_instruction=system_instruction,
        )

    def _setup_history_data(self, history_data: List[AgentMessage]) -> Iterable[StrictContentType]:
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

    def handler(self, conversation: ConversationData, message: str) -> Tuple[str, bool]:
        """Handle the chat messages and return the response and whether the chat has ended."""

        model = self.model()
        history_data = self.datastore.get_agent_messages(conversation.id)
        history = self._setup_history_data(history_data)
        session = model.start_chat(history=history)

        self.datastore.add_agent_message(
            type="text",
            data=message,
            sender="customer",
            conversation_id=conversation.id,
        )

        response = ""
        end_chat = False
        end_loop = False
        function_call_response = None

        while not end_loop:
            if function_call_response:
                res = session.send_message(function_call_response)
            else:
                res = session.send_message(message)

            fns, response, end_loop, end_chat = self._process_response(
                conversation.id, res)

            function_call_response = []
            for fn in fns:
                res_part = self._call_function(fn)
                function_call_response.append(res_part)

            if function_call_response:
                # Save responses to history
                responses_json = [MessageToDict(r._pb)
                                  for r in function_call_response]  # type: ignore

                self.datastore.add_agent_message(
                    sender="customer",
                    type="function_response",
                    data=json.dumps(responses_json),
                    conversation_id=conversation.id,
                )
        return response, end_chat

    def _call_function(self, fn):
        # Call the function and get the response
        func = getattr(self, fn.name)
        res = func(**fn.args)

        # Build the response parts.
        res_part = genai.protos.Part(function_response=genai.protos.FunctionResponse(
            name=fn.name, response={"result": res}))

        return res_part

    def _process_response(self, conversation_id: str, res: GenerateContentResponse):
        fns = []
        response = ""
        end_chat = False
        end_loop = False

        for part in res.parts:
            if part.function_call:
                fn = part.function_call
                args = ", ".join(f"{key}={val}" for key,
                                 val in fn.args.items())
                logger.debug(
                    f"Model declared a function call: {fn.name}({args})")
                fns.append(fn)
                response = MessageToJson(part._pb)

                self.datastore.add_agent_message(
                    sender="bot",
                    data=response,
                    type="function_call",
                    conversation_id=conversation_id,
                )
            else:
                response = part.text
                response = response.strip()

                end_loop = True

                if "<END />" in response:
                    end_chat = True
                    response = response.replace("<END />", "")

                self.datastore.add_agent_message(
                    type="text",
                    sender="bot",
                    data=response,
                    conversation_id=conversation_id,
                )
        return fns, response, end_loop, end_chat

    def get_all_instructions(self) -> List[Callable]:
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
