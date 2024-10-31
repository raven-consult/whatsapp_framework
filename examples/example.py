from whatsapp import Conversation, instruction


system_message = "You are helpful web search bot. You can help me search the web for information."


class EchoConversation(Conversation):
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


conversation = EchoConversation("1234",
                                system_message=system_message,
                                )

with conversation.start_chat("hello") as chat:
    while True:
        message = input("Enter your message: ")
        response = chat(message)

        print(response)

        if response == "Goodbye":
            break
