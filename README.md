# WhatsApp Web Clone

A fully functional WhatsApp Web clone built with Node.js, Express, Socket.IO, and the whatsapp-web.js library. This application allows you to interact with WhatsApp through a web browser interface running on your local machine.

## Features

- 🔐 **QR Code Authentication** - Scan QR code with your phone to connect
- 💬 **Real-time Messaging** - Send and receive messages in real-time
- 📱 **Chat Interface** - View your existing chats and conversations
- 🌐 **Web-based** - Access through any modern web browser
- 🔄 **Live Updates** - Messages appear instantly without page refresh
- 📋 **Chat List** - Browse through your recent conversations

## Prerequisites

- Node.js (v14 or higher)
- npm (Node Package Manager)
- A smartphone with WhatsApp installed
- Modern web browser (Chrome, Firefox, Safari, Edge)

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd whatsappweb
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

## Usage

1. **Start the application:**
   ```bash
   npm start
   ```

2. **Open your web browser and navigate to:**
   ```
   http://localhost:3000
   ```

3. **Scan the QR Code:**
   - Open WhatsApp on your phone
   - Go to Settings > WhatsApp Web/Desktop
   - Tap "Link a Device"
   - Scan the QR code displayed on your browser

4. **Start messaging:**
   - Once connected, you'll see your chat interface
   - Browse existing chats in the sidebar
   - Send new messages using the input form at the bottom
   - Enter a phone number (with country code) and your message

## How It Works

### Backend (server.js)
- **Express Server**: Serves the web interface and handles API requests
- **WhatsApp Client**: Uses whatsapp-web.js to connect to WhatsApp Web
- **Socket.IO**: Provides real-time communication between server and browser
- **QR Code Generation**: Creates QR codes for WhatsApp authentication

### Frontend (public/)
- **HTML Interface**: Clean, responsive design similar to WhatsApp Web
- **Real-time Updates**: Socket.IO client for live message updates
- **Chat Management**: Display chats, messages, and handle user interactions

## API Endpoints

- `GET /` - Main application interface
- `GET /api/status` - Check connection status
- `GET /api/qr` - Get current QR code (if available)

## Socket.IO Events

### Client to Server:
- `sendMessage` - Send a message to a contact
- `getChats` - Retrieve chat list

### Server to Client:
- `qr` - QR code data for authentication
- `ready` - WhatsApp client is connected and ready
- `message` - New incoming message
- `messageSent` - Confirmation of sent message
- `chats` - List of available chats
- `error` - Error messages

## File Structure

```
whatsappweb/
├── server.js              # Main server file
├── package.json           # Project dependencies
├── README.md             # This file
└── public/               # Frontend files
    ├── index.html        # Main HTML interface
    ├── styles.css        # CSS styling
    └── script.js         # Frontend JavaScript
```

## Security Notes

- This application runs locally on your machine
- Your WhatsApp session data is stored locally using LocalAuth
- No messages or data are sent to external servers
- The QR code is only valid for linking your device

## Troubleshooting

### QR Code Not Appearing
- Wait a few seconds for the WhatsApp client to initialize
- Refresh the browser page
- Check the server console for error messages

### Connection Issues
- Ensure your phone has internet connection
- Make sure WhatsApp is updated to the latest version
- Try restarting the server with `npm start`

### Messages Not Sending
- Verify the phone number format (include country code)
- Check that WhatsApp client shows as "ready" in the interface
- Ensure the recipient's number is valid

## Development

To run in development mode:
```bash
npm run dev
```

## Dependencies

- **whatsapp-web.js**: WhatsApp Web API client
- **express**: Web server framework
- **socket.io**: Real-time communication
- **qrcode**: QR code generation
- **cors**: Cross-origin resource sharing

## License

ISC License - Feel free to use and modify as needed.

## Disclaimer

This project is for educational purposes. Make sure to comply with WhatsApp's Terms of Service when using this application.
