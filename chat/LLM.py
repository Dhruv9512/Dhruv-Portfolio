import os
import re
import ast
import json
import logging
import nest_asyncio
from typing import Annotated, Dict, Any, List, TypedDict
from dotenv import load_dotenv

# LangChain / LangGraph Imports
from langchain_core.messages import SystemMessage, AIMessage, AnyMessage,HumanMessage
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_qdrant import QdrantVectorStore
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from qdrant_client import QdrantClient

# Helper Function
from .utility import *

# --- Setup ---
nest_asyncio.apply()
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- System Prompt ---
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

IMPORTANT:
- The user might misspell "Dhruv" or use a translated version like "Dulub", "Durubu", "Druv". 
- ALWAYS assume they are talking about "Dhruv Sharma" if the name is even slightly similar.
- Do not refuse to answer just because of a typo in the name.

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

analysis_prompt = """
Analyze the following user text: "{content}"
            
Task:
1. Detect the language name.
2. Translate the text to English.

CRITICAL CONTEXT:
- The user is chatting with a bot about a person named "Dhruv Sharma".
- If the user writes a name in their native script that sounds phonetically similar to "Dhruv", "Durubu", "Daruvu", or "Sharma", you MUST translate it as "Dhruv Sharma".
- Correct any phonetic misspellings of "Dhruv Sharma" in the translation.
            
Return ONLY a valid JSON object:
{{
    "detected_language": "Language Name",
    "translated_text": "Text in English"
}}
"""

Re_Ranking_Prompt = """
You are a relevance filter. 
User Query: "{query}"
        
Below are several text snippets from a portfolio. 
Analyze them and return the IDs of the snippets that contain DIRECT answers to the query.
Ignore snippets that are vague or unrelated.
        
Snippets:
{joined_docs}
        
Return ONLY a list of integer IDs (e.g., [0, 2, 5]). If none are relevant, return [].
"""


short_trans_prompt ="""
Translate the following text to {user_language}.
Maintain the persona of Luffy.
text: {text_normalized}
"""


translation_prompt = """
You are Luffy (from One Piece). Translate the following Markdown content to: "{user_language}".

RULES:
1. **Accurate Translation**: Translate the meaning accurately into the native script of {user_language} (e.g., use Kanji/Kana for Japanese).
2. **Technical Terms**: Keep technical names (like "Python", "Django", "Render", "Vercel", "GitHub") in English.
3. **Formatting**: PRESERVE the Markdown structure (Headers, Bullet points, Links) exactly.
4. **URL Safety**: Do NOT translate or change URLs inside `( )`.

Content to Translate:
{final_text}
"""


# ----------------------------------LangGrapg State Class-------------------------
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    language: str

