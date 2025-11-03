// ------------- Marked setup -------------
marked.use({
  gfm: true,
  breaks: true,
});

const renderer = new marked.Renderer();

// --- Helper Functions ---
function toStr(v) {
  return typeof v === "string" ? v : v == null ? "" : String(v);
}
function isAllowedHref(href) {
  return /^(https?:|mailto:|ftp:)/i.test(href);
}

// Token-aware custom link renderer
renderer.link = function (tokenOrHref, title, text) {
  let hrefStr, titleStr, textStr;

  if (tokenOrHref && typeof tokenOrHref === "object" && "href" in tokenOrHref) {
    hrefStr = toStr(tokenOrHref.href);
    titleStr = toStr(tokenOrHref.title);
    textStr = typeof text === "string" ? text : toStr(tokenOrHref.text);
  } else {
    hrefStr = toStr(tokenOrHref);
    titleStr = toStr(title);
    textStr = toStr(text);
  }

  const titleAttr = titleStr ? ` title="${titleStr}"` : "";
  let chosenHref = hrefStr;

  if (!isAllowedHref(chosenHref)) {
    const t = toStr(textStr);
    let m = /\[[^\]]+\]\((https?:\/\/[^\s)]+)\)/i.exec(t);
    if (m && isAllowedHref(m[1])) {
      chosenHref = m[1];
    } else {
      m = /(https?:\/\/[^\s)]+)/i.exec(t);
      if (m && isAllowedHref(m[1])) {
        chosenHref = m[1];
      }
    }
  }

  if (isAllowedHref(chosenHref)) {
    return `<a href="${chosenHref}" target="_blank"${titleAttr} data-href="${chosenHref}" class="chat-link btn btn-primary">Visit</a>`;
  }

  const label = textStr || "Invalid link";
  return `<span class="chat-link invalid-link"${titleAttr}>${label}</span>`;
};

// Markdown processing functions
function normalizeMarkdownLinks(md) {
  return md.replace(/\]\s+\(\s*(https?:\/\/[^)\s]+)\s*\)/g, "]($1)");
}

function convertMarkdownToHTML(markdownText) {
  const fixed = normalizeMarkdownLinks(markdownText);
  return marked.parse(fixed, { renderer });
}

// --- Chat UI Functions ---
function typeMessageWithLLM(
  element,
  llmJson,
  index = 0,
  speed = 300,
  onComplete = null
) {
  if (element._typingTimer) {
    clearTimeout(element._typingTimer);
    element._typingTimer = null;
  }

  const rawText =
    llmJson && typeof llmJson.content === "string" ? llmJson.content : "";
  const scrollContainer = element.closest(".chatbot-messages");

  const scrollToBottom = () => {
    if (scrollContainer)
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
  };

  if (index < rawText.length) {
    element.innerHTML = convertMarkdownToHTML(rawText.substring(0, index + 1));
    scrollToBottom();
    element._typingTimer = setTimeout(() => {
      typeMessageWithLLM(element, llmJson, index + 1, speed, onComplete);
    }, speed);
  } else {
    element.innerHTML = convertMarkdownToHTML(rawText);
    scrollToBottom();
    if (typeof onComplete === "function") onComplete();
  }
}

