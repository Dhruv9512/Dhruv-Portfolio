import os
import logging
from urllib.parse import unquote, urlparse
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from typing import Annotated
from langgraph.prebuilt import ToolNode, tools_condition
import json as std_json
from typing_extensions import TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver
import nest_asyncio
import re
import json
from typing import Dict, Any , List
from langchain_core.messages import AIMessage
nest_asyncio.apply()
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("__name__")

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



def get_embedder():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    # from langchain_ollama import OllamaEmbeddings

    # return OllamaEmbeddings(model="nomic-embed-text")

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

        # Strip code fences if present
        cleaned_text = re.sub(r"``(?:python)?\n?", "", raw_text.strip(), flags=re.IGNORECASE).strip("").strip()

        categories = ast.literal_eval(cleaned_text)

        if not isinstance(categories, list):
            raise ValueError("Gemini did not return a valid list.")

        # Normalize + match exactly
        normalized = [cat.strip().lower().replace(" ", "_") for cat in categories]
        matched = [cat for cat in categories_list if cat.lower().replace(" ", "_") in normalized]

        # --- MODIFIED POST-PROCESSING ---
        # Purpose: Always return 3 OR MORE categories.

        # We no longer trim if len(matched) > 3

        # 1. Pad if fewer than 3
        # Use a defined list of sensible defaults to pad with
        default_padding_categories = ["about me", "skill", "projectwork"]
        
        i = 0
        # Add defaults one by one until we reach 3, skipping duplicates
        while len(matched) < 3 and i < len(default_padding_categories):
            cat_to_add = default_padding_categories[i]
            if cat_to_add not in matched:
                matched.append(cat_to_add)
            i += 1
            
        # 2. Final check: In the unlikely event defaults were already present
        #    and we still have < 3, just duplicate the first item to force 3.
        while len(matched) < 3:
             if matched: # Avoid error on an empty 'matched' list
                 matched.append(matched[0])
             else: # Absolute fallback if LLM returned [] and defaults failed
                 matched = ["about me", "skill", "projectwork"]
                 break # We have 3 now
        
        # We no longer trim the list, so if 'matched' has > 3 items,
        # all of them will be returned.
        # --- END OF MODIFICATION ---

        return matched

    except Exception as e:
        logger.error(f"Error parsing Gemini category: {e}")
        # Fallback to defaults if parsing fails
        return ["about me", "skill", "projectwork"]

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
                search_kwargs={"k": 4, "fetch_k": 30, "lambda_mult": 0.5}  # Fetch more to avoid missing details
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
2. Merge them into a *single, complete, and self-contained* answer.
3. Preserve every relevant fact — do not omit technical details, responsibilities, or context.
4. Never describe anything as "current", "latest", "recent", "ongoing", or "main" unless the retrieved data explicitly states it.
   - If the data does not explicitly mark something as current, present it neutrally (e.g., "Dhruv Sharma has worked on..." or "Projects include...").
5. Always include *all relevant items* from the data, even if the user’s question asks for "current", "latest", "recent", or "main".
6. *When including URLs, copy them EXACTLY as they appear in Retrieved Portfolio Data without changing, shortening, or reformatting them.*
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

llm = get_gemini_llm().bind_tools(tools=tools)

