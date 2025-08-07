// Hide chat icon and footer on page load
// Hide chat icon and footer on page load
document.addEventListener('DOMContentLoaded', function () {
    const chat = document.getElementById('open-chat');
    const footer = document.getElementById('main_footer');
    if (chat) {
        chat.style.display = 'none';
    }
    if (footer) {
        footer.style.display = 'none';
    }

    const main = document.querySelector('main');
    if (main) {
        main.classList.remove('min-h-screen');
    }
    
    // Set the height of the main tag to match the chatbot card
    setTimeout(() => {
        const main = document.querySelector('main');
        const chatbotCard = document.querySelector('.chatbot-card');
        if (main && chatbotCard) {
            main.style.height = `${chatbotCard.offsetHeight}px`;
        }
    }, 0);
});

// [ rest of your existing JavaScript functions ]

async function fetchdata(messageText) {
    try {
        const response = await fetch('/chat/api/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: messageText })
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
    } finally {
        hideLoading();
        document.getElementById('user-input').disabled = false;
        document.getElementById('user-input').focus();
    }
}

function sendMessage() {
    const userInput = document.getElementById('user-input');
    const messageText = userInput.value.trim();
    if (messageText) {
        addMessage('user', messageText);
        userInput.value = '';
        showLoading();
        userInput.disabled = true;
        setTimeout(() => { fetchdata(messageText); }, 1000);
    }
}

function addMessage(sender, text) {
    const messagesContainer = document.getElementById('chatbot-messages');
    const outerDiv = document.createElement('div');
    outerDiv.className = `flex items-start gap-3 ${sender === 'user' ? 'justify-end' : ''}`;
    
    if (sender === 'bot') {
        const img = document.createElement('img');
        img.className = 'w-10 h-10 flex-shrink-0 rounded-full';
        img.src = '/static/index/img/cheatboaticon.gif';
        img.alt = 'MyBoat icon';
        outerDiv.appendChild(img);
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message p-3 rounded-lg shadow-md`;
    if (sender === 'bot') {
        messageDiv.innerHTML = convertMarkdownToHTML(text);
    } else {
        messageDiv.textContent = text;
    }
    outerDiv.appendChild(messageDiv);
    
    messagesContainer.appendChild(outerDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function convertMarkdownToHTML(markdownText) {
    let html = markdownText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/(^|[^\\])\*(?!\s)(.*?)\*/g, '$1<em>$2</em>');
    
    const lines = html.split('\n');
    let result = '';
    let inList = false;

    for (let line of lines) {
        line = line.trim();
        const match = line.match(/^\*\s*\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/);
        if (match) {
            if (!inList) { result += '<ul>'; inList = true; }
            const label = match[1];
            const url = match[2];
            result += `<li><a href="${url}" target="_blank" style="text-decoration: none;"><button class="btn btn-sm btn-primary" style="margin: 5px 0; background-color: #0d9488; color: white; border: none; padding: 8px 12px; border-radius: 5px; cursor: pointer;">${label}</button></a></li>`;
        } else if (line.startsWith('* ')) {
            if (!inList) { result += '<ul>'; inList = true; }
            const text = line.substring(2).trim();
            result += `<li>${text}</li>`;
        } else if (line !== '') {
            if (inList) { result += '</ul>'; inList = false; }
            result += `<p>${line}</p>`;
        }
    }
    if (inList) { result += '</ul>'; }
    return result;
}

function showLoading() {
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

function hideLoading() {
    const loadingDiv = document.getElementById('loading-message');
    if (loadingDiv) loadingDiv.remove();
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}