import os
import logging
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from typing import Annotated
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver
import nest_asyncio

nest_asyncio.apply()
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

memory_saver = MemorySaver()

# --- Clients and Models --- #
def get_qdrant_client():
    from qdrant_client import QdrantClient
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )

def get_gemini_llm():
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.2,
        google_api_key=os.environ.get("GOOGLE_API_KEY")
    )

def get_groq_llm():
    from langchain_groq import ChatGroq
    return ChatGroq(
        model="llama3-8b-8192",
        temperature=0.2,
        groq_api_key=os.environ.get("GROQ_API_KEY")
    )

def get_embedder():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001")

# --- State Type --- #
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

# --- Category Extractor --- #
def extract_categories_with_gemini(query: str) -> list[str]:
    import ast

    categories_list = [
        "about me", "certification", "education_marks_academic",
        "resume", "skill", "Work_Experience_and_Internships", "projectwork"
    ]

    prompt = f"""
You are a semantic classifier for Dhruv Sharma's portfolio. 
Given this query: "{query}", return the most relevant category from this list:

{categories_list}

Return ONLY one category as a valid Python list of one string, like: ["projectwork"]
"""

    try:
        model = get_gemini_llm()
        response = model.invoke(prompt)
        raw_text = response.content if hasattr(response, "content") else str(response)

        logger.info(f"Gemini raw response: {repr(raw_text)}")
        cleaned_text = raw_text.strip()
        if not cleaned_text.startswith("["):
            cleaned_text = f'["{cleaned_text}"]'

        categories = ast.literal_eval(cleaned_text)
        if not isinstance(categories, list) or not categories:
            raise ValueError("Invalid category format")

        selected = categories[0].strip().lower().replace(" ", "_")
        matched = [cat for cat in categories_list if cat.lower().replace(" ", "_") == selected]
        return matched if matched else []

    except Exception as e:
        logger.error(f"Error parsing Gemini category: {e}")
        return []

# --- Tool for RAG --- #
def qdrant_rag_tool(query: str) -> str:
    """
    Searches Dhruv Sharma's portfolio content using vector similarity from Qdrant.

    This function embeds the user's query and performs a semantic search against
    Dhruv's portfolio website/documents stored in Qdrant, optionally filtered by category.

    Args:
        query (str): The user's question about Dhruv Sharma (e.g., education, skills, projects).

    Returns:
        str: The most relevant content retrieved from the portfolio vector store.
    """

    from langchain_qdrant import QdrantVectorStore

    logger.info(f"User query: {query}")
    qdrant_client = get_qdrant_client()
    embedder = get_embedder()

    categories = extract_categories_with_gemini(query)
    logger.info(f"Resolved categories: {categories}")

    if not categories:
        return "No matching category found. Please rephrase your query."

    collection = categories[0]

    try:
        qdrant = QdrantVectorStore(
            client=qdrant_client,
            collection_name=collection,
            embedding=embedder
        )

        retriever = qdrant.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
        )

        docs = retriever.invoke(query)
        context = [doc.page_content for doc in docs if doc.page_content.strip()]
        logger.info(f"Found {context} relevant documents.")
        return "\n\n".join(context) if context else "No relevant information found."

    except Exception as e:
        logger.error(f"Error in Qdrant retrieval: {e}")
        return "An error occurred while retrieving data. Please try again later."

# --- Tool Binding --- #
tools = [qdrant_rag_tool]
llm = get_groq_llm().bind_tools(tools=tools)

# --- System Prompt --- #
system_prompt = """
You are the official assistant of Dhruv Sharma.

If the user tells you their name, remember it and refer to them by that name in future responses. Engage in friendly, conversational replies while staying professional.

Your primary responsibility is to answer questions about Dhruv Sharma — including his marks, education, projects, experience, or personal/professional background.

You MUST ALWAYS send every Dhruv Sharma-related question to the PortfolioRAGSearch tool to retrieve the answer.

If the user refers to "you", interpret it as referring to Dhruv Sharma — not yourself.

If no relevant information is found from the portfolio, respond:
"No information about that was found in Dhruv Sharma's portfolio."

If the user asks something unrelated to Dhruv Sharma, respond with:
"I can only assist with questions about Dhruv Sharma. Please ask something related to his portfolio."

Remain concise, helpful, polite, and always stay on topic.
"""

# --- LLM Tool Node --- #
def run_llm_with_tools(state: State):
    messages = state["messages"]
    system_msg = SystemMessage(content=system_prompt)
    all_messages = [system_msg] + messages

    current_user_msg = messages[-1].content if messages else ""

    for i in range(len(messages) - 2):
        if messages[i].type == "human" and messages[i].content.strip().lower() == current_user_msg.strip().lower():
            for j in range(i + 1, len(messages)):
                if messages[j].type == "ai":
                    logger.info("✅ Repeated question detected. Returning cached formatted response.")
                    return {"messages": [messages[j+2].content]}

    result = llm.invoke(all_messages)
    logger.info(f"LLM response: {result.content}")
    return {"messages": [result]}

# --- Formatter Node --- #
def format_response(state: State):
    llm = get_gemini_llm()
    human_prompt = """
You are Dhruv Sharma’s AI assistant.

Your job is to format answers for end users. You're given:
- The user's question
- An initial (raw) answer generated by an internal system (RAG)

Your task is to:
- Format the answer if it is related to Dhruv Sharma (his education, projects, experience, skills, achievements, or background).
- Refuse to answer general knowledge or unrelated questions (e.g., capitals of countries, weather, trivia).

### Guidelines:
1. Only output a **final, polished response** suitable for the user — do **not** include or refer to the original raw content.
2. Use a professional, helpful, and clear tone.
3. If any links are present, extract and move them to a **🔗 Links** section at the end, using markdown format.
4. Do not include technical metadata, IDs, or debugging information.
5. Never mention "raw answer", "RAG", or "retrieved documents".

---

**User Question:**  
{question}

**Initial Answer (for internal use only):**  
{raw_answer}

---

✅ Now write the **final response** to show to the user, starting below this line:

Formatted Response:
"""

    prompt = ChatPromptTemplate.from_template(human_prompt)
    chain = prompt | llm

    question = SystemMessage(content=system_prompt) + state['messages'][0].content
    raw_answer = state['messages'][-1].content

    result = chain.invoke({
        "question": question,
        "raw_answer": raw_answer
    })

    logger.info("✅ Final response formatted successfully.",result)
    return {"messages": [result]}

# --- Graph --- #
graph = StateGraph(State)
graph.add_node("Run LLM with Tools", run_llm_with_tools)
graph.add_node("Format Response", format_response)
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "Run LLM with Tools")
graph.add_conditional_edges("Run LLM with Tools", tools_condition)
graph.add_edge("tools", "Format Response")
graph.add_edge("Format Response", END)

main_graph = graph.compile(checkpointer=memory_saver)
