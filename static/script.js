class ChatUI {
    constructor() {
        this.messageList = document.getElementById('messageList');
        this.userInput = document.getElementById('userInput');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.setupEventListeners();
        this.loadHistory();
    }

    setupEventListeners() {
        this.userInput.addEventListener('input', this.autoResize.bind(this));
        this.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    autoResize() {
        this.userInput.style.height = 'auto';
        this.userInput.style.height = this.userInput.scrollHeight + 'px';
    }

    async sendMessage() {
        const message = this.userInput.value.trim();
        if (!message) return;

        this.addMessage(message, 'user');
        this.showTypingIndicator();
        this.userInput.value = '';
        this.autoResize();

        try {
            const response = await this.fetchAIResponse(message);
            this.addMessage(response, 'bot');
            this.saveHistory();
        } catch (error) {
            this.addMessage('Извините, произошла ошибка. Попробуйте еще раз.', 'bot');
        } finally {
            this.hideTypingIndicator();
        }
    }

    async fetchAIResponse(message) {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message })
        });

        if (!response.ok) throw new Error('API Error');
        const data = await response.json();
        return this.formatResponse(data.response);
    }

    formatResponse(text) {
        // Базовая обработка Markdown
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
    }

    addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = text;

        if (sender === 'user') {
            contentDiv.innerHTML += `<div class="message-time">${this.getCurrentTime()}</div>`;
        }

        messageDiv.appendChild(contentDiv);
        this.messageList.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showTypingIndicator() {
        this.typingIndicator.classList.add('active');
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.typingIndicator.classList.remove('active');
    }

    scrollToBottom() {
        this.messageList.scrollTop = this.messageList.scrollHeight;
    }

    getCurrentTime() {
        return new Date().toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    saveHistory() {
        const history = this.messageList.innerHTML;
        localStorage.setItem('chatHistory', history);
    }

    loadHistory() {
        const history = localStorage.getItem('chatHistory');
        if (history) {
            this.messageList.innerHTML = history;
            this.scrollToBottom();
        }
    }
}

// Инициализация чата
const chat = new ChatUI();
window.sendMessage = () => chat.sendMessage();