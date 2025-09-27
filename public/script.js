class WhatsAppWebClone {
    constructor() {
        this.socket = io();
        this.currentChat = null;
        this.messages = [];
        this.chats = [];

        this.initializeElements();
        this.setupEventListeners();
        this.setupSocketListeners();
    }

    initializeElements() {
        this.qrSection = document.getElementById('qrSection');
        this.chatInterface = document.getElementById('chatInterface');
        this.qrCode = document.getElementById('qrCode');
        this.connectionStatus = document.getElementById('connectionStatus');
        this.messageForm = document.getElementById('messageForm');
        this.phoneNumberInput = document.getElementById('phoneNumber');
        this.messageInput = document.getElementById('messageInput');
        this.messagesContainer = document.getElementById('messagesContainer');
        this.chatList = document.getElementById('chatList');
        this.refreshChatsBtn = document.getElementById('refreshChats');
        this.currentChatInfo = document.getElementById('currentChatInfo');
        this.toastContainer = document.getElementById('toastContainer');
        this.hideQrBtn = document.getElementById('hideQrBtn');
        this.showQrBtn = document.getElementById('showQrBtn');
        this.viewLogsBtn = document.getElementById('viewLogsBtn');
        this.logsModal = document.getElementById('logsModal');
        this.closeLogsModal = document.getElementById('closeLogsModal');
        this.logsStatus = document.getElementById('logsStatus');
        this.logsContent = document.getElementById('logsContent');
        this.logsList = document.getElementById('logsList');
        this.logViewer = document.getElementById('logViewer');
        this.backToLogsList = document.getElementById('backToLogsList');
        this.currentLogFile = document.getElementById('currentLogFile');
        this.logFileContent = document.getElementById('logFileContent');
    }

    setupEventListeners() {
        this.messageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        this.refreshChatsBtn.addEventListener('click', () => {
            this.loadChats();
        });

        this.hideQrBtn.addEventListener('click', () => {
            this.hideQRSection();
        });

        this.showQrBtn.addEventListener('click', () => {
            this.showQRSection();
        });

        this.viewLogsBtn.addEventListener('click', () => {
            this.openLogsModal();
        });

        this.closeLogsModal.addEventListener('click', () => {
            this.closeLogsModalHandler();
        });

        this.backToLogsList.addEventListener('click', () => {
            this.showLogsList();
        });

        // Close modal when clicking outside
        this.logsModal.addEventListener('click', (e) => {
            if (e.target === this.logsModal) {
                this.closeLogsModalHandler();
            }
        });
    }

    setupSocketListeners() {
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.updateConnectionStatus('Connected', true);
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.updateConnectionStatus('Disconnected', false);
        });

        this.socket.on('qr', (qrData) => {
            console.log('QR code received');
            this.displayQRCode(qrData);
        });

        this.socket.on('ready', (data) => {
            console.log('WhatsApp client ready:', data);
            this.showChatInterface();
            this.hideQRSection(); // Auto-hide QR when connected
            this.showToast('WhatsApp connected successfully! You can show the QR code again using the button in the top-right corner.', 'success');
            this.loadChats();
        });

        this.socket.on('authenticated', (message) => {
            console.log('Authenticated:', message);
            this.showToast('Authentication successful!', 'success');
        });

        this.socket.on('auth_failure', (message) => {
            console.error('Authentication failed:', message);
            this.showToast('Authentication failed. Please try again.', 'error');
        });

        this.socket.on('disconnected', (reason) => {
            console.log('WhatsApp disconnected:', reason);
            this.showQRSection();
            this.showToast('WhatsApp disconnected. Please scan QR code again.', 'error');
        });

        this.socket.on('message', (messageData) => {
            console.log('New message:', messageData);
            this.addMessage(messageData, false);
            this.showToast(`New message from ${messageData.sourceName}`, 'success');
        });

        this.socket.on('messageSent', (data) => {
            console.log('Message sent:', data);
            this.addMessage({
                body: data.body,
                timestamp: Date.now(),
                sourceName: `You ${data.targetName || ''}`,
                contact: { name: 'You', number: 'You' },
                from: 'You'
            }, true);
            this.showToast(`Message sent successfully ${data.targetName || ''}!`, 'success');
            this.messageInput.value = '';
        });

        this.socket.on('chats', (chatData) => {
            console.log('Chats received:', chatData);
            this.chats = chatData;
            this.displayChats();
        });

        this.socket.on('error', (error) => {
            console.error('Socket error:', error);
            this.showToast(error, 'error');
        });
    }

    updateConnectionStatus(status, isConnected) {
        this.connectionStatus.textContent = status;
        this.connectionStatus.className = `status ${isConnected ? 'connected' : 'disconnected'}`;
    }

    displayQRCode(qrData) {
        this.qrCode.innerHTML = `<img src="${qrData}" alt="QR Code" />`;
    }

    showQRSection() {
        this.qrSection.classList.remove('hidden');
        this.showQrBtn.classList.add('hidden');
        console.log('Showing QR section');
    }

    hideQRSection() {
        this.qrSection.classList.add('hidden');
        this.showQrBtn.classList.remove('hidden');
        console.log('Hiding QR section');
    }

    showChatInterface() {
        this.chatInterface.classList.remove('hidden');
        console.log('Showing chat interface');
        // Don't automatically hide QR section - let user control it
    }

    sendMessage() {
        const phoneNumber = this.phoneNumberInput.value.trim();
        const message = this.messageInput.value.trim();

        if (!phoneNumber || !message) {
            this.showToast('Please enter both phone number and message', 'error');
            return;
        }

        // Clean phone number (remove any non-digits except +)
        const cleanNumber = phoneNumber.replace(/[^\d+]/g, '');

        this.socket.emit('sendMessage', {
            number: cleanNumber,
            message: message
        });

        this.showToast('Sending message...', 'success');
    }

    addMessage(messageData, isOutgoing = false) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${isOutgoing ? 'outgoing' : 'incoming'}`;

        const timestamp = new Date(messageData.timestamp).toLocaleTimeString();
        // Use sourceName if available, otherwise fall back to contact name
        const senderName = messageData.sourceName ||
                          (isOutgoing ? 'You' : (messageData.contact?.name || messageData.contact?.number || 'Unknown'));

        // Check if it's a group message for styling
        const isGroupMessage = messageData.isGroupMsg || (messageData.sourceName && messageData.sourceName.includes(' in '));
        const messageInfoClass = isGroupMessage ? 'message-info group-message' : 'message-info';

        messageElement.innerHTML = `
            <div class="${messageInfoClass}">${this.escapeHtml(senderName)}</div>
            <div class="message-body">${this.escapeHtml(messageData.body)}</div>
            <div class="message-time">${timestamp}</div>
        `;

        // Remove welcome message if it exists
        const welcomeMessage = this.messagesContainer.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }

        this.messagesContainer.appendChild(messageElement);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

        this.messages.push(messageData);
    }

    loadChats() {
        this.socket.emit('getChats');
        this.chatList.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Loading chats...</p>
            </div>
        `;
    }

    displayChats() {
        if (this.chats.length === 0) {
            this.chatList.innerHTML = `
                <div class="loading">
                    <p>No chats found</p>
                </div>
            `;
            return;
        }

        this.chatList.innerHTML = '';

        this.chats.forEach(chat => {
            const chatElement = document.createElement('div');
            chatElement.className = 'chat-item';
            chatElement.onclick = () => this.selectChat(chat);

            const lastMessageText = chat.lastMessage ?
                chat.lastMessage.body.substring(0, 50) + (chat.lastMessage.body.length > 50 ? '...' : '') :
                'No messages';

            const lastMessageTime = chat.lastMessage ?
                new Date(chat.lastMessage.timestamp).toLocaleDateString() : '';

            chatElement.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; margin-bottom: 4px;">
                            ${this.escapeHtml(chat.name || 'Unknown')}
                            ${chat.isGroup ? '<i class="fas fa-users" style="margin-left: 5px; color: #666;"></i>' : ''}
                        </div>
                        <div style="font-size: 0.9rem; color: #666;">
                            ${this.escapeHtml(lastMessageText)}
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: #999;">
                        ${lastMessageTime}
                        ${chat.unreadCount > 0 ? `<div style="background: #25d366; color: white; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; margin-top: 4px;">${chat.unreadCount}</div>` : ''}
                    </div>
                </div>
            `;

            this.chatList.appendChild(chatElement);
        });
    }

    selectChat(chat) {
        this.currentChat = chat;

        // Update UI
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });
        event.currentTarget.classList.add('active');

        // Update chat header
        this.currentChatInfo.innerHTML = `
            <h3>${this.escapeHtml(chat.name || 'Unknown')} ${chat.isGroup ? '<i class="fas fa-users"></i>' : ''}</h3>
        `;

        // Pre-fill phone number if it's not a group
        if (!chat.isGroup) {
            const phoneNumber = chat.id.replace('@c.us', '').replace('@g.us', '');
            this.phoneNumberInput.value = phoneNumber;
        }

        this.showToast(`Selected chat: ${chat.name || 'Unknown'}`, 'success');
    }

    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        this.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Logs Modal Methods
    async openLogsModal() {
        this.logsModal.classList.remove('hidden');
        this.logsStatus.classList.remove('hidden');
        this.logsContent.classList.add('hidden');

        try {
            const response = await fetch('/api/logging-status');
            const data = await response.json();

            this.displayLogsStatus(data);
        } catch (error) {
            console.error('Error loading logs status:', error);
            this.logsStatus.innerHTML = `
                <div class="error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Failed to load logs status</p>
                </div>
            `;
        }
    }

    closeLogsModalHandler() {
        this.logsModal.classList.add('hidden');
        this.showLogsList();
    }

    displayLogsStatus(data) {
        this.logsStatus.classList.add('hidden');
        this.logsContent.classList.remove('hidden');

        if (data.files.length === 0) {
            this.logsList.innerHTML = `
                <div class="no-logs">
                    <i class="fas fa-info-circle"></i>
                    <h4>No log files found</h4>
                    <p>Messages from target groups will be logged here when received.</p>
                    <p><strong>Monitoring:</strong> ${data.targetGroups ? data.targetGroups.join(', ') : 'No groups configured'}</p>
                </div>
            `;
            return;
        }

        let totalMessages = data.files.reduce((sum, file) => sum + file.messageCount, 0);

        this.logsList.innerHTML = `
            <div class="logs-summary">
                <h4>📊 Summary</h4>
                <p><strong>Target Groups:</strong> ${data.targetGroups ? data.targetGroups.join(', ') : 'Not specified'}</p>
                <p><strong>Total Files:</strong> ${data.totalLogFiles}</p>
                <p><strong>Total Messages:</strong> ${totalMessages}</p>
            </div>
            <div class="logs-files">
                <h4>📁 Log Files</h4>
                ${data.files.map(file => `
                    <div class="log-file-item" onclick="app.viewLogFile('${file.filename}')">
                        <div class="log-file-name">${file.filename}</div>
                        <div class="log-file-stats">
                            <span><i class="fas fa-comments"></i> ${file.messageCount} messages</span>
                            <span><i class="fas fa-calendar"></i> ${new Date(file.modified).toLocaleDateString()}</span>
                            <span><i class="fas fa-file"></i> ${(file.size / 1024).toFixed(1)} KB</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    async viewLogFile(filename) {
        this.showLogViewer();
        this.currentLogFile.textContent = filename;
        this.logFileContent.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Loading log file...</p>
            </div>
        `;

        try {
            const response = await fetch(`/api/logs/${filename}`);
            const data = await response.json();

            this.logFileContent.textContent = data.content || 'No content found';
        } catch (error) {
            console.error('Error loading log file:', error);
            this.logFileContent.innerHTML = `
                <div class="error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Failed to load log file</p>
                </div>
            `;
        }
    }

    showLogsList() {
        this.logsList.classList.remove('hidden');
        this.logViewer.classList.add('hidden');
    }

    showLogViewer() {
        this.logsList.classList.add('hidden');
        this.logViewer.classList.remove('hidden');
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new WhatsAppWebClone();
});
