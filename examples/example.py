from whatsapp import Conversation, instruction


class EchoConversation(Conversation):
    @instruction
    def search_the_web(self, message: str) -> str:
        return "I can help you with that. What would you like me to search for?"


conversation = EchoConversation("1234")

with conversation.start_chat("hello") as chat:
    while True:
        message = input("Enter your message: ")
        response = chat(message)

        print(response)

        if response == "Goodbye":
            break
