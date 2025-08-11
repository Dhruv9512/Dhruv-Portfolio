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
import re

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
    import re

    categories_list = [
        "about me", "certification", "education_marks_academic",
        "resume", "skill", "Work_Experience_and_Internships", "projectwork"
    ]

    prompt = f"""
You are a semantic category classifier for Dhruv Sharma's portfolio.

Given the user query: "{query}", identify all relevant categories from the list below.
{categories_list}

Categories and their meanings:
1. "about me" → Personal background, biography, age, location, address, contact information, hometown, hobbies, interests, or any general personal details.
2. "certification" → Academic or professional certificates, completed courses, and awarded credentials.
3. "education_marks_academic" → Academic history, schools, colleges, degrees, grades, percentages, CGPA, and other academic achievements.
4. "resume" → Career summary, complete CV, or a document outlining qualifications and experience.
5. "skill" → Technical skills, soft skills, tools, languages, and areas of expertise.
6. "Work_Experience_and_Internships" → Past jobs, roles, companies, work history, professional positions, and internships.
7. "projectwork" → Academic, personal, or professional projects, case studies, portfolios, and hands-on work.

Your task:
- Carefully interpret the query's intent, even if the words are different from the category names.
- Map synonyms, paraphrases, and indirect requests to the most relevant category or categories.
- If a query spans multiple categories, return all of them.
- Do not make up new categories — only choose from the list above.
- Output must be a valid Python list of strings (e.g., ["about me", "skill"]).
- Do not output explanations, markdown, or extra text — only the list.


Only return a valid Python list of strings as plain text.
"""

    try:
        model = get_gemini_llm()
        response = model.invoke(prompt)
        raw_text = response.content if hasattr(response, "content") else str(response)

        logger.info(f"Gemini raw response: {repr(raw_text)}")

        # 💡 Strip code fences if present
        cleaned_text = re.sub(r"```(?:python)?\n?", "", raw_text.strip(), flags=re.IGNORECASE).strip("`").strip()

        categories = ast.literal_eval(cleaned_text)

        

        if not isinstance(categories, list):
            raise ValueError("Gemini did not return a valid list.")

        # Normalize + match
        normalized = [cat.strip().lower().replace(" ", "_") for cat in categories]
        matched = [cat for cat in categories_list if cat.lower().replace(" ", "_") in normalized]

        return matched

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

    # Step 1 — Classify query into portfolio categories
    categories = extract_categories_with_gemini(query)
    logger.info(f"Matched categories: {categories}")

    if not categories:
        return "No matching category found in Dhruv Sharma's portfolio."

    # Step 2 — Retrieve all context chunks across all categories
    all_context = []
    for collection in categories:
        try:
            qdrant = QdrantVectorStore(
                client=qdrant_client,
                collection_name=collection,
                embedding=embedder
            )

            retriever = qdrant.as_retriever(
                search_type="mmr",
                search_kwargs={"k": 8, "fetch_k": 30, "lambda_mult": 0.5}  # Fetch more to avoid missing details
            )

            docs = retriever.invoke(query)
            for doc in docs:
                if doc.page_content.strip():
                    all_context.append(doc.page_content.strip())

        except Exception as e:
            logger.error(f"Error retrieving from {collection}: {e}")

    if not all_context:
        return "No relevant information found in Dhruv Sharma's portfolio."

    # Step 3 — Merge all chunks into one string
    combined_context = "\n\n".join(set(all_context))  # set() removes duplicates

    # Step 4 — Create filter prompt for detailed synthesis
    filter_prompt = f"""
You are a precise and comprehensive answer generator for Dhruv Sharma's portfolio data.

Question:
{query}

Retrieved Portfolio Data:
{combined_context}

Instructions:
1. Identify ALL pieces of information in the provided text that relate to the question.
2. Merge them into a **single, complete, and self-contained** answer.
3. Preserve every relevant fact — do not omit technical details, responsibilities, or context.
4. Never describe anything as "current", "latest", "recent", "ongoing", or "main" unless the retrieved data explicitly states it.
   - If the data does not explicitly mark something as current, present it neutrally (e.g., "Dhruv Sharma has worked on..." or "Projects include...").
5. Always include **all relevant items** from the data, even if the user’s question asks for "current", "latest", "recent", or "main".
6. **When including URLs, copy them EXACTLY as they appear in Retrieved Portfolio Data without changing, shortening, or reformatting them.**
7. Do not generate or guess any URLs.
8. Keep tone professional and clear.
9. Never return "No information" unless truly nothing relevant exists.

Return ONLY the final combined answer.
"""





    # Step 5 — Ask LLM to merge & format
    llm = get_gemini_llm()
    answer = llm.invoke(filter_prompt).content

    return answer

# --- Tool Binding --- #
tools = [qdrant_rag_tool]

llm = get_groq_llm().bind_tools(tools=tools)

