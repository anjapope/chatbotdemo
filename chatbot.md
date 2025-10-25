---
layout: page
title: Chatbot Program
permalink: /chatbot/
---

# Interactive Chatbot Demo

<style>
.chatbot-container {
    max-width: 600px;
    margin: 40px auto;
    border: 1px solid #ddd;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.chatbot-header {
    background-color: #2196F3;
    color: white;
    padding: 20px;
    text-align: center;
}

.chatbot-messages {
    height: 400px;
    overflow-y: auto;
    padding: 20px;
    background-color: #f5f5f5;
}

.message {
    margin-bottom: 15px;
    display: flex;
}

.message.user {
    justify-content: flex-end;
}

.message.bot {
    justify-content: flex-start;
}

.message-bubble {
    max-width: 70%;
    padding: 10px 15px;
    border-radius: 15px;
    word-wrap: break-word;
}

.message.user .message-bubble {
    background-color: #2196F3;
    color: white;
}

.message.bot .message-bubble {
    background-color: white;
    color: #333;
    border: 1px solid #ddd;
}

.chatbot-input-area {
    padding: 15px;
    background-color: white;
    border-top: 1px solid #ddd;
}

.chatbot-input {
    display: flex;
    gap: 10px;
}

.chatbot-input input {
    flex: 1;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 20px;
    font-size: 14px;
}

.chatbot-input button {
    padding: 10px 20px;
    background-color: #2196F3;
    color: white;
    border: none;
    border-radius: 20px;
    cursor: pointer;
    font-size: 14px;
}

.chatbot-input button:hover {
    background-color: #1976D2;
}

.quick-replies {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
}

.quick-reply-btn {
    padding: 8px 15px;
    background-color: white;
    border: 1px solid #2196F3;
    color: #2196F3;
    border-radius: 15px;
    cursor: pointer;
    font-size: 13px;
}

.quick-reply-btn:hover {
    background-color: #E3F2FD;
}
</style>

<div class="chatbot-container">
    <div class="chatbot-header">
        <h2 style="margin: 0;">Training Assistant</h2>
        <p style="margin: 5px 0 0 0; font-size: 14px;">Ask me about chatbot design!</p>
    </div>
    
    <div class="chatbot-messages" id="chatMessages">
        <div class="message bot">
            <div class="message-bubble">
                Hi! I'm your chatbot design training assistant. I can help you learn about conversation design, user experience, and implementation strategies. What would you like to know?
            </div>
        </div>
    </div>
    
    <div class="chatbot-input-area">
        <div class="quick-replies" id="quickReplies">
            <button class="quick-reply-btn" onclick="sendQuickReply('What is a chatbot?')">What is a chatbot?</button>
            <button class="quick-reply-btn" onclick="sendQuickReply('Conversation design tips')">Conversation tips</button>
            <button class="quick-reply-btn" onclick="sendQuickReply('UX best practices')">UX best practices</button>
            <button class="quick-reply-btn" onclick="sendQuickReply('How to implement?')">Implementation</button>
        </div>
        <div class="chatbot-input">
            <input type="text" id="userInput" placeholder="Type your message..." onkeypress="handleKeyPress(event)">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>
</div>

