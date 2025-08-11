// === Marked.js custom renderer to render links as buttons ===
const renderer = new marked.Renderer();

renderer.link = function(href, title, text) {
  return `<a href="${href}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;">
            <button class="btn btn-sm btn-primary" style="margin:5px 0; background-color:#0d9488; color:white; border:none; padding:8px 12px; border-radius:5px; cursor:pointer;">
              ${text}
            </button>
          </a>`;
};

// === Converts markdown text to HTML using marked.js and custom renderer ===
function convertMarkdownToHTML(markdownText) {
    return marked.parse(markdownText, { renderer });
}

// === Typing effect that renders markdown as HTML character-by-character ===
function typeMessage(element, rawText, index = 0, speed = 20, onComplete = null) {
    if (index < rawText.length) {
        const currentText = rawText.substring(0, index + 1);
        element.innerHTML = convertMarkdownToHTML(currentText);
        element.parentElement.parentElement.scrollTop = element.parentElement.parentElement.scrollHeight;

        setTimeout(() => typeMessage(element, rawText, index + 1, speed, onComplete), speed);
    } else {
        element.parentElement.parentElement.scrollTop = element.parentElement.parentElement.scrollHeight;
        if (typeof onComplete === "function") {
            onComplete();
        }
    }
}

// === Shows loading spinner message ===
function showLoadingMessage() {
    const messagesContainer = document.getElementById('chatbot-messages');
    const outerDiv = document.createElement('div');
    outerDiv.className = 'flex items-start gap-3 loading-indicator';
    outerDiv.id = 'loading-message';

    const img = document.createElement('img');
    img.className = 'w-10 h-10 flex-shrink-0 rounded-full';
    img.src = '/static/index/img/cheatboaticon.gif';
    img.alt = 'MyBoat icon';

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message p-3 rounded-lg shadow-md';
    messageDiv.textContent = '...';

    outerDiv.appendChild(img);
    outerDiv.appendChild(messageDiv);
    messagesContainer.appendChild(outerDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// === Adds a chat message to the UI ===
function addMessage(sender, text) {
    const messagesContainer = document.getElementById('chatbot-messages');
    const outerDiv = document.createElement('div');
    outerDiv.className = `flex items-start gap-3 ${sender === 'user' ? 'justify-end' : ''}`;

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message p-3 rounded-lg shadow-md`;

    if (sender === 'bot') {
        const img = document.createElement('img');
        img.className = 'w-10 h-10 flex-shrink-0 rounded-full';
        img.src = '/static/index/img/cheatboaticon.gif';
        img.alt = 'MyBoat icon';
        outerDiv.appendChild(img);

        outerDiv.appendChild(messageDiv);
        messagesContainer.appendChild(outerDiv);

        // Disable input and show spinner
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');
        userInput.disabled = true;
        sendButton.classList.add('loading'); // add loading spinner CSS class
        sendButton.disabled = true;

        // Start typing, enable input after done
        typeMessage(messageDiv, text, 0, 20, () => {
            userInput.disabled = false;
            sendButton.classList.remove('loading');
            sendButton.disabled = false;
            userInput.focus();
            hideLoading();
        });
    } else {
        // For user messages, just plain text (no markdown)
        messageDiv.textContent = text;
        outerDiv.appendChild(messageDiv);
        messagesContainer.appendChild(outerDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// === Fetch data from backend API ===
let threadId = `thread_${Date.now()}_${Math.floor(Math.random() * 100000)}`;

async function fetchdata(messageText) {
    try {
        const response = await fetch('/chat/api/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: messageText , thread_id: threadId })
        });
        const data = await response.json();
        const botResponse = data?.response?.trim();
        if (botResponse) {
            if (botResponse.toLowerCase().includes("429") && botResponse.toLowerCase().includes("quota")) {
                addMessage('bot', `🚫 *Gemini API quota exceeded.*\nTry again later or check limits: [Gemini Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)`);
            } else {
                addMessage('bot', botResponse);
            }
        } else {
            addMessage('bot', '❗ Bot did not return a valid response. Please try rephrasing your question.');
        }
    } catch (error) {
        addMessage('bot', `❌ *Server Error:* ${error.message || 'Something went wrong. Please try again later.'}`);
    } finally{
        const loadingDiv = document.getElementById('loading-message');
        if (loadingDiv) loadingDiv.remove();
    }
}

// === Send message handler ===
function sendMessage() {
    const userInput = document.getElementById('user-input');
    const messageText = userInput.value.trim();
    if (messageText) {
        addMessage('user', messageText);
        userInput.value = '';

        showLoadingMessage();

        userInput.disabled = true;
        document.getElementById('send-button').classList.add('hidden');
        document.getElementById('input-loading').classList.remove('hidden');

        setTimeout(() => { fetchdata(messageText); }, 1000);
    }
}

// === Hide loading spinner and enable input ===
function hideLoading() {
    document.getElementById('send-button').classList.remove('hidden');
    document.getElementById('input-loading').classList.add('hidden');

    const userInput = document.getElementById('user-input');
    userInput.disabled = false;
    userInput.focus();
}

// === Handle Enter key for sending message ===
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// === Initial setup: hide chat icon/footer, adjust height ===
document.addEventListener('DOMContentLoaded', function () {
    const chat = document.getElementById('open-chat');
    const footer = document.getElementById('main_footer');
    if (chat) chat.style.display = 'none';
    if (footer) footer.style.display = 'none';

    const main = document.querySelector('main');
    if (main) main.classList.remove('min-h-screen');

    setTimeout(() => {
        const main = document.querySelector('main');
        const chatbotCard = document.querySelector('.chatbot-card');
        if (main && chatbotCard) {
            main.style.height = `${chatbotCard.offsetHeight}px`;
        }
    }, 0);
});
