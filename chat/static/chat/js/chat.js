// Function to hide the chat icon and footer
window.onload = function() {
    const chat = document.getElementById('open-chat');
    const footer = document.querySelector('.main_footer');
    if (chat && footer) {
        chat.style.display = 'none'; 
        footer.style.display = 'none';
    }
};

// Function to send a message
async function fetchdata(messageText) {
    try {
        console.log('Sending message:', messageText);

        const response = await fetch('https://dhruv-portfolio-chatbot.onrender.com/api/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: messageText })
        });

        if (!response.ok) {
            throw new Error(`Network response was not ok. Status: ${response.status}`);
        }

        const data = await response.json();
        console.log('API response:', data);

        if (data.response) {
            addMessage('bot', data.response); 
        } else {
            addMessage('bot', 'Bot did not return a response.');
        }
    } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
        addMessage('bot', 'Sorry, there was an error.'); // Show error to user
    } finally {
        hideLoading(); // Optional loading animation
        document.getElementById('user-input').disabled = false;
    }
}


// Function to send a message
function sendMessage() {
    console.log("sendMessage function called");
    const userInput = document.getElementById('user-input');
    const messageText = userInput.value.trim(); // Correct variable name
    console.log('Sending message:', messageText);
    
    if (messageText) {
        // Add user message to chat immediately
        adduserMessage(messageText); 
        
        // Clear input field
        userInput.value = ''; 
        
        // Show loading indicator
        showLoading(); 
        
        // Disable the input field to prevent multiple sends
        userInput.disabled = true; 
        
        // Call fetchdata to send the message to the API
        setTimeout(() => {
            fetchdata(messageText); 
        }, 1000);
    }
}

// Function to handle key press for sending message
function adduserMessage(text) {
    const messagesContainer = document.getElementById('chatbot-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message user-message`;
    messageDiv.textContent = text;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight; 
}

// Function to add a message to the boat chat
function addMessage(text) {
    const main = document.createElement('div');
    main.className = 'd-flex wh-100 row';

    const messagesContainer = document.getElementById('chatbot-messages');
    messagesContainer.appendChild(main);

    const img = document.createElement('img');
    img.className = 'col-2 myboat-icon';
    img.src = '/static/index/img/cheatboaticon.gif';
    img.alt = 'MyBoat icon';
    main.appendChild(img);

    const messageDiv = document.createElement('div');
    messageDiv.className = `message bot-message`;
    messageDiv.textContent = text;
    main.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight; 
}

// Function that create a loader
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
// Function to show loading indicator
function showLoading() {
    createLoader();
}

// Function to hide loading indicator
function hideLoading() {
    const loadingDiv = document.querySelector('.main_div');
    loadingDiv.remove();
}

// Function to handle key press for sending message
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage(); // Send message on Enter key press
    }
}

// Function to toggle chat visibility
function toggleChat() {
    const chatbotContainer = document.querySelector('.chatbot-container');
    chatbotContainer.style.display = chatbotContainer.style.display === 'none' ? 'flex' : 'none';
}