<script>
// Knowledge base for the chatbot
const knowledgeBase = {
    'what is a chatbot': 'A chatbot is a software application designed to simulate human conversation through text or voice interactions. It uses natural language processing to understand user inputs and provide appropriate responses. Visit the <a href="/modules/introduction">Introduction module</a> to learn more!',
    'types of chatbots': 'There are three main types: Rule-Based Chatbots (following predefined rules), AI-Powered Chatbots (using machine learning), and Hybrid Chatbots (combining both approaches). Each has its strengths depending on the use case.',
    'conversation design': 'Good conversation design involves being clear and concise, setting expectations, maintaining context, and handling errors gracefully. Check out the <a href="/modules/conversation-design">Conversation Design module</a> for detailed principles!',
    'conversation tips': 'Key tips include: writing for conversation (not documentation), testing with real users, iterating based on feedback, planning for unexpected inputs, and maintaining a consistent personality. Keep messages short and focused!',
    'user experience': 'Chatbot UX focuses on discoverability (helping users understand what the bot can do), providing feedback, error prevention and recovery, and ensuring accessibility. Learn more in the <a href="/modules/user-experience">User Experience module</a>!',
    'ux best practices': 'Best practices include: providing clear feedback, using quick reply buttons, keeping interfaces clean, supporting multiple input methods, and testing with real users. Always make it easy for users to understand what the chatbot can do.',
    'implementation': 'Implementation involves choosing a technology stack (like Dialogflow, Rasa, or Microsoft Bot Framework), setting up NLP, dialog management, and integrations. Visit the <a href="/modules/implementation">Implementation module</a> for detailed guidance!',
    'how to implement': 'Start by choosing your platform (cloud-based like Dialogflow, open source like Rasa, or low-code tools). Then set up NLP for intent recognition, design conversation flows, integrate with your systems, and test thoroughly before deployment.',
    'platforms': 'Popular chatbot platforms include Dialogflow (Google), Amazon Lex, Microsoft Bot Framework, and Rasa (open source). Each has different strengths - cloud platforms are easier to start with, while open source gives you more control.',
    'testing': 'Test your chatbot through usability testing, A/B testing, and analytics review. Key metrics include task completion rate, error rate, and user satisfaction. Always test with real users before launch!',
    'help': 'I can help you learn about: chatbot basics, conversation design, user experience, implementation strategies, testing, and best practices. Try asking specific questions or use the quick reply buttons above!',
    'hello': 'Hello! I\'m here to help you learn about chatbot design. What would you like to know? You can ask about conversation design, user experience, implementation, or any other aspect of chatbot development.',
    'hi': 'Hi there! Ready to learn about chatbot design? Feel free to ask me anything about creating effective chatbots!',
    'thanks': 'You\'re welcome! Is there anything else you\'d like to know about chatbot design?',
    'thank you': 'My pleasure! Feel free to ask if you have more questions about chatbot design and development.'
};

function addMessage(text, isUser) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'bot'}`;
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    
    // Use textContent for user messages to prevent XSS, innerHTML only for bot responses with links
    if (isUser) {
        bubbleDiv.textContent = text;
    } else {
        bubbleDiv.innerHTML = text;
    }
    
    messageDiv.appendChild(bubbleDiv);
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function getBotResponse(userMessage) {
    const normalizedMessage = userMessage.toLowerCase().trim();
    
    // Check for exact or partial matches
    for (const [key, value] of Object.entries(knowledgeBase)) {
        if (normalizedMessage.includes(key)) {
            return value;
        }
    }
    
    // Default response
    return 'That\'s an interesting question! While I don\'t have a specific answer for that, I can help you learn about chatbot design fundamentals. Try asking about conversation design, user experience, or implementation. You can also explore the <a href="/modules/introduction">training modules</a> for comprehensive information!';
}

function sendMessage() {
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    
    if (message === '') return;
    
    // Add user message
    addMessage(message, true);
    input.value = '';
    
    // Simulate bot "thinking"
    setTimeout(() => {
        const response = getBotResponse(message);
        addMessage(response, false);
    }, 500);
}

function sendQuickReply(message) {
    addMessage(message, true);
    
    setTimeout(() => {
        const response = getBotResponse(message);
        addMessage(response, false);
    }, 500);
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}
</script>

## About This Demo

This is a simple demonstration chatbot that showcases basic chatbot functionality. It uses a rule-based approach with a knowledge base to answer questions about chatbot design.

### Features Demonstrated:
- **Message interface** with user and bot messages
- **Quick reply buttons** for common questions
- **Text input** for free-form questions
- **Context-aware responses** based on keywords
- **Fallback handling** for unrecognized inputs

### Learning Points:
1. **User Interface**: Clean, conversational design that's easy to use
2. **Input Methods**: Both text input and quick replies for flexibility
3. **Response Strategy**: Keyword matching with graceful fallbacks
4. **Visual Feedback**: Clear distinction between user and bot messages

This is a simplified example. Production chatbots typically use more sophisticated NLP and machine learning for better understanding and more natural conversations.

### Try Building Your Own!

Now that you've seen a working example and learned about chatbot design principles, you're ready to build your own chatbot. Review the [training modules](/modules/introduction) for comprehensive guidance on creating effective, user-friendly chatbots.
