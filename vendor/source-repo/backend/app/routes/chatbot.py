import dotenv
from langchain_openai import ChatOpenAI
import os
import markdown  # Convert Markdown to HTML

dotenv.load_dotenv()

chat_model = ChatOpenAI(
    model="gpt-3.5-turbo", 
    temperature=0, 
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

def query_chatbot(messages):
    try:
        response = chat_model.invoke(messages)
        html_response = markdown.markdown(response.content)  # Convert Markdown to HTML
        return html_response
    except Exception as e:
        return str(e)
