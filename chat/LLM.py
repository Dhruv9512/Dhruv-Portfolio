# import os
# import pickle
# import requests
# import time
# from dotenv import load_dotenv
# from django.core.cache import cache

# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain.schema import HumanMessage, AIMessage, SystemMessage, Document
# from langchain.memory import ConversationSummaryMemory
# from langchain.chains.question_answering import load_qa_chain
# from qdrant_client import QdrantClient

# # Load environment variables
# load_dotenv()

# # Initialize Gemini model (used only for QA, not summarization)
# model = ChatGoogleGenerativeAI(
#     model="gemini-1.5-pro",
#     temperature=0.7,
#     google_api_key=os.environ.get("GOOGLE_API_KEY"),
# )

# # Initialize QA Chain
# qa_chain = load_qa_chain(llm=model, chain_type="stuff")

# # Function: Generate vector for user input using Hugging Face API
# def embed_query(text):
#     HF_API_KEY = os.environ.get("HF_API_KEY")
#     headers = {"Authorization": f"Bearer {HF_API_KEY}"}
#     url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-mpnet-base-v2"

#     for attempt in range(5):  # Retry logic for 503 errors
#         try:
#             response = requests.post(url, headers=headers, json={"inputs": text}, timeout=10)
#             response.raise_for_status()
#             embedding = response.json()
#             if isinstance(embedding[0], list):
#                 embedding = [sum(col) / len(col) for col in zip(*embedding)]
#             return embedding
#         except requests.exceptions.RequestException as e:
#             print(f"[Attempt {attempt+1}] ❌ Embedding Error: {e}")
#             if response.status_code in [500, 503]:
#                 time.sleep(2)  # Wait and retry
#             else:
#                 break
#         except Exception as e:
#             print("❌ Failed to parse embedding:", e)
#             break

#     # Fallback: Return a zero vector if embedding generation fails
#     print("❌ Embedding generation failed. Returning a zero vector as fallback.")
#     return [0.0] * 768

# # Function: Get similar answers using Qdrant
# def get_similar_ans(query, k=5):
#     collection_name = "my_collection"
#     client = QdrantClient(
#         url=os.environ.get("QDRANT_URL"),
#         api_key=os.environ.get("QDRANT_API_KEY")
#     )

#     query_embedding = embed_query(query)
#     if not query_embedding:
#         print("Failed to generate query embedding.")
#         return []

#     try:
#         search_results = client.search(
#             collection_name=collection_name,
#             query_vector=query_embedding,
#             limit=k
#         )
#         return search_results
#     except Exception as e:
#         print(f"Error with Qdrant API: {e}")
#         return []

# # ✅ Function: Summarize the conversation using Hugging Face
# def summarize_conversation(messages):
#     HF_API_KEY = os.environ.get("HF_API_KEY")
#     if not HF_API_KEY:
#         print("❌ Hugging Face API key is missing.")
#         return get_fallback_summary(messages, reason="missing API key")

#     headers = {"Authorization": f"Bearer {HF_API_KEY}"}

#     conversation_text = "\n".join([f"{msg.type}: {msg.content}" for msg in messages])
#     input_text = conversation_text[:1024]  # Optional truncation

#     try:
#         response = requests.post(
#             "https://api-inference.huggingface.co/models/facebook/bart-large-cnn",
#             headers=headers,
#             json={"inputs": input_text},
#             timeout=15
#         )
#         print("📨 Raw response text:", response.text)  # For debugging
#         response.raise_for_status()
#         result = response.json()

#         # ✅ Handle different formats
#         if isinstance(result, list) and result and "summary_text" in result[0]:
#             return result[0]["summary_text"]
#         elif isinstance(result, dict) and "summary_text" in result:
#             return result["summary_text"]
#         else:
#             print("⚠️ Unexpected Hugging Face response format:", result)
#             return get_fallback_summary(messages, reason="unexpected response")

#     except requests.exceptions.RequestException as e:
#         print(f"🚨 Request error with Hugging Face API: {e}")
#         return get_fallback_summary(messages, reason="network/API error")

