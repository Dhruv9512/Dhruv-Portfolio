import os
import re
import ast
import json
import logging
import nest_asyncio
from typing import Annotated, Dict, Any, List, TypedDict
from dotenv import load_dotenv

# LangChain / LangGraph Imports
from langchain_core.messages import SystemMessage, AIMessage, AnyMessage
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_qdrant import QdrantVectorStore
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from qdrant_client import QdrantClient

# --- Setup ---
nest_asyncio.apply()
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- 1. PROMPTS (PRESERVED EXACTLY) ---

SYSTEM_PROMPT = """
You are the official assistant of Dhruv Sharma and your name is "Luffy" from One Piece anime.
If the user starts with simple greetings (e.g., "Hi", "Hello", "How are you?", "What's up?"), you should respond in a friendly, conversational manner in your Luffy persona.
If the user tells you their name, remember it and refer to them by that name in future responses. Engage in friendly, conversational replies while staying professional.

When the user asks about you, Luffy, or uses "you" referring to the assistant, answer as Luffy with friendly, conversational replies.

Your primary responsibility is to answer questions about Dhruv Sharma — including his marks, education, projects, experience, or personal/professional background.

IMPORTANT:
- **Portfolio Questions:** If the user asks about Dhruv Sharma (projects, skills, education, contact), you MUST call the `qdrant_rag_tool`.
- **Memory/Context Questions:** If the user asks about *previous conversation* (e.g., "What did I just ask?", "Repeat that", "What is my name?"), DO NOT call the tool. Answer directly from your conversation history.
- **General/Off-topic:** If the user asks something unrelated to Dhruv or the chat (e.g. "Who is Batman?"), refuse politely.

If the user asks a question that is NOT related to Dhruv Sharma or his portfolio, respond ONLY with:
"I can only assist with questions about Dhruv Sharma. Please ask something related to his portfolio."

Do not answer Portfolio questions from memory without first retrieving from the knowledge base.
Remain concise, helpful, polite, and always stay on topic.

"""

CATEGORY_PROMPT_TEMPLATE = """
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

FILTER_PROMPT_TEMPLATE = """
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
10.**Focus strictly on the user's specific question.** Do not apologize for missing information (like email or phone) unless the user specifically asked for it.
11.*When including URLs, copy them EXACTLY as they appear in Retrieved Portfolio Data without changing, shortening, or reformatting them.*

Return ONLY the final combined answer.
"""

TITLE_GENERATION_PROMPT = """You are a helpful assistant that assigns short, descriptive titles for links.
Rules:
- 1 line per item in order.
- 2-3 words, no punctuation except parentheses for usernames.
- Prefer platform-specific names like 'GitHub Repository', 'Live Site', 'HackerRank Profile'.
- For Instagram profiles, format: 'Instagram Profile (@username)' when username is in URL.
- For Instagram reels/posts/stories: 'Instagram Reel', 'Instagram Post', 'Instagram Story'.
- For mailto: use 'Email'. For tel: use 'Phone'. For Google Drive: 'Document'.
- Do not include the URL in the title. Do not add emojis.
Return exactly N lines, one title per input in the same order.

Examples:
Input:
1) https://github.com/Dhruv9512/Pixel-Classes.git
2) https://pixelclass.netlify.app/
3) https://www.hackerrank.com/dhruv_sharma
4) https://www.instagram.com/dhruv.codes/
Output:
GitHub Repository
Live Site
HackerRank Profile
Instagram Profile (@dhruv.codes)

N = {n}
Input:
{input_list}
Output:
"""

HUMAN_FORMATTING_PROMPT_TEMPLATE = """
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