# --------------------------------My chatbot class----------------------------
class MyChatbot:
    def __init__(self,message:str,config:dict=None):
        self.messages = message
        self.config = config
        self.main_graph = None
        self.tools = None
        self.llm_with_tools = None
        self.memory_saver = MemorySaver()
        self.GroqLLM =  ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2, groq_api_key=os.environ.get("GROQ_API_KEY"))
        self.GeminiLLm=ChatGoogleGenerativeAI(model="gemini-1.5-flash",temperature=0.2,google_api_key=os.environ.get("GOOGLE_API_KEY"))
        self.embedder =  HuggingFaceEndpointEmbeddings(model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.qdrantClient= QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

    # Main Fuction That create and call the build graph
    async def build(self):
        
        # build graph
        self.main_graph = self._buildGraph()
        
        # call the graph using astream_event()
        async for event in self._stream_response():
            yield event
        
    # -------------------------------- Buld Graph Method create nodes and graph flows--------------------------------
    def _buildGraph(self) -> StateGraph:
        
        self.tools = [self._qdrant_rag_tool]
        self.llm_with_tools = self.GroqLLM.bind_tools(self.tools)

        # Create Node
        graph = StateGraph(State)
        graph.add_node("Run LLM with Tools", self._run_llm_with_tools)
        graph.add_node("tools", ToolNode(self.tools))
        graph.add_node("Format Response", self._format_response)
        graph.add_node("handle_chit_chat", self._handle_chit_chat)

        # Create Graph Flow 
        graph.add_edge(START, "Run LLM with Tools")
        graph.add_conditional_edges(
            "Run LLM with Tools",
            self._route_after_llm,
            {
                "tools": "tools",       
                "handle_chit_chat": "handle_chit_chat" 
            }
        )
        graph.add_edge("tools", "Format Response")
        graph.add_edge("Format Response", END)
        graph.add_edge("handle_chit_chat", END)

        
        return graph.compile(checkpointer=self.memory_saver)
    
    # -----------------------------------Stream Response method that invoke the graph and stream the response-----------------------------------
    async def _stream_response(self):
        async for event in self.main_graph.astream_events(
            {"messages": self.messages}, 
            config=self.config, 
            version="v1"
        ):
            kind = event["event"]
            node_name = event['metadata'].get('langgraph_node', '')
            tags = event.get("tags", [])

            # --- STREAMING FILTER LOGIC ---
            
            # Case A: Main LLM (Typing "Hy", "Hello")
            if kind == "on_chat_model_stream" and node_name == "Run LLM with Tools" and "response_stream" in tags:
                content = event["data"]["chunk"].content
                if content:
                    yield {
                        "type": "token",
                        "content": content
                    }

            # Case B: Final Formatted Output (RAG)
            elif kind == "on_chat_model_stream" and "response_stream" in tags:
                content = event["data"]["chunk"].content
                if content:
                    yield {
                        "type": "token",
                        "content": content
                    }

            # Case C: Logs (Searching...)
            elif kind == "on_tool_start":
                yield {
                    "type": "log",
                    "content": f"Searching: {event['name']}..."
                }
        
        # Signal completion
        yield {"type": "done"}
    
    # -----------------------------------Methods that are used in Graph as par the graph flow-------------------------
    # 1. Call llm with tools
    async def _run_llm_with_tools(self,state: State):
        messages = state["messages"]
        
        last_human_msg_index = -1
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], HumanMessage):
                last_human_msg_index = i
                break
                
        detected_language = "English" # Default
        
        if last_human_msg_index != -1:
            last_message = messages[last_human_msg_index]
            llm = self.GroqLLM
            
            try:
                analysis_prompt_formatted = analysis_prompt.format(content=last_message.content)
                response = await llm.ainvoke(analysis_prompt_formatted).content
                cleaned_json = strip_one_fence(response)
                data = json.loads(cleaned_json)
                
                detected_language = data.get("detected_language", "English")
                english_text = data.get("translated_text", last_message.content)
                
                logger.info(f"Detected: {detected_language}, English: {english_text}")
                
                messages[last_human_msg_index] = HumanMessage(content=english_text)
                
            except Exception as e:
                logger.error(f"Preprocessing error: {e}")
                detected_language = "English"

        # --- CLEAN HISTORY FOR LLM ---
        cleaned_history = clean_history(messages)
        
        # --- INVOKE LLM ---
        all_messages = [SystemMessage(content=SYSTEM_PROMPT)] + cleaned_history
        response_msg = await self.llm_with_tools.ainvoke(
            all_messages, 
            config={"tags": ["response_stream"]}
        )
        return {
            "messages": [response_msg],
            "language": detected_language
        }
        
    # 2. If llm with tool don't call the tool then this method get call
    async def _handle_chit_chat(self,state: State) -> Dict[str, Any]:
        """Handles simple conversation with standard translation."""
        last_message = state['messages'][-1]
        user_language = state.get("language", "English")
        english_content = last_message.content

        # Simple Translation only if needed
        if user_language and user_language.lower() != "english":
            llm = self.GroqLLM
            prompt = f"Translate the following text to {user_language}:\n\n{english_content}" 
            final_content = await llm.ainvoke(prompt,config={"tags": ["response_stream"]}).content
        else:
            final_content = english_content

        # Return valid JSON for your frontend
        payload = json.dumps({
            "content": final_content,
            "memory_english": english_content
        })
        
        return {"messages": [AIMessage(content=payload)]}
    # 2. If llm with tool ,call qdrant_rag_tool that give documents from Vector DB
    async def _qdrant_rag_tool(self,query: str) -> str:
        """Searches Dhruv Sharma's portfolio content using vector similarity."""
        
        logger.info(f"User query: {query}")
        
        # Extract the categories of query
        categories = await self._extract_categories_with_gemini(query)
        if not categories: return "No matching category found in portfolio."

        all_context_docs = []

        # ---- Fetch the Document from vectorer DB ----
        for collection in categories:
            try:
                store = QdrantVectorStore(client=self.qdrantClient, collection_name=collection, embedding=self.embedder)
                # Increased k to 10 to gather more candidates
                retriever = store.as_retriever(search_type="mmr", search_kwargs={"k": 10, "fetch_k": 30, "lambda_mult": 0.5})
                docs = await retriever.ainvoke(query)
                all_context_docs.extend(docs)
            except Exception as e:
                logger.error(f"Error retrieving from {collection}: {e}")
        
        # Doing Some validation and Creating Join Documents
        if not all_context_docs: return "No relevant information found in portfolio."
        doc_text_list = [f"ID {i}: {d.page_content.strip()}" for i, d in enumerate(all_context_docs) if d.page_content.strip()]
        joined_docs = "\n\n".join(doc_text_list)
        if not joined_docs: return "No relevant information found."

        #---- LLM-Based Re-ranking / Filtering ---- 
        try:
            llm_check = self.GroqLLM
            check_prompt = Re_Ranking_Prompt.format(query=query, joined_docs=joined_docs)
            check_response = await llm_check.ainvoke(check_prompt).content
            relevant_ids = [int(num) for num in re.findall(r'\d+', check_response)]
            
            # Filter the docs based on LLM selection
            relevant_content = [all_context_docs[i].page_content.strip() for i in relevant_ids if i < len(all_context_docs)]
            
            # Fallback: if LLM says "none", but we have docs, take the top 3 just in case
            if not relevant_content:
                relevant_content = [d.page_content.strip() for d in all_context_docs[:5]]           
        except Exception as e:
            logger.error(f"Re-ranking error: {e}. Falling back to raw retrieval.")
            relevant_content = [d.page_content.strip() for d in all_context_docs[:5]]

        combined_context = "\n\n".join(set(relevant_content))
        
        #---- Final Answer Generation ----
        llm = self.GroqLLM
        answer = await llm.ainvoke(FILTER_PROMPT_TEMPLATE.format(query=query, combined_context=combined_context)).content
        return answer

    # 3.format_response that give final formated ans
    async def _format_response(self,state: State) -> Dict[str, Any]:
        raw_answer = state['messages'][-1].content
        user_language = state.get("language", "English")
        
        # --- SANITIZE EMAILS ---
        raw_answer = sanitize_email(raw_answer)
        try:
            payload = json.loads(raw_answer)
            if isinstance(payload, dict) and "content" in payload: return {"messages": [AIMessage(content=raw_answer)]}
        except: pass

        question = next((msg.content for msg in reversed(state['messages']) if isinstance(msg, HumanMessage)), "")
        
        # --- PRE-PROCESSING ---
        cleaned_text = enforce_no_nested_or_duplicate_links(strip_one_fence(raw_answer))
        
        # Handle URLs and Titles
        urls = [u for u in collect_urls_in_text(cleaned_text) if not is_null_url(u)]
        titles = await self._llm_generate_titles_helper(urls)
        url_to_title = dict(zip(urls, titles))
        # --- LINK NORMALIZATION ---
        normalized_content = text_normalized(cleaned_text, url_to_title)
        normalized_content = enforce_no_nested_or_duplicate_links(normalized_content)
        normalized_content = collapse_blank_lines(normalized_content)
        
        # --- DECIDE TO SKIP OR FORMAT ---
        line_count = len(normalized_content.strip().splitlines())
        has_http = "http" in normalized_content
        llm = self.GroqLLM
        
        # Short response path
        if line_count < 3 and not has_http:
            logger.info("Skipping heavy formatting for short response.")
            
            if user_language and user_language.lower() != "english":
                
                short_trans_prompt_formatted = short_trans_prompt.format(user_language=user_language, text_normalized=normalized_content)
                translated_short = await llm.ainvoke(short_trans_prompt_formatted).content
                payload_json = json.dumps({"content": translated_short, "memory_english": normalized_content})
                return {"messages": [AIMessage(content=payload_json)]}
            else:
                payload_json = json.dumps({"content": normalized_content})
                return {"messages": [AIMessage(content=payload_json)]}

        # --- HEAVY FORMATTING ---
        formatted = await llm.ainvoke(HUMAN_FORMATTING_PROMPT_TEMPLATE.format(question=question, normalized=normalized_content),config={"tags": ["response_stream"]} )
        final_text = strip_one_fence(str(formatted.content))
        
        # Translate to the User's Language
        if user_language and user_language.lower() != "english":
            translation_prompt_formatted = translation_prompt.format(user_language=user_language, final_text=final_text)
            translated_content = await llm.ainvoke(translation_prompt_formatted).content
            
            # Fallback if translation failed (returned empty or broken content)
            if len(translated_content) < len(final_text) * 0.2: 
                logger.warning("Translation seemed to fail (content too short). Reverting to English.")
                translated_content = final_text
        else:
            translated_content = final_text
            
        payload = json.dumps({
            "content": translated_content, 
            "memory_english": final_text
        })
        return {"messages": [AIMessage(content=payload)]}


    # ------------------------------------Helper Class Methods-------------------------- 
    # Extract the categories of query
    async def _extract_categories_with_gemini(self,query: str) -> list[str]:
        categories_list = ["about me", "certification", "education_marks_academic", "resume", "skill", "work_experience_and_internships", "projectwork"]
        prompt = CATEGORY_PROMPT_TEMPLATE.format(query=query, categories_list=categories_list)
        
        try:
            model = self.GroqLLM
            response = await model.ainvoke(prompt)
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

    # Method that Generate Title 
    async def _llm_generate_titles_helper(self,urls: List[str]) -> List[str]:
        if not urls: return []
        llm = self.GroqLLM
        input_list = "\n".join(f"{i+1}) {u}" for i, u in enumerate(urls))
        prompt = TITLE_GENERATION_PROMPT.format(n=len(urls), input_list=input_list)
        resp = await llm.ainvoke(prompt)
        content = strip_one_fence(str(resp.content))
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        return [lines[i] if i < len(lines) else "Link" for i in range(len(urls))]

    # Method that decide where to go based on tool calls
    def _route_after_llm(self,state: State) -> str:
        """Decides where to go based on tool calls."""
        last_message = state["messages"][-1]
        
        # If the LLM wants to use a tool, go to the tool node
        if last_message.tool_calls:
            return "tools"
            
        # If NO tool call, go to the chit-chat handler
        return "handle_chit_chat"