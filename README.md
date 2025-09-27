# WhatsApp Web Clone with AI-Powered Customer Support Analysis

A complete WhatsApp Web clone built with Node.js, Express, Socket.IO, and whatsapp-web.js. Features real-time messaging, QR code authentication, automated message logging, and AI-powered customer support issue analysis with Slack integration.

## Features

- **Real-time messaging** with Socket.IO
- **QR code authentication** for WhatsApp Web
- **Responsive design** that works on desktop and mobile
- **Automated message logging** for specific WhatsApp groups
- **AI-powered issue categorization** with sample message extraction
- **Slack integration** with rich Block Kit formatting
- **Session persistence** with LocalAuth strategy
- **Auto-discovery** of most recent log files for batch processing

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd whatsappweb
   ```

2. **Install dependencies**
   ```bash
   npm install
   pip install openai requests  # For AI summarization
   ```

3. **Set environment variables**
   ```bash
   export OPENAI_API_KEY="sk-your-openai-api-key"
   export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
   export SLACK_CHANNEL="C09BK6AGAF7"  # Optional: default channel
   ```

4. **Start the server**
   ```bash
   npm start
   ```

5. **Open your browser**
   Navigate to `http://localhost:3000`

6. **Scan QR code**
   Use your phone's WhatsApp to scan the QR code and connect

## Message Logging & AI Analysis System

### Monitored Groups
The system automatically logs messages from these WhatsApp groups:
- **retail all-stars**
- **Seeds+Customer Support**
- **Winwise Agent Support**
- **Merchant Acquisition_Paybox**

### Log Files Structure
```
message-logs/
├── retail-allstars-messages-2025-09-27.txt
├── seedscustomer-support-messages-2025-09-27.txt
├── winwise-agent-support-messages-2025-09-26.txt
└── merchant-acquisitionpaybox-messages-2025-09-27.txt

summaries/
├── retail-allstars-summary.txt
├── seedscustomer-support-summary.txt
└── winwise-agent-support-summary.txt
```

## AI Summarization Commands

### Auto-Discovery Mode (Recommended)
Process the most recent log file for each target group automatically:

```bash
# Generate summaries and post to Slack
python scripts/summarize_logs.py --slack --slack-channel C09BK6AGAF7

# Generate summaries only (no Slack posting)
python scripts/summarize_logs.py

# Use different model
python scripts/summarize_logs.py --model gpt-4 --slack

# Custom log directory
python scripts/summarize_logs.py --log-dir /path/to/logs --slack
```

### Explicit File Mode
Process specific files:

```bash
# Process specific log file
python scripts/summarize_logs.py --slack message-logs/retail-allstars-messages-2025-09-27.txt

# Process multiple files
python scripts/summarize_logs.py --slack message-logs/*.txt

# Post existing summary to Slack (no API key needed)
python scripts/summarize_logs.py --slack summaries/retail-allstars-summary.txt
```

### Command Options
- `--slack` - Post summaries to Slack
- `--slack-channel CHANNEL_ID` - Specify Slack channel
- `--model MODEL_NAME` - OpenAI model (default: gpt-4o-mini)
- `--log-dir DIRECTORY` - Log files directory (default: message-logs)
- `--insecure` - Skip SSL verification (not recommended)
- `--ca-bundle PATH` - Custom CA bundle for SSL

## Ubuntu Server Deployment with Nginx & Cron

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js (using NodeSource repository)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python and pip
sudo apt install python3 python3-pip -y

# Install PM2 for process management
sudo npm install -g pm2

# Install Nginx
sudo apt install nginx -y
```

### 2. Application Deployment

```bash
# Clone your repository
cd /var/www
sudo git clone <your-repository-url> whatsappweb
cd whatsappweb

# Install dependencies
sudo npm install
sudo pip3 install openai requests

# Set up environment variables
sudo nano /var/www/whatsappweb/.env
```

Add to `.env` file:
```env
PORT=3001
OPENAI_API_KEY=sk-your-openai-api-key
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL=C09BK6AGAF7
NODE_ENV=production
```

```bash
# Set proper permissions
sudo chown -R www-data:www-data /var/www/whatsappweb
sudo chmod -R 755 /var/www/whatsappweb

