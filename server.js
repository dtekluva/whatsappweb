const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const path = require('path');
const cors = require('cors');
const fs = require('fs').promises;
const fsSync = require('fs');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

const PORT = process.env.PORT || 3000;

// Message logging configuration
const TARGET_GROUP_NAMES = ['retail all-stars', 'Seeds+Customer Support', 'Winwise Agent Support', 'Merchant Acquisition_Paybox']; // Group names to monitor (case-insensitive)
const LOG_DIRECTORY = path.join(__dirname, 'message-logs');

// Ensure log directory exists
if (!fsSync.existsSync(LOG_DIRECTORY)) {
    fsSync.mkdirSync(LOG_DIRECTORY, { recursive: true });
    console.log(`Created message logs directory: ${LOG_DIRECTORY}`);
}

// Utility function to format date for filename
function getDateString() {
    const now = new Date();
    return now.toISOString().split('T')[0]; // YYYY-MM-DD format
}

// Utility function to format timestamp for log entries
function getTimestamp() {
    return new Date().toISOString();
}

// Function to log messages from target group
async function logGroupMessage(messageData, contact, chat) {
    try {
        const dateString = getDateString();

        // Create filename based on group name and current date
        const groupNameForFile = chat.name.toLowerCase()
            .replace(/[^a-z0-9\s]/g, '') // Remove special characters except spaces
            .replace(/\s+/g, '-') // Replace spaces with hyphens
            .trim();
        const filename = `${groupNameForFile}-messages-${dateString}.txt`;
        const filepath = path.join(LOG_DIRECTORY, filename);

        const timestamp = getTimestamp();
        const senderName = contact.name || contact.pushname || contact.number || 'Unknown';
        const messageContent = messageData.body || '[No text content]';

        // Format the log entry
        const logEntry = `[${timestamp}] ${senderName}: ${messageContent}\n`;

        // Append to file (create if doesn't exist)
        await fs.appendFile(filepath, logEntry, 'utf8');

        console.log(`✅ LOGGED MESSAGE from "${chat.name}" group:`);
        console.log(`   📁 File: ${filename}`);
        console.log(`   👤 Sender: ${senderName}`);
        console.log(`   💬 Message: ${messageContent.substring(0, 100)}${messageContent.length > 100 ? '...' : ''}`);

        return true;
    } catch (error) {
        console.error(`❌ ERROR logging message from "${chat.name}" group:`, error.message);
        return false;
    }
}

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// WhatsApp client setup
const client = new Client({
    authStrategy: new LocalAuth({
        clientId: "whatsapp-web-clone"
    }),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-gpu'
        ]
    }
});

let qrCodeData = null;
let isClientReady = false;
let clientInfo = null;

// WhatsApp client event handlers
client.on('qr', async (qr) => {
    console.log('QR Code received');
    try {
        qrCodeData = await qrcode.toDataURL(qr);
        io.emit('qr', qrCodeData);
        console.log('QR Code sent to frontend');
    } catch (err) {
        console.error('Error generating QR code:', err);
    }
});

client.on('ready', () => {
    console.log('WhatsApp client is ready!');
    isClientReady = true;
    qrCodeData = null;

    // Get client info
    client.info.then(info => {
        clientInfo = info;
        io.emit('ready', {
            message: 'WhatsApp client is ready!',
            clientInfo: info
        });
    });
});

client.on('authenticated', () => {
    console.log('WhatsApp client authenticated');
    io.emit('authenticated', 'WhatsApp client authenticated');
});

client.on('auth_failure', (msg) => {
    console.error('Authentication failed:', msg);
    io.emit('auth_failure', msg);
});

client.on('disconnected', (reason) => {
    console.log('WhatsApp client disconnected:', reason);
    isClientReady = false;
    clientInfo = null;
    io.emit('disconnected', reason);
});

client.on('message', async (message) => {
    console.log('New message received:', message.body);

    // Get contact info
    const contact = await message.getContact();
    const chat = await message.getChat();

    // Check if this message is from any of the target groups and log it
    if (chat.isGroup && chat.name) {
        const groupName = chat.name.toLowerCase().trim();
        const targetGroupNames = TARGET_GROUP_NAMES.map(name => name.toLowerCase().trim());

        if (targetGroupNames.includes(groupName)) {
            console.log(`🎯 Message detected from target group: "${chat.name}"`);

            // Log the message to file
            const logSuccess = await logGroupMessage(message, contact, chat);

            if (logSuccess) {
                console.log(`📝 Message successfully logged to file`);
            } else {
                console.log(`⚠️  Failed to log message to file`);
            }
        }
    }

    // Determine the source name for display
    let sourceName = '';
    if (chat.isGroup) {
        // For group messages, show "Contact Name in Group Name"
        const contactName = contact.name || contact.pushname || contact.number;
        sourceName = `${contactName} in ${chat.name}`;
    } else {
        // For individual chats, just show the contact name
        sourceName = contact.name || contact.pushname || contact.number;
    }

    const messageData = {
        id: message.id._serialized,
        body: message.body,
        from: message.from,
        to: message.to,
        timestamp: message.timestamp,
        type: message.type,
        isGroupMsg: message.isGroupMsg,
        sourceName: sourceName, // Add the formatted source name
        contact: {
            id: contact.id._serialized,
            name: contact.name || contact.pushname || contact.number,
            pushname: contact.pushname,
            number: contact.number
        },
        chat: {
            id: chat.id._serialized,
            name: chat.name,
            isGroup: chat.isGroup
        }
    };

    io.emit('message', messageData);
});

