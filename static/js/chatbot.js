// Floating Chatbot Widget
(function() {
    let chatWidget = null;
    let isOpen = false;
    let chatHistory = [];

    function createChatWidget() {
        // Create container
        chatWidget = document.createElement('div');
        chatWidget.id = 'chatbotWidget';
        chatWidget.innerHTML = `
            <div class="chatbot-toggle" id="chatbotToggle" onclick="toggleChatbot()">
                <span class="chatbot-icon">🤖</span>
                <span class="chatbot-badge" id="chatbotBadge" style="display: none;">1</span>
            </div>
            <div class="chatbot-container" id="chatbotContainer" style="display: none;">
                <div class="chatbot-header">
                    <div class="chatbot-header-content">
                        <span class="chatbot-icon-header">🤖</span>
                        <div>
                            <h3>Agriculture Assistant</h3>
                            <p>Ask about farming, crops, or schemes</p>
                        </div>
                    </div>
                    <button class="chatbot-close" onclick="toggleChatbot()">×</button>
                </div>
                <div class="chatbot-messages" id="chatbotMessages">
                    <div class="chatbot-message bot">
                        <div class="message-content">
                            Hello! I'm your agriculture assistant. How can I help you today?
                        </div>
                    </div>
                </div>
                <div class="chatbot-input-container">
                    <input 
                        type="text" 
                        id="chatbotInput" 
                        placeholder="Ask about crops, diseases, schemes..."
                        autocomplete="off"
                    >
                    <button class="chatbot-send" id="chatbotSend" onclick="sendChatMessage()">
                        <span>➤</span>
                    </button>
                </div>
            </div>
        `;

        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            #chatbotWidget {
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 1000;
                font-family: 'Inter', sans-serif;
            }

            .chatbot-toggle {
                width: 60px;
                height: 60px;
                background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                box-shadow: 0 4px 20px rgba(46, 204, 113, 0.4);
                transition: transform 0.3s;
                position: relative;
            }

            .chatbot-toggle:hover {
                transform: scale(1.1);
            }

            .chatbot-icon {
                font-size: 28px;
            }

            .chatbot-badge {
                position: absolute;
                top: -5px;
                right: -5px;
                background: #e74c3c;
                color: white;
                border-radius: 50%;
                width: 22px;
                height: 22px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                font-weight: bold;
            }

            .chatbot-container {
                position: absolute;
                bottom: 80px;
                right: 0;
                width: 380px;
                height: 500px;
                background: white;
                border-radius: 16px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                display: flex;
                flex-direction: column;
                overflow: hidden;
                animation: slideUp 0.3s ease-out;
            }

            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .chatbot-header {
                background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
                color: white;
                padding: 1rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .chatbot-header-content {
                display: flex;
                gap: 12px;
                align-items: center;
            }

            .chatbot-icon-header {
                font-size: 32px;
            }

            .chatbot-header h3 {
                font-size: 1.1rem;
                margin: 0;
                font-weight: 600;
            }

            .chatbot-header p {
                font-size: 0.8rem;
                margin: 0;
                opacity: 0.9;
            }

            .chatbot-close {
                background: rgba(255, 255, 255, 0.2);
                border: none;
                color: white;
                width: 32px;
                height: 32px;
                border-radius: 50%;
                font-size: 20px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.3s;
            }

            .chatbot-close:hover {
                background: rgba(255, 255, 255, 0.3);
            }

            .chatbot-messages {
                flex: 1;
                padding: 1rem;
                overflow-y: auto;
                background: #f9f9f9;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .chatbot-message {
                display: flex;
                animation: fadeIn 0.3s ease-in;
            }

            @keyframes fadeIn {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .chatbot-message.user {
                justify-content: flex-end;
            }

            .chatbot-message.bot {
                justify-content: flex-start;
            }

            .message-content {
                max-width: 75%;
                padding: 10px 14px;
                border-radius: 12px;
                word-wrap: break-word;
                line-height: 1.4;
                font-size: 0.9rem;
            }

            .chatbot-message.user .message-content {
                background: #2ecc71;
                color: white;
                border-bottom-right-radius: 4px;
            }

            .chatbot-message.bot .message-content {
                background: white;
                color: #333;
                border: 1px solid #e0e0e0;
                border-bottom-left-radius: 4px;
            }

            .typing-indicator {
                display: flex;
                gap: 4px;
                padding: 10px 14px;
            }

            .typing-dot {
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background: #999;
                animation: typing 1.4s infinite;
            }

            .typing-dot:nth-child(2) {
                animation-delay: 0.2s;
            }

            .typing-dot:nth-child(3) {
                animation-delay: 0.4s;
            }

            @keyframes typing {
                0%, 60%, 100% {
                    transform: translateY(0);
                }
                30% {
                    transform: translateY(-8px);
                }
            }

            .chatbot-input-container {
                padding: 1rem;
                background: white;
                border-top: 1px solid #e0e0e0;
                display: flex;
                gap: 8px;
                align-items: center;
            }

            #chatbotInput {
                flex: 1;
                padding: 10px 14px;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                font-size: 0.9rem;
                outline: none;
                transition: border-color 0.3s;
            }

            #chatbotInput:focus {
                border-color: #2ecc71;
            }

            .chatbot-send {
                background: #2ecc71;
                color: white;
                border: none;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.3s;
                font-size: 18px;
            }

            .chatbot-send:hover {
                background: #27ae60;
            }

            .chatbot-send:disabled {
                background: #ccc;
                cursor: not-allowed;
            }

            @media (max-width: 768px) {
                .chatbot-container {
                    width: calc(100vw - 40px);
                    height: calc(100vh - 120px);
                    bottom: 100px;
                    right: 20px;
                    max-height: 70vh;
                }

                #chatbotWidget {
                    bottom: 100px;
                    right: 15px;
                }

                .chatbot-toggle {
                    width: 55px;
                    height: 55px;
                }

                .chatbot-icon {
                    font-size: 24px;
                }
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(chatWidget);

        // Add enter key listener
        const input = document.getElementById('chatbotInput');
        if (input) {
            input.addEventListener('keypress', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendChatMessage();
                }
            });
        }
    }

    // Toggle chatbot
    window.toggleChatbot = function() {
        if (!chatWidget) {
            createChatWidget();
        }
        
        const container = document.getElementById('chatbotContainer');
        const toggle = document.getElementById('chatbotToggle');
        
        isOpen = !isOpen;
        
        if (isOpen) {
            container.style.display = 'flex';
            setTimeout(() => {
                const input = document.getElementById('chatbotInput');
                if (input) input.focus();
            }, 100);
            // Hide badge when opened
            const badge = document.getElementById('chatbotBadge');
            if (badge) badge.style.display = 'none';
        } else {
            container.style.display = 'none';
        }
    };

    // Send message
    window.sendChatMessage = async function() {
        const input = document.getElementById('chatbotInput');
        const sendButton = document.getElementById('chatbotSend');
        const messagesContainer = document.getElementById('chatbotMessages');
        
        const message = input.value.trim();
        if (!message) return;

        // Add user message
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'chatbot-message user';
        userMessageDiv.innerHTML = `<div class="message-content">${escapeHtml(message)}</div>`;
        messagesContainer.appendChild(userMessageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Clear input and disable
        input.value = '';
        sendButton.disabled = true;
        sendButton.innerHTML = '<span>⏳</span>';

        // Show typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chatbot-message bot';
        typingDiv.id = 'chatbotTyping';
        typingDiv.innerHTML = `
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    target_language: selectedLanguageName()
                })
            });

            const data = await response.json();

            // Remove typing indicator
            const typing = document.getElementById('chatbotTyping');
            if (typing) typing.remove();

            const botMessageDiv = document.createElement('div');
            botMessageDiv.className = 'chatbot-message bot';
            const replyText = data.response || data.error || 'Sorry, I encountered an error. Please try again.';
            botMessageDiv.innerHTML = `<div class="message-content">${formatBotMessage(replyText)}</div>`;
            messagesContainer.appendChild(botMessageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } catch (error) {
            const typing = document.getElementById('chatbotTyping');
            if (typing) typing.remove();
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'chatbot-message bot';
            
            // Fallback response when API is unavailable
            const fallbackResponse = `I apologize, but I'm temporarily unable to process your request. Here's some general farming advice:

**Common Farming Practices:**
- Monitor your crop regularly for early pest and disease detection
- Maintain proper soil moisture through appropriate irrigation
- Apply fertilizers based on soil testing results
- Rotate crops annually to maintain soil health
- Follow recommended pesticide safety guidelines

**Government Support:**
- Contact your local agriculture office for scheme eligibility
- PM-KISAN offers ₹6,000/year for most farmers
- Crop insurance schemes protect against weather damage
- Subsidies available for equipment and seeds

For specific advice, please try again or contact your local agriculture extension officer. 🌾`;
            
            errorDiv.innerHTML = `<div class="message-content">${formatBotMessage(fallbackResponse)}</div>`;
            messagesContainer.appendChild(errorDiv);
            console.error('Chatbot error:', error);
        } finally {
            sendButton.disabled = false;
            sendButton.innerHTML = '<span>➤</span>';
            input.focus();
        }
    };

    // Escape HTML to prevent XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function selectedLanguageName() {
        const lang = localStorage.getItem('selectedLanguage') || document.getElementById('languageSelect')?.value || 'en';
        return window.AgroVisionTranslate?.languageName ? window.AgroVisionTranslate.languageName(lang) : lang;
    }

    function formatBotMessage(text) {
        return escapeHtml(text || '')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }

    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createChatWidget);
    } else {
        createChatWidget();
    }
})();
