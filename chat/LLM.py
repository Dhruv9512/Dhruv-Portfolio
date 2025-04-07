import os
import pickle
import requests
from dotenv import load_dotenv
from django.core.cache import cache

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage, Document
from langchain.memory import ConversationSummaryMemory
from langchain.chains.question_answering import load_qa_chain
from qdrant_client import QdrantClient

# Load environment variables
load_dotenv()


# ------------------------ Embedding with HuggingFace ------------------------
def embed_query(text):
    HF_API_TOKEN = os.environ.get("HF_API_KEY")
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-mpnet-base-v2",
            headers=headers,
            json={"inputs": text}
        )
        response.raise_for_status()
        embedding = response.json()
        if isinstance(embedding[0], list):  # average token embeddings
            embedding = [sum(col) / len(col) for col in zip(*embedding)]
        return embedding
    except Exception as e:
        print(f"❌ Embedding Error: {e}")
        return None


# ------------------------ LangChain Model Setup ------------------------
model = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0.7,
    google_api_key=os.environ.get("GOOGLE_API_KEY"),
)

qa_chain = load_qa_chain(llm=model, chain_type="stuff")


# ------------------------ Search from Vector DB ------------------------
def get_similar_ans(query, k=5):
    collection_name = "my_collection"
    client = QdrantClient(
        url=os.environ.get("QDRANT_URL"),
        api_key=os.environ.get("QDRANT_API_KEY")
    )

    # Generate embedding using Hugging Face
    query_embedding = embed_query(query)
    if not query_embedding:
        return []

    search_results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=k
    )
    return search_results


# ------------------------ Summarize Memory ------------------------
def summarize_conversation(messages):
    conversation_text = "\n".join([f"{msg.type}: {msg.content}" for msg in messages])
    prompt = (
        "Summarize the following conversation while keeping key details and context:\n\n"
        f"{conversation_text}\n\n"
        "Provide a concise but informative summary."
    )
    response = model.invoke(prompt)
    return response.content if response else "No summary available."


# ------------------------ Get or Create Memory ------------------------
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

    # Add system prompt if not already present
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


# ------------------------ Save Memory After Summary ------------------------
def save_memory(memory):
    try:
        summary = summarize_conversation(memory.chat_memory.messages)
        memory.chat_memory.messages = [SystemMessage(content=summary)]
        cache.set("chat_memory_messages", pickle.dumps(memory.chat_memory.messages), timeout=None)
    except Exception as e:
        print("Error saving memory:", e)


# ------------------------ Main Chat Function ------------------------
def chat_bot(user_input):
    memory = get_memory()

    # Step 1: Count messages
    message_count = cache.get("message_count", 0)
    message_count += 1
    cache.set("message_count", message_count)

    # Step 2: Add user message
    if not memory.chat_memory.messages or memory.chat_memory.messages[-1].content != user_input:
        memory.chat_memory.add_message(HumanMessage(content=user_input))

    try:
        # Step 3: Search similar documents
        query_results = get_similar_ans(user_input)
        query_docs = [Document(page_content=str(hit.payload)) for hit in query_results]

        # Step 4: Chat context
        chat_context = "\n".join(
            [f"{msg.type}: {msg.content}" for msg in memory.chat_memory.messages[-5:]]
        )

        # Step 5: QA Chain
        response = qa_chain.run({
            "input_documents": query_docs,
            "question": chat_context
        })

        # Step 6: Add AI response to memory
        memory.chat_memory.add_message(AIMessage(content=str(response)))  # ← fix for JSON serialization

        # Step 7: Summarize if enough messages
        if message_count >= 5:
            save_memory(memory)
            cache.set("message_count", 0)
        else:
            cache.set("chat_memory_messages", pickle.dumps(memory.chat_memory.messages), timeout=None)

        return str(response)  # ← fix for frontend or API

    except Exception as e:
        print("Error in chat_bot:", e)
        return "Something went wrong while processing your request."