// Socket.IO connection handling
io.on('connection', (socket) => {
    console.log('Client connected:', socket.id);

    // Send current status to newly connected client
    if (qrCodeData) {
        socket.emit('qr', qrCodeData);
    } else if (isClientReady) {
        socket.emit('ready', {
            message: 'WhatsApp client is ready!',
            clientInfo: clientInfo
        });
    }

    // Handle send message request
    socket.on('sendMessage', async (data) => {
        try {
            if (!isClientReady) {
                socket.emit('error', 'WhatsApp client is not ready');
                return;
            }

            const { number, message } = data;
            const chatId = number.includes('@c.us') ? number : `${number}@c.us`;

            const sentMessage = await client.sendMessage(chatId, message);

            // Get chat info for the sent message
            const chat = await client.getChatById(chatId);
            let targetName = '';
            if (chat.isGroup) {
                targetName = `to ${chat.name}`;
            } else {
                targetName = `to ${chat.name || chatId.replace('@c.us', '')}`;
            }

            socket.emit('messageSent', {
                success: true,
                messageId: sentMessage.id._serialized,
                to: chatId,
                body: message,
                targetName: targetName,
                isGroup: chat.isGroup
            });

            console.log('Message sent successfully to:', chatId);
        } catch (error) {
            console.error('Error sending message:', error);
            socket.emit('error', `Failed to send message: ${error.message}`);
        }
    });

    // Handle get chats request
    socket.on('getChats', async () => {
        try {
            if (!isClientReady) {
                socket.emit('error', 'WhatsApp client is not ready');
                return;
            }

            const chats = await client.getChats();
            const chatList = chats.slice(0, 20).map(chat => ({
                id: chat.id._serialized,
                name: chat.name,
                isGroup: chat.isGroup,
                lastMessage: chat.lastMessage ? {
                    body: chat.lastMessage.body,
                    timestamp: chat.lastMessage.timestamp
                } : null,
                unreadCount: chat.unreadCount
            }));

            socket.emit('chats', chatList);
        } catch (error) {
            console.error('Error getting chats:', error);
            socket.emit('error', `Failed to get chats: ${error.message}`);
        }
    });

    socket.on('disconnect', () => {
        console.log('Client disconnected:', socket.id);
    });
});

// API Routes
app.get('/api/status', (req, res) => {
    res.json({
        isReady: isClientReady,
        hasQR: !!qrCodeData,
        clientInfo: clientInfo
    });
});

app.get('/api/qr', (req, res) => {
    if (qrCodeData) {
        res.json({ qr: qrCodeData });
    } else {
        res.status(404).json({ error: 'No QR code available' });
    }
});

// API endpoint to get logging status and information
app.get('/api/logging-status', async (req, res) => {
    try {
        const logFiles = await fs.readdir(LOG_DIRECTORY);

        // Filter log files for all target groups
        const targetLogFiles = logFiles.filter(file => {
            return TARGET_GROUP_NAMES.some(groupName => {
                const groupNameForFile = groupName.toLowerCase()
                    .replace(/[^a-z0-9\s]/g, '') // Remove special characters except spaces
                    .replace(/\s+/g, '-') // Replace spaces with hyphens
                    .trim();
                return file.startsWith(`${groupNameForFile}-messages-`);
            });
        });

        const fileStats = await Promise.all(
            targetLogFiles.map(async (filename) => {
                const filepath = path.join(LOG_DIRECTORY, filename);
                const stats = await fs.stat(filepath);
                const content = await fs.readFile(filepath, 'utf8');
                const messageCount = content.split('\n').filter(line => line.trim()).length;

                return {
                    filename,
                    size: stats.size,
                    created: stats.birthtime,
                    modified: stats.mtime,
                    messageCount
                };
            })
        );

        res.json({
            targetGroups: TARGET_GROUP_NAMES,
            logDirectory: LOG_DIRECTORY,
            totalLogFiles: targetLogFiles.length,
            files: fileStats.sort((a, b) => b.modified - a.modified) // Sort by most recent first
        });
    } catch (error) {
        console.error('Error getting logging status:', error);
        res.status(500).json({ error: 'Failed to get logging status' });
    }
});

// API endpoint to get log file content
app.get('/api/logs/:filename', async (req, res) => {
    try {
        const filename = req.params.filename;

        // Security check - only allow log files from target groups
        const isValidLogFile = TARGET_GROUP_NAMES.some(groupName => {
            const groupNameForFile = groupName.toLowerCase()
                .replace(/[^a-z0-9\s]/g, '') // Remove special characters except spaces
                .replace(/\s+/g, '-') // Replace spaces with hyphens
                .trim();
            return filename.startsWith(`${groupNameForFile}-messages-`) && filename.endsWith('.txt');
        });

        if (!isValidLogFile) {
            return res.status(400).json({ error: 'Invalid log file name' });
        }

        const filepath = path.join(LOG_DIRECTORY, filename);
        const content = await fs.readFile(filepath, 'utf8');

        res.json({
            filename,
            content,
            lines: content.split('\n').filter(line => line.trim()).length
        });
    } catch (error) {
        if (error.code === 'ENOENT') {
            res.status(404).json({ error: 'Log file not found' });
        } else {
            console.error('Error reading log file:', error);
            res.status(500).json({ error: 'Failed to read log file' });
        }
    }
});

// Serve the main page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start server
server.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
    console.log('Initializing WhatsApp client...');
    console.log('');
    console.log('📋 MESSAGE LOGGING CONFIGURATION:');
    console.log(`   🎯 Target Groups: ${TARGET_GROUP_NAMES.map(name => `"${name}"`).join(', ')}`);
    console.log(`   📁 Log Directory: ${LOG_DIRECTORY}`);
    console.log(`   📝 Log Format: [group-name]-messages-YYYY-MM-DD.txt`);
    console.log('');
    client.initialize();
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('Shutting down gracefully...');
    await client.destroy();
    server.close(() => {
        console.log('Server closed');
        process.exit(0);
    });
});