# --- System Prompt --- #
system_prompt = """
You are the official assistant of Dhruv Sharma and your name is "Luffy" from One Piece anime.
If the user starts with simple greetings (e.g., "Hi", "Hello", "How are you?", "What's up?"), you should respond in a friendly, conversational manner in your Luffy persona.
If the user tells you their name, remember it and refer to them by that name in future responses. Engage in friendly, conversational replies while staying professional.

When the user asks about you, Luffy, or uses "you" referring to the assistant, answer as Luffy with friendly, conversational replies.

Your primary responsibility is to answer questions about Dhruv Sharma — including his marks, education, projects, experience, or personal/professional background.

IMPORTANT:
- For EVERY question that is about Dhruv Sharma (including any mention of "Dhruv Sharma", "you" meaning him, or any detail from his portfolio), you MUST call the qdrant_rag_tool to retrieve information BEFORE answering.
- Never skip the RAG step, even if you think you already know the answer.
- Do not answer from memory without first retrieving from the portfolio knowledge base.

If the user asks a question that is NOT related to Dhruv Sharma or his portfolio, respond ONLY with:
"I can only assist with questions about Dhruv Sharma. Please ask something related to his portfolio."
Do NOT provide any additional information, answers, or hints.

Remain concise, helpful, polite, and always stay on topic.

"""

    
def run_llm_with_tools(state: State):
    # ... (rest of your setup code) ...
    messages = state["messages"]
    system_msg = SystemMessage(content=system_prompt)
    all_messages = [system_msg] + messages
    current_user_msg = messages[-1].content if messages else ""

    # Check for repeated questions
    for i in range(len(messages) - 2):
        if (
            messages[i].type == "human"
            and messages[i].content.strip().lower() == current_user_msg.strip().lower()
        ):
            # Found a matching previous question. 
            # Now, find the *final answer* for it.
            for j in range(i + 1, len(messages)):
                if messages[j].type == "ai":
                    
                    # --- THIS IS THE FIX ---
                    # Check if the cached message is a valid, final answer
                    
                    # Safely check if the message has tool calls
                    has_tool_calls = hasattr(messages[j], 'tool_calls') and messages[j].tool_calls
                    
                    # Check if the message has actual, non-empty content
                    has_content = messages[j].content and messages[j].content.strip()

                    if has_content and not has_tool_calls:
                        # This is a REAL answer. Return it from cache.
                        logger.info(f"✅ Repeated question detected. Returning cached formatted response: {messages[j].content}")
                        return {"messages": [messages[j].content]}
                    
                    # If it's a tool call or has empty content,
                    # just continue the loop. The *next* AI message
                    # might be the actual final answer.
                    # --- END OF FIX ---

            # If the inner 'j' loop finished without returning,
            # it means we found the question but no valid *final answer* for it.
            # We should break from the 'i' loop and let the LLM run again.
            logger.info(f"⚠️ Repeated question detected, but no valid final answer was cached. Re-running LLM.")
            break 

    logger.info(f"🔍 Query after rewrite: {state['messages'][-1].content}")

    # If no cache hit, run LLM
    result = llm.invoke(all_messages)
    logger.info(f"LLM response: {result}")
    return {"messages": [result]}




# ---------------- Config ----------------
ALLOWED_SCHEMES = ("https://", "http://", "mailto:", "ftp://", "tel:")

MD_LINK_RE = re.compile(r"\[([^\]\n]{1,200})\]\(([^()\s]{1,2048})\)")
NESTED_LINK_RE = re.compile(r"\[[^\]]*\]\([^()]*\)\s*\([^()]*\)")
DUPLICATE_URL_AFTER_RE = re.compile(r"\]\([^()]*\)\s*\((?:https?|mailto|ftp|tel):[^()]*\)")
BARE_URL_RE = re.compile(r"(?P<url>(?:https?://|http://|mailto:|ftp://|tel:)[^\s<>()\[\]{}\"'`,;]+)")

