from langchain.schema.messages import HumanMessage, SystemMessage
from ..routes.chatbot import query_chatbot


messages = [
    SystemMessage(
        content="""You're an assistant knowledgeable about
        economics. Only answer economic-related questions."""
    ),
]

def get_response(human_messages):
    print(human_messages)

    messages.append(HumanMessage(content=human_messages))
    response = query_chatbot(messages)
    return response