# Start application with PM2
cd /var/www/whatsappweb
sudo -u www-data pm2 start server.js --name "whatsappweb"
sudo pm2 startup
sudo pm2 save
```

### 3. Nginx Configuration

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/whatsappweb
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    location / {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }
}
```

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/whatsappweb /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4. SSL Certificate (Optional but Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 5. Automated AI Summarization with Cron

```bash
# Create summarization script
sudo nano /var/www/whatsappweb/scripts/daily_summary.sh
```

Add this content:
```bash
#!/bin/bash
cd /var/www/whatsappweb

# Set environment variables
export OPENAI_API_KEY="sk-your-openai-api-key"
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
export SLACK_CHANNEL="C09BK6AGAF7"

# Run summarization
/usr/bin/python3 scripts/summarize_logs.py --slack --slack-channel $SLACK_CHANNEL

# Log the execution
echo "$(date): Daily summary completed" >> /var/log/whatsapp-summary.log
```

```bash
# Make script executable
sudo chmod +x /var/www/whatsappweb/scripts/daily_summary.sh

# Set up cron job for daily execution at 9 AM
sudo crontab -e
```

Add this line to run daily at 9:00 AM:
```cron
0 9 * * * /var/www/whatsappweb/scripts/daily_summary.sh
```

### 6. Monitoring & Logs

```bash
# View application logs
sudo -u www-data pm2 logs whatsappweb

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# View summary execution logs
sudo tail -f /var/log/whatsapp-summary.log

# Check cron job status
sudo grep CRON /var/log/syslog
```

### 7. Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## Cron Schedule Examples

```bash
# Daily at 9 AM
0 9 * * * /var/www/whatsappweb/scripts/daily_summary.sh

# Every 6 hours
0 */6 * * * /var/www/whatsappweb/scripts/daily_summary.sh

# Monday to Friday at 9 AM
0 9 * * 1-5 /var/www/whatsappweb/scripts/daily_summary.sh

# Multiple times per day (9 AM, 1 PM, 5 PM)
0 9,13,17 * * * /var/www/whatsappweb/scripts/daily_summary.sh
```

## Project Structure

```
whatsappweb/
├── server.js                    # Main server file
├── public/
│   ├── index.html              # Frontend HTML
│   ├── styles.css              # Styling
│   └── script.js               # Frontend JavaScript
├── scripts/
│   ├── summarize_logs.py       # AI summarization script
│   └── daily_summary.sh        # Cron automation script
├── message-logs/               # WhatsApp message logs
├── summaries/                  # Generated AI summaries
├── .wwebjs_auth/              # WhatsApp session data
├── .env                       # Environment variables
└── README.md                  # This file
```

## API Endpoints

- `GET /` - Main application interface
- `GET /api/logs/status` - Logging system status and target groups
- `GET /api/logs/files` - List available log files
- `GET /api/logs/content/:filename` - View log file content

## Configuration

### Target Groups
Edit `TARGET_GROUP_NAMES` in both `server.js` and `scripts/summarize_logs.py`:

```javascript
const TARGET_GROUP_NAMES = [
    'retail all-stars',
    'Seeds+Customer Support',
    'Winwise Agent Support',
    'Merchant Acquisition_Paybox'
];
```

### Environment Variables
- `PORT` - Server port (default: 3000)
- `OPENAI_API_KEY` - Required for AI summarization
- `SLACK_BOT_TOKEN` - Required for Slack integration
- `SLACK_CHANNEL` - Default Slack channel ID
- `NODE_ENV` - Environment (development/production)

## Troubleshooting

### Common Issues

1. **WhatsApp session expired**
   ```bash
   # Clear session and restart
   sudo rm -rf /var/www/whatsappweb/.wwebjs_auth
   sudo -u www-data pm2 restart whatsappweb
   ```

2. **OpenAI API errors**
   ```bash
   # Check API key and quota
   curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
   ```

3. **Slack posting fails**
   ```bash
   # Test Slack token
   curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" https://slack.com/api/auth.test
   ```

4. **Cron job not running**
   ```bash
   # Check cron service
   sudo systemctl status cron
   # Check logs
   sudo grep CRON /var/log/syslog | tail -10
   ```

## Technologies Used

- **Backend**: Node.js, Express.js
- **Real-time**: Socket.IO
- **WhatsApp**: whatsapp-web.js
- **Frontend**: Vanilla JavaScript, CSS3
- **AI**: OpenAI GPT-4o-mini
- **Integration**: Slack API with Block Kit
- **Deployment**: PM2, Nginx, Ubuntu
- **Automation**: Cron

## License

MIT License