function showLoadingMessage() {
  const messagesContainer = document.getElementById("chatbot-messages");
  const outerDiv = document.createElement("div");
  outerDiv.className = "flex items-start gap-3 loading-indicator";
  outerDiv.id = "loading-message";
  const img = document.createElement("img");
  img.className = "w-10 h-10 flex-shrink-0 rounded-full";
  img.src = "/static/index/img/cheatboaticon.gif";
  img.alt = "MyBoat icon";
  const messageDiv = document.createElement("div");
  messageDiv.className = "message p-3 rounded-lg shadow-md";
  messageDiv.textContent = "...";
  outerDiv.appendChild(img);
  outerDiv.appendChild(messageDiv);
  messagesContainer.appendChild(outerDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addMessage(sender, payload) {
  const messagesContainer = document.getElementById("chatbot-messages");
  const outerDiv = document.createElement("div");
  outerDiv.className = `flex items-start gap-3 ${
    sender === "user" ? "justify-end" : ""
  }`;
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${sender}-message p-3 ${
    sender === "bot" ? "bot-message" : ""
  }`;

  if (sender === "bot") {
    // FIXED: Remove the '...' loader right before adding the bot message
    const loadingDiv = document.getElementById("loading-message");
    if (loadingDiv) loadingDiv.remove();

    const img = document.createElement("img");
    img.className = "w-10 h-10 flex-shrink-0 rounded-full";
    img.src = "/static/index/img/cheatboaticon.gif";
    img.alt = "MyBoat icon";
    outerDiv.appendChild(img);
    outerDiv.appendChild(messageDiv);
    messagesContainer.appendChild(outerDiv);
    
    // The loading state is now handled by hideLoading in the callback
    typeMessageWithLLM(messageDiv, payload, 0, 1, () => {
        hideLoading(); // This will re-enable inputs and remove the loading class
    });
  } else {
    messageDiv.textContent = payload;
    outerDiv.appendChild(messageDiv);
    messagesContainer.appendChild(outerDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }
}

let threadId = `thread_${Date.now()}_${Math.floor(Math.random() * 100000)}`;

async function fetchdata(messageText) {
  try {
    const response = await fetch("/chat/api/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: messageText, thread_id: threadId }),
    });

    let data;
    try {
      data = await response.json();
    } catch (e) {
      console.error("Response is not JSON:", e);
      addMessage("bot", { content: "❗ Server returned a non-JSON response." });
      return;
    }

    const botPayloadString = data?.response;
    let botPayload;

    if (typeof botPayloadString === "string") {
      const trimmed = botPayloadString.trim();
      if (trimmed.startsWith("{")) {
        try {
          botPayload = JSON.parse(trimmed);
        } catch (e) {
          console.error("Failed to parse bot payload JSON:", e);
          botPayload = { content: trimmed };
        }
      } else {
        botPayload = { content: trimmed };
      }
    } else {
      console.error("Received a non-string payload:", botPayloadString);
      botPayload = {
        content: "❗ I received an unexpected response. Please try again.",
      };
    }

    if (typeof botPayload !== "object" || botPayload === null) {
      botPayload = { content: String(botPayload ?? "") };
    }
    if (!("content" in botPayload) || typeof botPayload.content !== "string") {
      botPayload.content = String(botPayload.content ?? "");
    }

    addMessage("bot", botPayload);
  } catch (error) {
    // FIXED: Ensure the '...' loader is removed on error
    const loadingDiv = document.getElementById("loading-message");
    if (loadingDiv) loadingDiv.remove();
    
    // Also re-enable the inputs on error
    hideLoading();

    addMessage("bot", {
      content: `❌ *Server Error:* ${error.message || "Something went wrong."}`,
    });
  }
  // FIXED: Removed the 'finally' block that was causing the loader to disappear too soon.
}

function sendMessage() {
  const userInput = document.getElementById("user-input");
  const messageText = userInput.value.trim();
  if (messageText) {
    addMessage("user", messageText);
    userInput.value = "";
    showLoadingMessage();

    // FIXED: Unify the loading state logic
    const sendButton = document.getElementById("send-button");
    userInput.disabled = true;
    sendButton.disabled = true;
    sendButton.classList.add("loading"); // Add a class to style the button

    setTimeout(() => {
      fetchdata(messageText);
    }, 300);
  }
}

function hideLoading() {
  // FIXED: This function now reverses the state set in sendMessage
  const sendButton = document.getElementById("send-button");
  const userInput = document.getElementById("user-input");
  
  sendButton.classList.remove("loading");
  sendButton.disabled = false;
  userInput.disabled = false;
  userInput.focus();
}

function handleKeyPress(event) {
  if (event.key === "Enter") {
    sendMessage();
  }
}

window.sendMessage = sendMessage;
window.handleKeyPress = handleKeyPress;

document.addEventListener("DOMContentLoaded", function () {
  const chat = document.getElementById("open-chat");
  const footer = document.getElementById("main_footer");
  if (chat) chat.style.display = "none";
  if (footer) footer.style.display = "none";
  const main = document.querySelector("main");
  if (main) main.classList.remove("min-h-screen");
  setTimeout(() => {
    const main = document.querySelector("main");
    const chatbotCard = document.querySelector(".chatbot-card");
    if (main && chatbotCard) {
      main.style.height = `${chatbotCard.offsetHeight}px`;
    }
  }, 0);
});