#     except ValueError as e:
#         print(f"🚨 JSON parsing error from Hugging Face API: {e}")
#         return get_fallback_summary(messages, reason="response parsing error")

# # 🔁 Helper Function: Fallback Summary
# def get_fallback_summary(messages, reason="unknown"):
#     first_user_msg = next(
#         (msg.content for msg in messages if isinstance(msg, HumanMessage)),
#         "No user message available."
#     )
#     return f"Summary not available due to {reason}. But your first question was:\n\n➡️ **{first_user_msg}**"

# # Function: Retrieve memory
# def get_memory():
#     memory = ConversationSummaryMemory(
#         llm=model,
#         return_messages=True
#     )

#     messages_data = cache.get("chat_memory_messages")
#     if messages_data:
#         try:
#             memory.chat_memory.messages = pickle.loads(messages_data)
#         except Exception as e:
#             print("Error loading cached messages:", e)

#     # Ensure system prompt is always present
#     system_message = SystemMessage(
#         content=(
#             "You are an intelligent assistant chatbot named Mitsuha.\n"
#             "If asked, 'What is your name?', reply exactly: 'I am Dhruv Sharma, an assistant.'\n"
#             "You are also known as Mitsuha.\n"
#             "If you don’t know something, say: 'I don't have that information at the moment.'"
#         )
#     )
#     if not memory.chat_memory.messages or not any(isinstance(msg, SystemMessage) for msg in memory.chat_memory.messages):
#         memory.chat_memory.add_message(system_message)
#     else:
#         # Ensure the system message is always the first message
#         memory.chat_memory.messages = [system_message] + [
#             msg for msg in memory.chat_memory.messages if not isinstance(msg, SystemMessage)
#         ]

#     return memory

# # Function: Save memory (after summarizing)
# def save_memory(memory):
#     try:
#         # Get the summary of messages
#         summary = summarize_conversation(memory.chat_memory.messages)

#         # Append the summary as a SystemMessage instead of replacing the memory
#         memory.chat_memory.add_message(SystemMessage(content=summary))

#         # Save the updated memory to cache
#         cache.set("chat_memory_messages", pickle.dumps(memory.chat_memory.messages), timeout=None)

#     except Exception as e:
#         print("❌ Error saving memory:", e)

# # Main chatbot function
# def chat_bot(user_input):
#     memory = get_memory()

#     # Add user message to memory
#     if not memory.chat_memory.messages or memory.chat_memory.messages[-1].content != user_input:
#         memory.chat_memory.add_message(HumanMessage(content=user_input))

#     try:
#         # Handle specific questions directly
#         if user_input.lower() in ["who are you?", "what is your name?"]:
#             return "I am Dhruv Sharma, an assistant. You can also call me Mitsuha."

#         if "dhruv sharma" in user_input.lower():
#             return "I am Dhruv Sharma's assistant chatbot, designed to help with various tasks."


#         # Handle ambiguous responses
#         if user_input.lower() in ["yes", "no"]:
#             return "Could you please clarify your question?"

#         # Search relevant docs from Qdrant
#         query_results = get_similar_ans(user_input)
#         if not query_results:
#             return "No relevant documents found."

#         query_docs = [Document(page_content=str(hit.payload)) for hit in query_results]

#         # Run Gemini QA chain using the invoke method
#         response = qa_chain.invoke({
#             "input_documents": query_docs,
#             "question": user_input  # Use the user's input directly
#         })

#         # Extract the response content if it's a dictionary
#         if isinstance(response, dict) and "output_text" in response:
#             response_text = response["output_text"]
#         else:
#             response_text = str(response)

#         # Check if the response is valid
#         if not response_text.strip():
#             return "I couldn't generate a meaningful response. Please try rephrasing your question."

#         # Store Gemini’s answer to memory
#         memory.chat_memory.add_message(AIMessage(content=response_text))

#         # Save memory after processing
#         save_memory(memory)

#         return response_text

#     except Exception as e:
#         print(f"Error in chat_bot: {e}")
#         return "Something went wrong while processing your request."
