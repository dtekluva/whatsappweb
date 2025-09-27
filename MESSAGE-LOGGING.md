# WhatsApp Message Logging System

## Overview

The WhatsApp Web Clone now includes an automated message logging system that monitors and saves messages from specific WhatsApp groups. This feature is designed for record-keeping and compliance purposes.

## Features

### 🎯 **Targeted Group Monitoring**
- Monitors messages from multiple WhatsApp groups simultaneously
- Currently configured groups: "retail all-stars" and "Seeds+Customer Support"
- Case-insensitive group name matching
- Automatic detection of group messages vs individual chats

### 📁 **Automated File Management**
- Creates daily log files with timestamp-based naming
- File format: `[group-name]-messages-YYYY-MM-DD.txt`
- Examples: `retail-all-stars-messages-2025-09-26.txt`, `seedscustomer-support-messages-2025-09-26.txt`
- Automatic directory creation (`./message-logs/`)
- Organized by date and group for easy management

### 💬 **Message Format**
Each logged message includes:
- **Timestamp**: ISO 8601 format for precise timing
- **Sender Name**: Contact name, push name, or phone number
- **Message Content**: Full message text

Example log entry:
```
[2025-09-26T08:20:15.123Z] John Doe: Good morning team! Ready for today's sales targets?
```

### 🔍 **Web Interface**
- **Logs Viewer**: Built-in web interface to view logged messages
- **File Browser**: List all log files with statistics
- **Content Viewer**: Read log file contents directly in the browser
- **Statistics**: Message counts, file sizes, and dates

## Configuration

### Target Groups
The system is currently configured to monitor:
- **Group Names**: "retail all-stars" and "Seeds+Customer Support" (case-insensitive)
- **Location**: Configurable in `server.js` via `TARGET_GROUP_NAMES` array

### File Storage
- **Directory**: `./message-logs/` (relative to project root)
- **Naming**: `[group-name]-messages-YYYY-MM-DD.txt` (special characters removed, spaces become hyphens)
- **Format**: Plain text with UTF-8 encoding

## Usage

### Automatic Logging
1. **Start the application**: `npm start`
2. **Connect WhatsApp**: Scan QR code or use existing session
3. **Messages are logged automatically** when received from the target group

### Viewing Logs via Web Interface
1. **Open the application**: `http://localhost:3000`
2. **Click the logs button**: File icon in the chat sidebar
3. **Browse log files**: View statistics and select files to read
4. **Read content**: View full message history in chronological order

### Console Output
When a message from the target group is received, you'll see:
```
🎯 Message detected from target group: "retail all-stars"
✅ LOGGED MESSAGE from "retail all-stars" group:
   📁 File: retail-all-stars-messages-2025-09-26.txt
   👤 Sender: John Doe
   💬 Message: Good morning team! Ready for today's...
📝 Message successfully logged to file
```

## API Endpoints

### Get Logging Status
```http
GET /api/logging-status
```

**Response:**
```json
{
  "targetGroup": "retail all-stars",
  "logDirectory": "/path/to/message-logs",
  "totalLogFiles": 3,
  "files": [
    {
      "filename": "retail-all-stars-messages-2025-09-26.txt",
      "size": 1024,
      "created": "2025-09-26T08:00:00.000Z",
      "modified": "2025-09-26T18:30:00.000Z",
      "messageCount": 25
    }
  ]
}
```

### Get Log File Content
```http
GET /api/logs/{filename}
```

**Response:**
```json
{
  "filename": "retail-all-stars-messages-2025-09-26.txt",
  "content": "[2025-09-26T08:20:15.123Z] John Doe: Good morning...",
  "lines": 25
}
```

## Error Handling

### File System Errors
- **Directory Creation**: Automatically creates log directory if missing
- **Write Failures**: Logs errors to console, continues operation
- **Permission Issues**: Graceful error handling with console warnings

### Network Errors
- **API Failures**: Returns appropriate HTTP status codes
- **File Not Found**: 404 response for missing log files
- **Invalid Requests**: 400 response for malformed requests

### Application Resilience
- **Logging failures don't affect chat functionality**
- **Continues monitoring even after file errors**
- **Automatic retry on next message**

## Security Considerations

### File Access
- **Restricted file access**: Only allows reading retail all-stars log files
- **Path validation**: Prevents directory traversal attacks
- **Filename validation**: Only allows expected filename patterns

### Data Privacy
- **Local storage only**: Messages are stored locally on your server
- **No external transmission**: Logs are not sent to external services
- **Access control**: Only accessible via your local application

## Customization

### Change Target Group
Edit `server.js`:
```javascript
const TARGET_GROUP_NAME = 'your-group-name-here';
```

### Change Log Directory
Edit `server.js`:
```javascript
const LOG_DIRECTORY = path.join(__dirname, 'your-custom-directory');
```

### Modify Log Format
Edit the `logGroupMessage` function in `server.js` to customize the log entry format.

## File Structure

```
whatsappweb/
├── message-logs/                    # Log files directory
│   ├── retail-all-stars-messages-2025-09-26.txt
│   ├── retail-all-stars-messages-2025-09-27.txt
│   └── ...
├── server.js                       # Main server with logging logic
├── public/
│   ├── index.html                  # UI with logs viewer
│   ├── script.js                   # Frontend logging interface
│   └── styles.css                  # Logs modal styling
└── MESSAGE-LOGGING.md              # This documentation
```

## Troubleshooting

### No Messages Being Logged
1. **Check group name**: Ensure the group name matches exactly (case-insensitive)
2. **Verify connection**: Make sure WhatsApp client is connected and ready
3. **Check console**: Look for error messages in the server console
4. **File permissions**: Ensure the application can write to the message-logs directory

### Web Interface Issues
1. **Refresh the page**: Try refreshing the browser
2. **Check console**: Look for JavaScript errors in browser console
3. **API connectivity**: Test API endpoints directly with curl

### File Access Problems
1. **Directory permissions**: Ensure the message-logs directory is writable
2. **Disk space**: Check available disk space
3. **File locks**: Ensure no other processes are accessing the log files

## Compliance and Legal

- **Data Retention**: Configure appropriate data retention policies
- **Privacy Laws**: Ensure compliance with local privacy regulations
- **Consent**: Obtain necessary consent from group members
- **Access Control**: Implement appropriate access controls for log files

This logging system provides a robust foundation for message archival and compliance requirements while maintaining the full functionality of your WhatsApp Web clone.