# --- 2. CONFIG & CONSTANTS ---
ALLOWED_SCHEMES = ("https://", "http://", "ftp://", "tel:")
MD_LINK_RE = re.compile(r"\[([^\]\n]{1,200})\]\(([^()\s]{1,2048})\)")
NESTED_LINK_RE = re.compile(r"\[[^\]]*\]\([^()]*\)\s*\([^()]*\)")
DUPLICATE_URL_AFTER_RE = re.compile(r"\]\([^()]*\)\s*\((?:https?|mailto|ftp|tel):[^()]*\)")
BARE_URL_RE = re.compile(r"(?P<url>(?:https?://|http://|ftp://|tel:)[^\s<>()\[\]{}\"'`,;]+)")
BARE_EMAIL_RE = re.compile(r"(?<!mailto:)\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


# --- 3. MODEL & CLIENT FACTORIES ---
def get_groq_llm():
    if not os.environ.get("GROQ_API_KEY"): raise ValueError("GROQ_API_KEY missing.")
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2, groq_api_key=os.environ.get("GROQ_API_KEY"))

def get_gemini_llm():
    if not os.environ.get("GOOGLE_API_KEY"): raise ValueError("GOOGLE_API_KEY missing.")
    return ChatGoogleGenerativeAI(model="gemini-2.0-flash",temperature=0.2,google_api_key=os.environ.get("GOOGLE_API_KEY"))

def get_embedder():
    if not os.environ.get("HUGGINGFACEHUB_API_TOKEN"): raise ValueError("HUGGINGFACEHUB_API_TOKEN missing.")
    return HuggingFaceEndpointEmbeddings(model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

def get_qdrant_client():
    return QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))


# --- 4. UTILITIES (Regex, Strings, URLs) ---
def strip_one_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl == -1: return s
        last = s.rfind("\n```")
        if last == -1:
            if s.endswith("```"): return s[first_nl + 1: len(s) - 3].strip()
            return s
        return s[first_nl + 1: last].rstrip("\n").strip()
    return s

def is_allowed_absolute_url(url: str) -> bool:
    return any(url.startswith(s) for s in ALLOWED_SCHEMES)

def is_null_url(url: str) -> bool:
    return url.strip().lower() == "[https://null.com](https://null.com)"

def enforce_no_nested_or_duplicate_links(text: str) -> str:
    text = NESTED_LINK_RE.sub("", text)
    text = DUPLICATE_URL_AFTER_RE.sub(")", text)
    return text

def collect_urls_in_text(text: str) -> List[str]:
    urls = set()
    for m in MD_LINK_RE.finditer(text):
        if is_allowed_absolute_url(m.group(2).strip()): urls.add(m.group(2).strip())
    for m in BARE_URL_RE.finditer(text):
        if is_allowed_absolute_url(m.group("url").strip()): urls.add(m.group("url").strip())
    return list(urls)

