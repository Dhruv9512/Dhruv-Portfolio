import pickle
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage, Document
import os
from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory
from django.core.cache import cache
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient
from langchain.chains.question_answering import load_qa_chain

# Load environment variables
load_dotenv()

# Create model
model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
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

# Function to retrieve memory from cache
def get_memory():
    """Retrieve or create memory from cache"""
    messages_data = cache.get("chat_memory_messages")
    memory = ConversationBufferMemory(return_messages=True)

    if messages_data:
        try:
            messages = pickle.loads(messages_data)
            memory.chat_memory.messages = messages
        except Exception as e:
            print("Error loading messages from cache:", e)

    # ✅ Ensure system message is always present
    system_message = SystemMessage(
       content="From now on, you are **Dhruv Sharma**, an interviewer. "
                    "You are NOT an AI assistant, NOT a chatbot, and NOT a language model. "
                    "Your job is to conduct interviews and answer questions based on the database. "
                    "You respond only with factual information available in the database. "
                    "If asked, 'What is your name?', always reply exactly: 'I am Dhruv Sharma, an interviewer.' "
                    "If the data is not available, say: 'I don't have that information at the moment.'"
    )
    
    if not memory.chat_memory.messages or not any(isinstance(msg, SystemMessage) for msg in memory.chat_memory.messages):
        memory.chat_memory.add_message(system_message)

    return memory

# Function to save memory
def save_memory(memory):
    """Save updated memory to cache"""
    try:
        cache.set("chat_memory_messages", pickle.dumps(memory.chat_memory.messages), timeout=None)
    except Exception as e:
        print("Error saving messages:", e)

# Retrieve memory
memory = get_memory()

# Chatbot function
def chat_boat(user_input):
    """Processes user input and returns chatbot response"""
    
    print("Before Adding User Message:", memory.chat_memory.messages)
    memory.chat_memory.add_message(HumanMessage(content=user_input))
    print("After Adding User Message:", memory.chat_memory.messages)

    try:
        quary = get_similar_ans(user_input)
        quary = [Document(page_content=str(v.payload)) for v in quary]
        
        # Format chat history for better AI understanding
        chat_history = "\n".join([msg.content for msg in memory.chat_memory.messages])

        # Get response from model
        response = qa_chain.run({
            "input_documents": quary, 
            "question": user_input, 
            "context": chat_history
        })

        # ✅ **Force identity in every response**
        response = f"I am Dhruv Sharma. {response}"

    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        print(error_message)
        return error_message

    # Add response to memory
    memory.chat_memory.add_message(AIMessage(content=str(response)))
    save_memory(memory)  # ✅ Ensure memory is saved properly

    print("Saved Memory:", pickle.loads(cache.get("chat_memory_messages")))  # Debug stored memory

    return response

