import os
import pickle
from dotenv import load_dotenv
from django.core.cache import cache

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage, Document
from langchain.memory import ConversationSummaryMemory
from langchain.chains.question_answering import load_qa_chain
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

# Initialize Gemini model
model = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0.7,
    google_api_key=os.environ.get("GOOGLE_API_KEY"),
)

# Initialize QA Chain
qa_chain = load_qa_chain(llm=model, chain_type="stuff")

# Initialize SentenceTransformer model
sentence_model = SentenceTransformer("all-mpnet-base-v2")

# Function: Get similar answers using Qdrant and sentence-transformers
def get_similar_ans(query, k=5):
    collection_name = "my_collection"
    client = QdrantClient(
        url=os.environ.get("QDRANT_URL"),
        api_key=os.environ.get("QDRANT_API_KEY")
    )

    # Generate embedding using SentenceTransformer
    query_embedding = sentence_model.encode(query).tolist()

    search_results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=k
    )
    return search_results

# Function: Summarize the conversation
def summarize_conversation(messages):
    conversation_text = "\n".join([f"{msg.type}: {msg.content}" for msg in messages])
    prompt = (
        "Summarize the following conversation while keeping key details and context:\n\n"
        f"{conversation_text}\n\n"
        "Provide a concise but informative summary."
    )
    response = model.invoke(prompt)
    return response.content if response else "No summary available."

# Function: Retrieve memory
def get_memory():
    memory = ConversationSummaryMemory(
        llm=model,
        return_messages=True
    )

    messages_data = cache.get("chat_memory_messages")
    if messages_data:
        try:
            memory.chat_memory.messages = pickle.loads(messages_data)
        except Exception as e:
            print("Error loading cached messages:", e)

    # Ensure system prompt is present
    if not memory.chat_memory.messages or not any(isinstance(msg, SystemMessage) for msg in memory.chat_memory.messages):
        system_message = SystemMessage(
            content=(
                "You are an intelligent assistant chatbot named Mitsuha.\n"
                "If asked, 'What is your name?', reply exactly: 'I am Dhruv Sharma, an assistant.'\n"
                "You are also known as Mitsuha.\n"
                "If you don’t know something, say: 'I don't have that information at the moment.'"
            )
        )
        memory.chat_memory.add_message(system_message)

    return memory

# Function: Save memory (after summarizing)
def save_memory(memory):
    try:
        summary = summarize_conversation(memory.chat_memory.messages)
        memory.chat_memory.messages = [SystemMessage(content=summary)]
        cache.set("chat_memory_messages", pickle.dumps(memory.chat_memory.messages), timeout=None)
    except Exception as e:
        print("Error saving memory:", e)

# Main chatbot function
def chat_bot(user_input):
    memory = get_memory()

    # Add user's message to memory
    memory.chat_memory.add_message(HumanMessage(content=user_input))

    try:
        # Get relevant documents from vector DB
        query_results = get_similar_ans(user_input)
        query_docs = [Document(page_content=str(hit.payload)) for hit in query_results]

        # Run QA chain with latest input
        response = qa_chain.run({
            "input_documents": query_docs,
            "question": memory.chat_memory.messages
        })

        # Add bot's response to memory
        memory.chat_memory.add_message(AIMessage(content=str(response)))

        # Save updated memory
        save_memory(memory)

        return response

    except Exception as e:
        print("Error in chat_bot:", e)
        return "Something went wrong while processing your request."
