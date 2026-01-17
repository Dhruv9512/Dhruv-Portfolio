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

  // Logic to clean up Href (kept from your original code)
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
    const displayLabel = textStr && textStr.trim() !== "" ? textStr : "Visit";
    
    return `<a href="${chosenHref}" target="_blank"${titleAttr} data-href="${chosenHref}" class="chat-link btn btn-primary">${displayLabel}</a>`;
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

// --- WebSocket Setup ---
// Generate a unique thread ID for the session (non-persistent)
const threadId = `session-${Math.random().toString(36).substr(2, 9)}`;
console.log("Current Session ID:", threadId);

// Determine protocol (ws or wss)
const socketProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const chatSocket = new WebSocket(
    socketProtocol + window.location.host + '/ws/chat/' + threadId + '/'
);

let botMessageBuffer = ""; 
let currentBotMessageDiv = null;

chatSocket.onopen = function(e) {
    console.log("WebSocket connected.");
};

chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);

    // --- 1. Remove Loading Indicator on first real token ---
    const loadingDiv = document.getElementById("loading-message");
    if (loadingDiv && (data.type === 'token' || data.type === 'done')) {
        loadingDiv.remove();
    }

    // --- 2. Handle Stream Tokens ---
    if (data.type === 'token') {
        // Create the bot message bubble if it doesn't exist yet
        if (!currentBotMessageDiv) {
            currentBotMessageDiv = createBotMessageBubble();
        }
        
        botMessageBuffer += data.content;
        
        // Render Markdown immediately
        currentBotMessageDiv.innerHTML = convertMarkdownToHTML(botMessageBuffer);
        
        // Auto-scroll
        const messagesContainer = document.getElementById("chatbot-messages");
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } 
    // --- 3. Handle Status Logs ---
    else if (data.type === 'log') {
        // Optional: Update a status bar instead of console
        console.log("Luffy Log:", data.content);
    }
    // --- 4. Handle Completion ---
    else if (data.type === 'done') {
        console.log("Stream complete.");
        botMessageBuffer = ""; 
        currentBotMessageDiv = null; // Reset for next turn
        hideLoading(); // Re-enable inputs
    }
    // --- 5. Handle Errors ---
    else if (data.type === 'error') {
        if (loadingDiv) loadingDiv.remove();
        addMessage("bot", `❌ *Error:* ${data.content}`);
        hideLoading();
    }
};

chatSocket.onclose = function(e) {
    console.error('Chat socket closed unexpectedly');
    // Optional: Attempt reconnect logic here
};

// --- UI Helper Functions ---

function createBotMessageBubble() {
    const messagesContainer = document.getElementById("chatbot-messages");
    const outerDiv = document.createElement("div");
    outerDiv.className = "flex items-start gap-3";
    
    const img = document.createElement("img");
    img.className = "w-10 h-10 flex-shrink-0 rounded-full";
    img.src = "/static/index/img/cheatboaticon.gif";
    img.alt = "MyBoat icon";
    
    const messageDiv = document.createElement("div");
    messageDiv.className = "message bot-message p-3 rounded-lg shadow-md";
    
    outerDiv.appendChild(img);
    outerDiv.appendChild(messageDiv);
    messagesContainer.appendChild(outerDiv);
    
    return messageDiv;
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

  if (sender === "user") {
    messageDiv.textContent = payload; // User messages are plain text
    outerDiv.appendChild(messageDiv);
    messagesContainer.appendChild(outerDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  } else {
    // Static bot messages (like errors)
    messageDiv.innerHTML = convertMarkdownToHTML(payload);
    const img = document.createElement("img");
    img.className = "w-10 h-10 flex-shrink-0 rounded-full";
    img.src = "/static/index/img/cheatboaticon.gif";
    
    outerDiv.appendChild(img);
    outerDiv.appendChild(messageDiv);
    messagesContainer.appendChild(outerDiv);
  }
}

function sendMessage() {
  const userInput = document.getElementById("user-input");
  const messageText = userInput.value.trim();
  
  if (messageText) {
    // 1. Add User Message to UI
    addMessage("user", messageText);
    userInput.value = "";
    
    // 2. Show Loading Indicator
    showLoadingMessage();

    // 3. Disable Inputs
    const sendButton = document.getElementById("send-button");
    userInput.disabled = true;
    sendButton.disabled = true;
    sendButton.classList.add("loading");

    // 4. Send via WebSocket (with slight delay for UI feel)
    setTimeout(() => {
        if (chatSocket.readyState === WebSocket.OPEN) {
            chatSocket.send(JSON.stringify({
                'message': messageText
            }));
        } else {
            console.error("WebSocket is not open.");
            addMessage("bot", "❌ Connection lost. Please refresh.");
            hideLoading();
            const loadingDiv = document.getElementById("loading-message");
            if(loadingDiv) loadingDiv.remove();
        }
    }, 100);
  }
}

function hideLoading() {
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

// Global Exports
window.sendMessage = sendMessage;
window.handleKeyPress = handleKeyPress;

// Initialization
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