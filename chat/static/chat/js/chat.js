// Hide chat icon and footer on page load
window.onload = function () {
    const chat = document.getElementById('open-chat');
    const footer = document.querySelector('.main_footer');
    if (chat && footer) {
        chat.style.display = 'none';
        footer.style.display = 'none';
    }
};

// Send message to backend API and handle response
async function fetchdata(messageText) {
    try {
        console.log('Sending message:', messageText);

        const response = await fetch('/chat/api/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: messageText })
        });

        if (!response.ok) {
            throw new Error(`Status ${response.status}`);
        }

        const data = await response.json();
        console.log('Raw API response:', data);

        const botResponse = data?.response?.trim();

        if (botResponse) {
            const lowerResp = botResponse.toLowerCase();

            if (lowerResp.includes("429") && lowerResp.includes("quota")) {
                addMessage('bot', `🚫 *Gemini API quota exceeded.*\nTry again later or check limits: [Gemini Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)`);
            } else {
                addMessage('bot', botResponse);
            }
        } else {
            addMessage('bot', '❗ Bot did not return a valid response. Please try rephrasing your question.');
        }

    } catch (error) {
        console.error('Fetch error:', error);
        addMessage('bot', `❌ *Server Error:* ${error.message || 'Something went wrong. Please try again later.'}`);
    } finally {
        hideLoading();
        document.getElementById('user-input').disabled = false;
    }
}

// Send message triggered by user action
function sendMessage() {
    const userInput = document.getElementById('user-input');
    const messageText = userInput.value.trim();

    if (messageText) {
        adduserMessage(messageText);
        userInput.value = '';
        showLoading();
        userInput.disabled = true;

        setTimeout(() => {
            fetchdata(messageText);
        }, 1000);
    }
}

// Add user message to chat UI
function adduserMessage(text) {
    const messagesContainer = document.getElementById('chatbot-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    messageDiv.textContent = text;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Add bot or user message to chat UI with Markdown and buttons
function addMessage(sender, text) {
    const main = document.createElement('div');
    main.className = 'd-flex wh-100 row';

    const messagesContainer = document.getElementById('chatbot-messages');
    messagesContainer.appendChild(main);

    if (sender === 'bot') {
        const img = document.createElement('img');
        img.className = 'col-2 myboat-icon';
        img.src = '/static/index/img/cheatboaticon.gif';
        img.alt = 'MyBoat icon';
        main.appendChild(img);
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    if (sender === 'bot') {
        messageDiv.innerHTML = convertMarkdownToHTML(text);
    } else {
        messageDiv.textContent = text;
    }

    main.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Convert Markdown to HTML with bullet points and buttons
function convertMarkdownToHTML(markdownText) {
    // Convert **bold**
    let html = markdownText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Convert *italic* (not list bullets)
    html = html.replace(/(^|[^\\])\*(?!\s)(.*?)\*/g, '$1<em>$2</em>');

    const lines = html.split('\n');
    let result = '<ul>';
    for (let line of lines) {
        line = line.trim();

        // Match Markdown-style [Label](URL) link with bullet
        const match = line.match(/^\*\s*\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/);
        if (match) {
            const label = match[1];
            const url = match[2];
            result += `
                <li>
                    <a href="${url}" target="_blank" style="text-decoration: none;">
                        <button class="btn btn-sm btn-primary" style="margin: 5px 0;">${label}</button>
                    </a>
                </li>`;
        } else if (line.startsWith('* ')) {
            // Handle regular bullet points
            const text = line.substring(2).trim();
            result += `<li>${text}</li>`;
        } else if (line !== '') {
            // Paragraph or line
            result += `<p>${line}</p>`;
        }
    }
    result += '</ul>';
    return result;
}


// Show loading indicator
function showLoading() {
    createLoader();
}

// Hide loading indicator
function hideLoading() {
    const loadingDiv = document.querySelector('.main_div');
    if (loadingDiv) loadingDiv.remove();
}

// Create loader element
function createLoader() {
    const main = document.createElement('div');
    main.className = 'd-flex wh-100 row main_div align-items-center';

    const messagesContainer = document.getElementById('chatbot-messages');
    messagesContainer.appendChild(main);

    const img = document.createElement('img');
    img.className = 'col-2 myboat-icon mb-3';
    img.src = '/static/index/img/cheatboaticon.gif';
    img.alt = 'MyBoat icon';
    main.appendChild(img);

    const messageDiv = document.createElement('div');
    messageDiv.id = 'loading';
    main.appendChild(messageDiv);

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Handle Enter key
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// Toggle chat visibility
function toggleChat() {
    const chatbotContainer = document.querySelector('.chatbot-container');
    chatbotContainer.style.display = chatbotContainer.style.display === 'none' ? 'flex' : 'none';
}
