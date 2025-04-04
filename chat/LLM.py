import os
import pickle
from dotenv import load_dotenv
from django.core.cache import cache
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.schema import HumanMessage, AIMessage, SystemMessage, Document
from langchain_community.chat_message_histories import ChatMessageHistory
from qdrant_client import QdrantClient
from langchain.chains.combine_documents.stuff import create_stuff_documents_chain
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()

# Initialize Gemini model
model = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0.7,
    google_api_key=os.environ.get("GOOGLE_API_KEY"),
)

# Define QA Prompt
qa_prompt = PromptTemplate.from_template(
    "Use the following context to answer the question:\n\n{context}\n\nQuestion: {question}"
)

# Create QA Chain
qa_chain = create_stuff_documents_chain(llm=model, prompt=qa_prompt)

# Initialize Chat Memory
memory = ChatMessageHistory()

# Function to get similar answers
def get_similar_ans(query, k=5):
    collection_name = "my_collection"
    client = QdrantClient(
        url=os.environ.get("QDRANT_URL"),
        api_key=os.environ.get("QDRANT_API_KEY")
    )

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    try:
        query_embedding = embeddings.embed_query(query)
    except Exception as e:
        print(f"Embedding error: {e}")
        return []

    # Search in Qdrant
    search_results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=k,
    )

    return search_results

# Function to retrieve memory from cache
def get_memory():
    messages_data = cache.get("chat_memory_messages")

    if messages_data:
        try:
            memory.messages = pickle.loads(messages_data)
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

    if not memory.messages or not any(isinstance(msg, SystemMessage) for msg in memory.messages):
        memory.add_message(system_message)

# Function to save memory
def save_memory():
    try:
        cache.set("chat_memory_messages", pickle.dumps(memory.messages), timeout=None)
    except Exception as e:
        print("Error saving messages:", e)

# Retrieve memory
get_memory()

# Chatbot function
def chat_bot(user_input):
    memory.add_message(HumanMessage(content=user_input))

    try:
        query_results = get_similar_ans(user_input)

        # Extract relevant text content from search results
        query_docs = []
        for v in query_results:
            if isinstance(v.payload, dict):
                content = "\n".join([f"{key}: {value}" for key, value in v.payload.items() if key != "source_file"])
                query_docs.append(Document(page_content=content, metadata={"source": v.payload.get("source_file", "unknown")}))


        # Call QA Chain with properly formatted inputs
        response = qa_chain.invoke({
            "context": query_docs,  
            "question": str(memory.messages),  
        })

    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        print(error_message)
        return error_message

    # Save AI response to memory
    memory.add_message(AIMessage(content=str(response)))
    save_memory()  

    return response
