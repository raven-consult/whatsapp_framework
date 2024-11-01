from textwrap import dedent
from whatsapp import Conversation, instruction


class EchoConversation(Conversation):
    system_message = dedent("""\
You are helpful web search bot. You can help me search the web for information.
Use the tools provided to you **only** when neccessary, if you have access to the data in your context, use that and answer the question
""")

    @instruction
    def search_the_web(self, message: str):
        """Search the web for the size of Unilag super bowl.

        Args:
            query: The query to search for.

        Returns:
            A dictionary containing the search results.
        """
        return {
            "message": "The size of Unilag super bowl is 530 by 300 meters and it has a seating capacity of 24,325.",
        }


conversation = EchoConversation(
    "1234",
    gemini_model_name="models/gemini-1.5-flash",
)

with conversation.start_chat("hello") as chat:
    while True:
        message = input("Enter your message: ")
        response = chat(message)

        print(response)

        if response == "Goodbye":
            break