# --- System Prompt --- #
system_prompt = """
You are the official assistant of Dhruv Sharma and your name is "Luffy" from One Piece anime.

If the user tells you their name, remember it and refer to them by that name in future responses. Engage in friendly, conversational replies while staying professional.

When the user asks about you, Luffy, or uses "you" referring to the assistant, answer as Luffy with friendly, conversational replies.

Your primary responsibility is to answer questions about Dhruv Sharma — including his marks, education, projects, experience, or personal/professional background.

IMPORTANT:
- For EVERY question that is about Dhruv Sharma (including any mention of "Dhruv Sharma", "you" meaning him, or any detail from his portfolio), you MUST call the `qdrant_rag_tool` to retrieve information BEFORE answering.
- Never skip the RAG step, even if you think you already know the answer.
- Do not answer from memory without first retrieving from the portfolio knowledge base.

If the user asks a question that is NOT related to Dhruv Sharma or his portfolio, respond ONLY with:
"I can only assist with questions about Dhruv Sharma. Please ask something related to his portfolio."
Do NOT provide any additional information, answers, or hints.

Remain concise, helpful, polite, and always stay on topic.

"""


# --- LLM Tool Node --- #
# def rewrite_query_with_context(state: State) -> str:
#     logger.info("rewrite_query_with_context called")

#     def get_role(msg):
#         if hasattr(msg, "type"):
#             return msg.type  # LangChain message object
#         elif isinstance(msg, dict):
#             return msg.get("role", "")
#         return ""

#     def get_content(msg):
#         if hasattr(msg, "content"):
#             return msg.content  # LangChain message object
#         elif isinstance(msg, dict):
#             return msg.get("content", "")
#         return ""

#     # Build history text
#     history_text = "\n".join(
#         [f"{get_role(msg).capitalize()}: {get_content(msg)}" for msg in state["messages"]]
#     )

#     latest_query = state["messages"][-1].content
#     prompt = f"""
# You are a query rewriter for Dhruv Sharma's portfolio chatbot.

# Conversation so far:  
# {history_text}

# User's latest question:  
# "{latest_query}"
 
# - Do NOT add, remove, or change any words, except replace vague pronouns like "it", "this", "that", "he", "she", "they" with the exact thing or person they refer to.
# - Do NOT change the meaning or introduce new information, references, or entities.
# - Only replace vague pronouns. If the query does not contain vague pronouns, return it exactly as is.
# - Do NOT change any proper nouns or specific names.
# - Return only the rewritten query with no extra text.

# Only do exactly what is mentioned above. Do not add, remove, or alter anything else.



# """


#     groq_llm = get_groq_llm()
#     rewritten_query = groq_llm.invoke(prompt)

#     logger.info(f"The rewrite is: {rewritten_query}")

#     return rewritten_query.content


    
def run_llm_with_tools(state: State):
    # Rewrite latest query in place
    # state["messages"][-1].content =  rewrite_query_with_context(state)

    messages = state["messages"]
    system_msg = SystemMessage(content=system_prompt)
    all_messages = [system_msg] + messages

    # Get the latest user query content
    current_user_msg = messages[-1].content if messages else ""

    # Check for repeated questions
    for i in range(len(messages) - 2):
        if (
            messages[i].type == "human"
            and messages[i].content.strip().lower() == current_user_msg.strip().lower()
        ):
            for j in range(i + 1, len(messages)):
                if messages[j].type == "ai":
                    logger.info(f"✅ Repeated question detected. Returning cached formatted response: {messages[j].content}")
                    return {"messages": [messages[j].content]}  # don't do j+1

    logger.info(f"🔍 Query after rewrite: {state['messages'][-1].content}")

    # If no cache hit, run LLM
    result = llm.invoke(all_messages)
    logger.info(f"LLM response: {result}")
    return {"messages": [result]}


# --- Formatter Node --- #

def format_response(state: State):
    """
    Formats the latest message in `state` into clean Markdown.
    Always formats the content — no filtering, no bypass.
    """
    llm = get_gemini_llm()

    # Get raw answer from last message
    raw_answer = state['messages'][-1].content
    question = state['messages'][0].content  # First message = user question

    # Extract links from raw_answer
    links = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', raw_answer)

    # Remove links from the text (replace [title](url) → title)
    answer_without_links = re.sub(
        r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'\1', raw_answer
    )

    # Markdown formatting prompt
    human_prompt = """
You are Dhruv Sharma’s AI assistant.

You are given:
- The user's **question**
- The initial answer with links removed

Your task:
- Return a **clean, polished Markdown response** suitable for display.
- Use professional, clear language.
- Apply Markdown best practices:
  - **Bold** for key terms or headings
  - Bullet points for lists
  - `###` for section headers
  - Tables for structured data

Do **not** add or modify links — they will be appended after.

---

**User Question:**  
{question}

**Initial Answer (links removed):**  
{answer_without_links}

---

✅ Write the final response in Markdown (without links).
Formatted Response:
"""
    prompt = ChatPromptTemplate.from_template(human_prompt)
    chain = prompt | llm

    # Generate formatted Markdown
    formatted_text = chain.invoke({
        "question": question,
        "answer_without_links": answer_without_links
    }).content

    # Append extracted links at the end in Markdown
    if links:
        formatted_text += "\n\n🔗 **Links**\n"
        for title, url in links:
            formatted_text += f"- [{title}]({url})\n"

    logger.info("✅ Final Markdown response formatted.")
    return {"messages": [formatted_text]}

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
