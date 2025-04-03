import pickle
import os
from dotenv import load_dotenv
from django.core.cache import cache
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.schema import HumanMessage, AIMessage, SystemMessage, Document
from langchain.memory import ConversationSummaryMemory
from qdrant_client import QdrantClient
from langchain.chains.question_answering import load_qa_chain

# Load environment variables
load_dotenv()

# Initialize Gemini model
model = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0.7,
    google_api_key=os.environ.get("GOOGLE_API_KEY"),
)
qa_chain = load_qa_chain(model, chain_type="stuff")

# Function to get similar answers
def get_similar_ans(query, k=5):
    collection_name = "my_collection"
    client = QdrantClient(
        url=os.environ.get("QDRANT_URL"),
        api_key=os.environ.get("QDRANT_API_KEY")
    )

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    query_embedding = embeddings.embed_query(query)

    # Search in Qdrant
    search_results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=k,
    )

    return search_results

# Function to summarize conversation using Gemini
def summarize_conversation(messages):
    """Summarizes conversation history using Gemini."""
    conversation_text = "\n".join([f"{msg.type}: {msg.content}" for msg in messages])

    summary_prompt = (
        "Summarize the following conversation while keeping the key details and context:\n\n"
        f"{conversation_text}\n\n"
        "Provide a concise but detailed summary."
    )

    summary_response = model.invoke(summary_prompt)
    return summary_response.content if summary_response else "No summary available."

# Function to retrieve memory from cache
def get_memory():
    messages_data = cache.get("chat_memory_messages")
    
    memory = ConversationSummaryMemory(
        llm=model,  # Using Gemini to summarize conversations
        return_messages=True
    )

    if messages_data:
        try:
            memory.chat_memory.messages = pickle.loads(messages_data)
        except Exception as e:
            print("Error loading messages from cache:", e)

    # Ensure system message is present
    system_message = SystemMessage(
        content="From now on, you are **Dhruv Sharma**, an interviewer. "
                "You are NOT an AI assistant, NOT a chatbot, and NOT a language model. "
                "Your job is to conduct interviews and answer questions based on the database. "
                "If asked, 'What is your name?', always reply exactly: 'I am Dhruv Sharma, an interviewer.' "
                "If the data is not available, say: 'I don't have that information at the moment.'"
    )

    if not memory.chat_memory.messages or not any(isinstance(msg, SystemMessage) for msg in memory.chat_memory.messages):
        memory.chat_memory.add_message(system_message)

    return memory

# Function to save memory
def save_memory(memory):
    try:
        # Summarize before saving to keep it efficient
        summary = summarize_conversation(memory.chat_memory.messages)
        memory.chat_memory.messages = [SystemMessage(content=summary)]
        
        cache.set("chat_memory_messages", pickle.dumps(memory.chat_memory.messages), timeout=None)
    except Exception as e:
        print("Error saving messages:", e)

# Retrieve memory
memory = get_memory()

# Chatbot function
def chat_boat(user_input):
    memory.chat_memory.add_message(HumanMessage(content=user_input))

    try:
        query_results = get_similar_ans(user_input)
        query_docs = [Document(page_content=str(v.payload)) for v in query_results]

        response = qa_chain.run({
            "input_documents": query_docs,
            "question": memory.chat_memory.messages,
        })
    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        print(error_message)
        return error_message

    memory.chat_memory.add_message(AIMessage(content=str(response)))
    save_memory(memory)  # Save memory to cache

    print("Saved Memory:", pickle.loads(cache.get("chat_memory_messages")))  # Debug stored memory

    return response