def collapse_blank_lines(s: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", s.strip())

# --- 5. CORE LOGIC & TOOLS ---

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

def extract_categories_with_gemini(query: str) -> list[str]:
    categories_list = ["about me", "certification", "education_marks_academic", "resume", "skill", "Work_Experience_and_Internships", "projectwork"]
    prompt = CATEGORY_PROMPT_TEMPLATE.format(query=query, categories_list=categories_list)
    
    try:
        model = get_groq_llm()
        response = model.invoke(prompt)
        cleaned_text = re.sub(r"``(?:python)?\n?", "", response.content.strip(), flags=re.IGNORECASE).strip("").strip()
        categories = ast.literal_eval(cleaned_text)
        
        normalized = [cat.strip().lower().replace(" ", "_") for cat in categories]
        matched = [cat for cat in categories_list if cat.lower().replace(" ", "_") in normalized]
        
        if not matched:
            matched = ["about me", "skill", "projectwork"]
        return matched

    except Exception as e:
        logger.error(f"Category extraction error: {e}")
        return ["about me", "skill", "projectwork"]

def qdrant_rag_tool(query: str) -> str:
    """Searches Dhruv Sharma's portfolio content using vector similarity."""
    
    logger.info(f"User query: {query}")
    categories = extract_categories_with_gemini(query)
    
    if not categories: return "No matching category found in portfolio."

    qdrant_client = get_qdrant_client()
    embedder = get_embedder()
    all_context_docs = [] # Changed from simple string list to objects for filtering

    # 1. Fetch MORE documents (Strategy 1: High Recall)
    for collection in categories:
        try:
            store = QdrantVectorStore(client=qdrant_client, collection_name=collection, embedding=embedder)
            # Increased k to 10 to gather more candidates
            retriever = store.as_retriever(search_type="mmr", search_kwargs={"k": 10, "fetch_k": 30, "lambda_mult": 0.5})
            docs = retriever.invoke(query)
            all_context_docs.extend(docs)
        except Exception as e:
            logger.error(f"Error retrieving from {collection}: {e}")

    if not all_context_docs: return "No relevant information found in portfolio."

    # 2. LLM-Based Re-ranking / Filtering (Strategy 1: High Precision)
    # We ask the LLM to pick the winners before generating the answer.
    
    # Format docs with IDs
    doc_text_list = [f"ID {i}: {d.page_content.strip()}" for i, d in enumerate(all_context_docs) if d.page_content.strip()]
    joined_docs = "\n\n".join(doc_text_list)

    if not joined_docs: return "No relevant information found."

    # Fast check with Groq to find relevant IDs
    check_prompt = f"""
    You are a relevance filter. 
    User Query: "{query}"
    
    Below are several text snippets from a portfolio. 
    Analyze them and return the IDs of the snippets that contain DIRECT answers to the query.
    Ignore snippets that are vague or unrelated.
    
    Snippets:
    {joined_docs}
    
    Return ONLY a list of integer IDs (e.g., [0, 2, 5]). If none are relevant, return [].
    """
    
    try:
        llm_check = get_groq_llm()
        check_response = llm_check.invoke(check_prompt).content
        relevant_ids = [int(num) for num in re.findall(r'\d+', check_response)]
        
        # Filter the docs based on LLM selection
        relevant_content = [all_context_docs[i].page_content.strip() for i in relevant_ids if i < len(all_context_docs)]
        
        # Fallback: if LLM says "none", but we have docs, take the top 3 just in case
        if not relevant_content:
             relevant_content = [d.page_content.strip() for d in all_context_docs[:3]]
             
    except Exception as e:
        logger.error(f"Re-ranking error: {e}. Falling back to raw retrieval.")
        relevant_content = [d.page_content.strip() for d in all_context_docs[:5]]

    combined_context = "\n\n".join(set(relevant_content))
    
    # 3. Final Answer Generation
    llm = get_groq_llm()
    answer = llm.invoke(FILTER_PROMPT_TEMPLATE.format(query=query, combined_context=combined_context)).content
    return answer

# --- 6. NODE FUNCTIONS ---

tools = [qdrant_rag_tool]
llm_with_tools = get_groq_llm().bind_tools(tools)

def run_llm_with_tools(state: State):
    messages = state["messages"]
    system_msg = SystemMessage(content=SYSTEM_PROMPT)
    all_messages = [system_msg] + messages
    current_user_msg = messages[-1].content if messages else ""

    # Caching logic for repeated questions
    for i in range(len(messages) - 2):
        if messages[i].type == "human" and messages[i].content.strip().lower() == current_user_msg.strip().lower():
            for j in range(i + 1, len(messages)):
                if messages[j].type == "ai":
                    has_tools = hasattr(messages[j], 'tool_calls') and messages[j].tool_calls
                    has_content = messages[j].content and messages[j].content.strip()
                    if has_content and not has_tools:
                        logger.info("✅ Returning cached response.")
                        return {"messages": [messages[j].content]}
            break

    result = llm_with_tools.invoke(all_messages)
    return {"messages": [result]}

def llm_generate_titles_helper(urls: List[str]) -> List[str]:
    if not urls: return []
    llm = get_groq_llm()
    input_list = "\n".join(f"{i+1}) {u}" for i, u in enumerate(urls))
    prompt = TITLE_GENERATION_PROMPT.format(n=len(urls), input_list=input_list)
    resp = llm.invoke(prompt)
    content = strip_one_fence(str(resp.content))
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    return [lines[i] if i < len(lines) else "Link" for i in range(len(urls))]

def format_response(state: Dict[str, Any]) -> Dict[str, Any]:
    raw_answer = state['messages'][-1].content
    # --- STEP 0: SANITIZE EMAILS (Make them plain text) ---
    raw_answer = re.sub(r"\[.*?\]\(mailto:([^)]+)\)", r"\1", raw_answer, flags=re.IGNORECASE)
    
    # 2. Remove any remaining "mailto:" prefixes
    raw_answer = re.sub(r"mailto:", "", raw_answer, flags=re.IGNORECASE)
    try:
        payload = json.loads(raw_answer)
        if isinstance(payload, dict) and "content" in payload: return {"messages": [AIMessage(content=raw_answer)]}
    except: pass

    question = next((msg.content for msg in state['messages'] if getattr(msg, "type", None) == 'human'), "")
    
    # --- STEP 1: PRE-PROCESSING ---
    cleaned_text = enforce_no_nested_or_duplicate_links(strip_one_fence(raw_answer))
    email_map = {}
    def protect_email(match):
        placeholder = f"__EMAIL_PLACEHOLDER_{len(email_map)}__"
        email_map[placeholder] = match.group(0)
        return placeholder
    text_safe = BARE_EMAIL_RE.sub(protect_email, cleaned_text)

    # Handle URLs and Titles
    urls = [u for u in collect_urls_in_text(text_safe) if not is_null_url(u)]
    titles = llm_generate_titles_helper(urls)
    url_to_title = dict(zip(urls, titles))

    # --- STEP 2: LINK NORMALIZATION ---
    def normalize_link(text, url): 
        if is_null_url(url): return f"{url_to_title.get(url, 'Link')}: Link not available"
        if not is_allowed_absolute_url(url): return ""
        
        title = url_to_title.get(url) or (text if text else "Link")
        if title == "": title = "Link"
        return f"{title}: [Visit]({url})"

    text_normalized = MD_LINK_RE.sub(lambda m: normalize_link(m.group(1).strip(), m.group(2).strip()), text_safe)
    text_normalized = BARE_URL_RE.sub(lambda m: normalize_link(None, m.group("url").strip()), text_normalized)
    
    # Final Cleanup
    text_normalized = enforce_no_nested_or_duplicate_links(text_normalized)
    text_normalized = collapse_blank_lines(text_normalized)

    # --- STEP 4: DECIDE TO SKIP OR FORMAT ---
    line_count = len(text_normalized.strip().splitlines())
    has_http = "http" in text_normalized
    
    # If it's short, return immediately
    if line_count < 3 and not has_http:
         for ph, email in email_map.items():
            text_normalized = text_normalized.replace(ph, email)
            
         logger.info("Skipping heavy formatting for short response.")
         payload_json = json.dumps({"content": text_normalized})
         return {"messages": [AIMessage(content=payload_json)]}

    # --- STEP 5: HEAVY FORMATTING ---
    llm = get_groq_llm()
    formatted = llm.invoke(HUMAN_FORMATTING_PROMPT_TEMPLATE.format(question=question, normalized=text_normalized))
    final_text = strip_one_fence(str(formatted.content))

    # Restore Bare Emails (Plain text)
    for ph, email in email_map.items():
        final_text = final_text.replace(ph, email)

    payload_json = json.dumps({"content": final_text})
    print(f"Final response: {final_text}")
    return {"messages": [AIMessage(content=payload_json)]}

# --- 7. GRAPH CONSTRUCTION ---
graph = StateGraph(State)
graph.add_node("Run LLM with Tools", run_llm_with_tools)
graph.add_node("tools", ToolNode(tools))
graph.add_node("Format Response", format_response)

graph.add_edge(START, "Run LLM with Tools")
graph.add_conditional_edges("Run LLM with Tools", tools_condition)
graph.add_edge("tools", "Format Response")
graph.add_edge("Format Response", END)

memory_saver = MemorySaver()
main_graph = graph.compile(checkpointer=memory_saver)