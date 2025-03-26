from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage , AIMessage , SystemMessage
from django.contrib.sessions.models import Session
import time
import os
from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory
from django.core.cache import cache
from django.http import JsonResponse

# load env
load_dotenv()

# create model
model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash", 
    temperature=0.6,
    google_api_key = os.environ.get("GOOGLE_API_KEY")
)

# create memory
def get_memory():
    """Retrieve or create memory from cache"""
    memory = cache.get("chat_memory")
    if memory is None:
        memory = ConversationBufferMemory(return_messages=True)
        cache.set("chat_memory", memory, timeout=None)  # Store in cache permanently
    return memory

def save_memory(memory):
    """Save updated memory to cache"""
    cache.set("chat_memory", memory, timeout=None)

memory = get_memory()
#  Add a system message
memory.chat_memory.add_message(SystemMessage(content="Hello, I am a chatbot. How can I help you?"))
# create chatbot that predict the output
def chat_boat(user_input):
    # add user message to memory
    memory.chat_memory.add_message(HumanMessage(content=user_input))
    # get response from model
    response = model.invoke(memory.chat_memory.messages)
    # add response to memory
    memory.chat_memory.add_message(AIMessage(content=str(response.content)))
    save_memory(memory)

    return response.content