# NEW: Regex to find bare email addresses that are NOT part of a mailto: link
BARE_EMAIL_RE = re.compile(r"(?<!mailto:)\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


# ---------------- Utilities ----------------
def is_allowed_absolute_url(url: str) -> bool:
    return any(url.startswith(s) for s in ALLOWED_SCHEMES)

def is_null_url(url: str) -> bool:
    return url.strip().lower() == "https://null.com"

def strip_one_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl == -1:
            return s
        last = s.rfind("\n```")
        if last == -1:
            if s.endswith("```"):
                inner = s[first_nl + 1: len(s) - 3]
                return inner.strip()
            return s
        inner = s[first_nl + 1: last].rstrip("\n")
        return inner.strip()
    return s

def enforce_no_nested_or_duplicate_links(text: str) -> str:
    text = NESTED_LINK_RE.sub("", text)
    text = DUPLICATE_URL_AFTER_RE.sub(")", text)
    return text

def collapse_blank_lines(s: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", s.strip())


# ---------------- Title generation via LLM ----------------
def llm_generate_titles(llm, urls: List[str]) -> List[str]:
    """
    Ask the LLM to return concise, human-readable titles for each URL.
    Guarantees length and style. Fallback to 'Link' if the model misses any.
    """
    if not urls:
        return []
    prompt = (
        "You are a helpful assistant that assigns short, descriptive titles for links.\n"
        "Rules:\n"
        "- 1 line per item in order.\n"
        "- 2-3 words, no punctuation except parentheses for usernames.\n"
        "- Prefer platform-specific names like 'GitHub Repository', 'Live Site', 'HackerRank Profile'.\n"
        "- For Instagram profiles, format: 'Instagram Profile (@username)' when username is in URL.\n"
        "- For Instagram reels/posts/stories: 'Instagram Reel', 'Instagram Post', 'Instagram Story'.\n"
        "- For mailto: use 'Email'. For tel: use 'Phone'. For Google Drive: 'Document'.\n"
        "- Do not include the URL in the title. Do not add emojis.\n"
        "Return exactly N lines, one title per input in the same order.\n\n"
        "Examples:\n"
        "Input:\n"
        "1) https://github.com/Dhruv9512/Pixel-Classes.git\n"
        "2) https://pixelclass.netlify.app/\n"
        "3) https://www.hackerrank.com/dhruv_sharma\n"
        "4) https://www.instagram.com/dhruv.codes/\n"
        "Output:\n"
        "GitHub Repository\n"
        "Live Site\n"
        "HackerRank Profile\n"
        "Instagram Profile (@dhruv.codes)\n\n"
        f"N = {len(urls)}\n"
        "Input:\n" + "\n".join(f"{i+1}) {u}" for i, u in enumerate(urls)) + "\n"
        "Output:\n"
    )
    resp = llm.invoke(prompt)
    content = getattr(resp, "content", resp)
    if not isinstance(content, str):
        content = str(content)
    lines = [ln.strip() for ln in strip_one_fence(content).splitlines() if ln.strip()]
    titles = []
    for i in range(len(urls)):
        titles.append(lines[i] if i < len(lines) else "Link")
    return titles


# ---------------- Normalization using LLM titles ----------------
# --- Helper functions for link normalization ---

def collect_urls_in_text(text: str) -> List[str]:
    """ Gathers all Markdown and bare URLs from a text block. """
    urls = set()
    # Find Markdown links: [text](url)
    for m in MD_LINK_RE.finditer(text):
        url = m.group(2).strip()
        if is_allowed_absolute_url(url):
            urls.add(url)
    # Find bare URLs: http://...
    for m in BARE_URL_RE.finditer(text):
        url = m.group("url").strip()
        if is_allowed_absolute_url(url):
            urls.add(url)
    return list(urls)

# NEW REPLACEMENT for make_normalizer
def make_md_normalizer(url_to_title: dict):
    """ 
    Creates a replacer function for existing Markdown links.
    Converts: [any text](url) -> Title: [Visit](url)
    """
    def normalize_md_link(match: re.Match) -> str:
        text = match.group(1).strip()
        url = match.group(2).strip()
        
        if is_null_url(url):
            title = url_to_title.get(url) or (text if text else "Link")
            return f"{title}: Link not available"
        if not is_allowed_absolute_url(url):
            return "" # Remove invalid links
        
        # Use the title from the map, fallback to original link text
        title = url_to_title.get(url) or (text if text else "Link")
        return f"{title}: [Visit]({url})"
    return normalize_md_link

# NEW REPLACEMENT for convert_bare_urls_to_lines
def make_bare_url_normalizer(url_to_title: dict):
    """ 
    Creates a replacer function for bare URLs.
    Converts: http://... -> Title: [Visit](http://...)
    """
    def normalize_bare_url(match: re.Match) -> str:
        url = match.group("url").strip()
        
        if is_null_url(url):
            # Find title, fallback to "Link"
            title = url_to_title.get(url, "Link")
            return f"{title}: Link not available"
        if not is_allowed_absolute_url(url):
            return "" # Remove invalid links

        title = url_to_title.get(url, "Link")
        return f"{title}: [Visit]({url})"
    return normalize_bare_url


# ---------------- Main entry ----------------
def format_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inputs:
     - state['messages']: list where the last item is the model draft and the first human is the question.
    Output:
     - {"messages": [AIMessage(content=payload_json)]} where payload_json is a JSON string
       with only: content (Markdown with inline links preserved/standardized).
    """
    # llm = get_gemini_llm() # This should be defined in your environment

    # Extract latest model content
    raw_answer = state['messages'][-1].content

    # --- NEW IDEMPOTENCY CHECK ---
    try:
        # Check if the raw_answer is *already* our final JSON payload
        payload = std_json.loads(raw_answer)
        if isinstance(payload, dict) and "content" in payload:
            logger.info("✅ Format Response: Input is already formatted JSON. Passing through.")
            # It is! Just return the original message.
            return {"messages": [AIMessage(content=raw_answer)]}
    except (std_json.JSONDecodeError, TypeError, ValueError):
        # It's not JSON. It's raw text from the RAG tool or LLM.
        # Proceed as normal.
        pass
    # --- END OF CHECK ---

    # Extract original question
    question = ""
    for msg in state['messages']:
        if getattr(msg, "type", None) == 'human':
            question = msg.content
            break

    # Step 1: pre-clean raw
    stripped = strip_one_fence(raw_answer)
    sanitized = enforce_no_nested_or_duplicate_links(stripped)

    # --- MODIFICATION START: Protect and Restore Emails ---
    # Temporarily replace bare emails with placeholders
    protected_text = sanitized
    email_map = {}
    def replace_email(match):
        email = match.group(0)
        placeholder = f"__EMAIL_PLACEHOLDER_{len(email_map)}__"
        email_map[placeholder] = email
        return placeholder

    protected_text = BARE_EMAIL_RE.sub(replace_email, protected_text)
    # --- END MODIFICATION ---

    # Step 2: gather unique absolute URLs for titling
    urls = [u for u in collect_urls_in_text(protected_text) if not is_null_url(u)]

    # Step 3: request titles from LLM
    url_titles = llm_generate_titles(llm, urls)
    url_to_title = dict(zip(urls, url_titles))

    # (This helper function is good, keep it)
    def safe_title(url: str, fallback: str = "Link") -> str:
        t = (url_to_title.get(url) or "").strip()
        if not t:
            if url.startswith("mailto:"): return "Email"
            if url.startswith("tel:"): return "Phone"
            return fallback
        return t

    for u in list(url_to_title.keys()):
        url_to_title[u] = safe_title(u, url_to_title.get(u, "Link"))

    # --- REVISED NORMALIZATION STEPS ---

    # Step 4: Create both normalizers
    md_normalizer = make_md_normalizer(url_to_title)
    bare_url_normalizer = make_bare_url_normalizer(url_to_title)

    # Step 5: Normalize existing Markdown links FIRST
    # This replaces [text](url) with Title: [Visit](url)
    normalized_md = MD_LINK_RE.sub(md_normalizer, protected_text)

    # Step 6: Normalize bare URLs SECOND
    # This replaces http://... with Title: [Visit](http://...)
    # We run this on the output of the previous step to catch any bare URLs
    all_normalized = BARE_URL_RE.sub(bare_url_normalizer, normalized_md)

    # --- END REVISION ---

    # Step 7: final sanitation and line filtering
    normalized = enforce_no_nested_or_duplicate_links(all_normalized)
    lines = []
    for ln in normalized.splitlines():
        if not ln.strip():
            lines.append(ln)
            continue
        bad = False
        # Check for any remaining invalid MD links
        for m in MD_LINK_RE.finditer(ln):
            url = m.group(2).strip()
            if is_null_url(url): continue
            if not is_allowed_absolute_url(url):
                bad = True
                break
        if not bad:
            lines.append(ln)

    normalized = "\n".join(lines)
    normalized = collapse_blank_lines(normalized)

    # Step 8: final formatting prompt (This prompt is good from our last fix)
    human_prompt = f"""
You are an expert Markdown formatter for Dhruv Sharma's portfolio.
You will be given content that is already structured with titles and links.
Your task is to reformat it to be cleaner, more organized, and more readable.

The user's question was: "{question}"
The content to format is:
"{normalized}"

**RULES:**
1.  Find project titles (e.g., `Mechanic Setu:`, `Pixel Class:`). Format them as bold level-3 headings (e.g., `### **Mechanic Setu**`). **You must remove the colon** after the title.
2.  Take the paragraph description *after* the title and **analyze it.**
3.  **Create logical sub-headings** (e.g., `Features`, `Technologies Used`, `Key Details`) based on the content. Format these sub-headings as **bold text on their own line** (e.g., `**Features**`). **Do not use heading markers** (like `####`).
4.  **Rewrite** the description's details as concise bullet points *under* the appropriate new sub-headings.
5.  After all description-based sub-headings, create a final sub-heading: `**Links**`.
6.  Place all preserved links (e.g., `GitHub Repository: [Visit](...)`) as a bulleted list *under* the `**Links**` sub-heading.
7.  Return ONLY the formatted Markdown. Do not add any extra explanations.

**Example Input:**
Mechanic Setu:
Mechanic Setu (mechanic side) helps mechanics manage and respond to service requests... The system uses WebSockets for instant notifications... The Django backend is integrated with Celery...
GitHub Repository: [Visit](https://github.com/Dhruv9512/Mechanic-Setu.git)
Live Site: [Visit](https://setu-partner.netlify.app/)

**Example Output:**
### **Mechanic Setu**

**Features**
- Helps mechanics manage and respond to service requests from nearby users.
- Allows mechanics to track user location and update job status.
- Uses WebSockets for instant notifications (new, accepted, completed).

**Technologies Used**
- Django backend with Celery for asynchronous task handling.

**Links**
- GitHub Repository: [Visit](https://github.com/Dhruv9512/Mechanic-Setu.git)
- Live Site: [Visit](https://setu-partner.netlify.app/)
"""
    formatted = llm.invoke(human_prompt)
    formatted_text = getattr(formatted, "content", formatted)
    if not isinstance(formatted_text, str):
        formatted_text = str(formatted_text)
    formatted_text = strip_one_fence(formatted_text)

    # Restore the protected emails back into the final text
    restored_text = formatted_text
    for placeholder, email in email_map.items():
        restored_text = restored_text.replace(placeholder, email)

    final_payload = {"content": restored_text}
    print(f"Final formatted response: {final_payload['content']}")
    payload_json = json.dumps(final_payload)
    return {"messages": [AIMessage(content=payload_json)]}




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