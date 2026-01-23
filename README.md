# Water Alert Bot

A Telegram bot that monitors water supply alerts for Yerevan and sends notifications to subscribed users.

## Features

- Automatic water alert monitoring every 60 minutes
- Real-time Telegram notifications
- Multi-user subscription management
- File-based user database (temporarily)
- Configurable polling and HTTP settings

## Architecture

### Components

```
water-bot/
├── app/
│   ├── api/                    # API endpoints (if needed)
│   ├── config/                 # Configuration files
│   │   └── settings.py         # Telegram bot settings
│   ├── handlers/               # Message handlers
│   │   └── message_handlers.py # Bot command handlers
│   ├── models/                 # Data models
│   │   └── telegram_models.py  # User subscription models
│   ├── services/               # Business logic
│   │   ├── telegram_service.py # Telegram session management
│   │   └── water_scraper.py    # Water alert scraper
│   └── base_scraper.py         # Base scraper class
├── config/                     # Legacy config (for scrapers)
├── main.py                     # Main application entry point
└── requirements.txt            # Python dependencies
```

## Bot Commands

- `/start` - Start the bot and auto-subscribe
- `/subscribe` - Subscribe to water alerts
- `/unsubscribe` - Unsubscribe from alerts
- `/status` - Check your subscription status
- `/check` - Manually check for current water alerts
- `/help` - Show help message

## Configuration

### Telegram Settings (app/config/settings.py)

All settings can be configured via environment variables in `.env`:

**Required:**
- `SESSION_SECRET_KEY` - Secret key for sessions
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token

**Optional (with defaults):**
- `TELEGRAM_API_BASE_URL` - Telegram API base URL (default: https://api.telegram.org)
- `TELEGRAM_HTTP_TIMEOUT_TOTAL` - Total timeout for HTTP requests (default: 30s)
- `TELEGRAM_HTTP_TIMEOUT_CONNECT` - Connection timeout (default: 5s)
- `TELEGRAM_HTTP_TIMEOUT_SOCK_READ` - Socket read timeout (default: 10s)
- `TELEGRAM_HTTP_CONNECTION_LIMIT` - Total connection limit (default: 100)
- `TELEGRAM_HTTP_CONNECTION_LIMIT_PER_HOST` - Per-host connection limit (default: 30)
- `TELEGRAM_POLLING_INTERVAL` - Polling interval in seconds (default: 1.0)
- `TELEGRAM_POLLING_TIMEOUT` - Long polling timeout (default: 30s)
- `TELEGRAM_PARSE_MODE` - Default message parse mode (default: Markdown)

## How It Works

### Alert Monitoring Flow

1. **Scheduler**: APScheduler runs `check_and_send_alerts()` every 60 minutes
2. **Scraping**: WaterScraper fetches data from water supply organizations websites
3. **Filtering**: Temporarily only alerts matching specified location are processed
4. **Deduplication**: Alert IDs are tracked to avoid sending duplicates
5. **Notification**: Each active user receives new alerts via Telegram
6. **Error Handling**: If a user blocks the bot, their subscription is deactivated

## License

## Contributing

[Contribution guidelines]

## Support

For issues and questions, please open an issue on GitHub.
