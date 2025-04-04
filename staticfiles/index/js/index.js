// Function to change navbar style on scroll
window.onscroll = function() {
    // Check if we are on the home page
    if (window.location.pathname === '/' || window.location.pathname === '/home.html') {
        const navbar = document.querySelector('.navbar');
        if (document.body.scrollTop > 40 || document.documentElement.scrollTop > 40) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    }
};

// Function to toggle the chat window
function toggleChat() {
    $('#chatbotModal').modal('toggle'); // Toggle the modal
}

// Function to send a message
function sendMessage() {
    const userInput = document.getElementById('user-input');
    const messageText = userInput.value.trim();
    if (messageText) {
        addMessage('user', messageText);
        userInput.value = '';
        // Simulate bot response
        setTimeout(() => {
            addMessage('bot', 'Thank you for your message! I will get back to you shortly.');
        }, 1000);
    }
}

// Function to handle key press events
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
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
