import re
import json
from typing import List, Tuple, Dict
from langchain_core.messages import AIMessage

# --- Constants ---
ALLOWED_SCHEMES = ("https://", "http://", "ftp://", "tel:")
MD_LINK_RE = re.compile(r"\[([^\]\n]{1,200})\]\(([^()\s]{1,2048})\)")
NESTED_LINK_RE = re.compile(r"\[[^\]]*\]\([^()]*\)\s*\([^()]*\)")
DUPLICATE_URL_AFTER_RE = re.compile(r"\]\([^()]*\)\s*\((?:https?|mailto|ftp|tel):[^()]*\)")
BARE_URL_RE = re.compile(r"(?P<url>(?:https?://|http://|ftp://|tel:)[^\s<>()\[\]{}\"'`,;]+)")

# --- Helper Functions ---

def is_allowed_absolute_url(url: str) -> bool:
    return any(url.startswith(s) for s in ALLOWED_SCHEMES)

def is_null_url(url: str) -> bool:
    return url.strip().lower() in ["[https://null.com](https://null.com)", "https://null.com"]

def normalize_link(text, url, url_to_title): 
    if is_null_url(url): 
        return f"{url_to_title.get(url, 'Link')}: Link not available"
    if not is_allowed_absolute_url(url): 
        return ""
    
    title = url_to_title.get(url) or (text if text else "Link")
    if title == "": title = "Link"
    return f"{title}: [Visit]({url})"

def text_normalized(text, url_to_title):
    # Applies normalization to markdown links and bare URLs
    text_norm = MD_LINK_RE.sub(lambda m: normalize_link(m.group(1).strip(), m.group(2).strip(), url_to_title), text)
    text_norm = BARE_URL_RE.sub(lambda m: normalize_link(None, m.group("url").strip(), url_to_title), text_norm)
    return text_norm
        
def sanitize_email(raw_answer):    
    raw_answer = re.sub(r"\[.*?\]\(mailto:([^)]+)\)", r"\1", raw_answer, flags=re.IGNORECASE)
    raw_answer = re.sub(r"mailto:", "", raw_answer, flags=re.IGNORECASE)
    return raw_answer

def clean_history(messages: list) -> list:
    """Helper: Extracts raw English content from JSON-wrapped AIMessages."""
    cleaned_history = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.content.strip().startswith('{'):
            try:
                payload = json.loads(msg.content)
                cleaned_history.append(AIMessage(content=payload.get("memory_english", "")))
            except:
                cleaned_history.append(msg)
        else:
            cleaned_history.append(msg)
    return cleaned_history

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