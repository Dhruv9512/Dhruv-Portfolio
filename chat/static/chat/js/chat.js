// Function to hide the chat icon
window.onload = function() {
    const chat = document.getElementById('open-chat');
    if (chat) {
        chat.style.display = 'none'; 
    }

    const footer = document.querySelector('.main_footer');
    if (footer) {
        footer.style.display = 'none';
    }
};

// Function to send a message
async function fetchdata(messageText) {
    try {
        console.log('Sending message:', messageText); // Log the message to send
        
        const response = await fetch('api/', {
            method: 'POST', // Use POST method to send data
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: messageText }) // Send user message
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json(); // Wait for the JSON data to be parsed
        console.log(data); // Handle the data returned from the API

        // Assuming the bot's response is in data.response
        addMessage('bot', data.response); // Add bot response to chat
    } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
        addMessage('bot', 'Sorry, there was an error.'); // Add error message
    } finally {
        hideLoading(); // Hide loading indicator
    }
}

function sendMessage() {
    console.log("sendMessage function called");
    const userInput = document.getElementById('user-input');
    const messageText = userInput.value.trim(); // Correct variable name
    console.log('Sending message:', messageText);
    if (messageText) {
        addMessage('user', messageText); // Add user message to chat
        userInput.value = ''; // Clear input field
        showLoading(); // Show loading indicator

        fetchdata(messageText); // Use the correct variable here
    }
}

// Function to add a message to the chat
function addMessage(sender, text) {
    const messagesContainer = document.getElementById('chatbot-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    messageDiv.textContent = text;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight; // Scroll to the bottom
}

// Function to show loading indicator
function showLoading() {
    const loadingDiv = document.getElementById('loading');
    loadingDiv.style.display = 'block'; // Show loading
}

// Function to hide loading indicator
function hideLoading() {
    const loadingDiv = document.getElementById('loading');
    loadingDiv.style.display = 'none'; // Hide loading
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