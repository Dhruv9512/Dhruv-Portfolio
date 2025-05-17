// Hide chat icon and footer on page load
window.onload = function() {
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

        const response = await fetch('https://dhruv-portfolio-chatbot.onrender.com/api/', {
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
                addMessage('bot', `🚫 *Gemini API quota exceeded.*\nTry again later or check limits: https://ai.google.dev/gemini-api/docs/rate-limits`);
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
    console.log("sendMessage function called");
    const userInput = document.getElementById('user-input');
    const messageText = userInput.value.trim();
    console.log('Sending message:', messageText);

    if (messageText) {
        adduserMessage(messageText); // Show user message
        userInput.value = '';        // Clear input field
        showLoading();               // Show loader
        userInput.disabled = true;   // Disable input to prevent spam

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

// Add bot message to chat UI
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
    messageDiv.textContent = text;
    main.appendChild(messageDiv);

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Create loader element for loading animation
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

// Show loading indicator
function showLoading() {
    createLoader();
}

// Hide loading indicator
function hideLoading() {
    const loadingDiv = document.querySelector('.main_div');
    if (loadingDiv) loadingDiv.remove();
}

// Handle "Enter" key press for sending message
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// Toggle chatbot visibility on screen
function toggleChat() {
    const chatbotContainer = document.querySelector('.chatbot-container');
    chatbotContainer.style.display = chatbotContainer.style.display === 'none' ? 'flex' : 'none';
}
