# Enhanced Telegram Integration

This document describes the enhanced Telegram integration features implemented for the Unified GUI Platform.

## Overview

The enhanced Telegram integration provides bidirectional communication between the web interface and Telegram, enabling:

- **Bidirectional messaging** - Messages sent through web interface appear in Telegram and vice versa
- **Webhook handling** - Real-time processing of incoming Telegram messages
- **Message queue system** - Reliable message delivery with retry logic and persistence
- **Multiple chat support** - Manage multiple Telegram chats from a single interface
- **QnA integration** - Ask questions via Telegram and get responses mirrored to web interface

## Architecture

### Core Components

1. **EnhancedTelegramService** - Main service handling Telegram communication
2. **MessageQueueManager** - Persistent message queue with SQLite storage
3. **TelegramQnAHandler** - Processes questions and integrates with QnA system
4. **MessageMirrorService** - Synchronizes messages between Telegram and web interface
5. **Webhook Router** - FastAPI endpoints for Telegram webhook handling

### Message Flow

```
Web Interface → EnhancedTelegramService → MessageQueue → Telegram API
                                      ↓
                              MessageMirrorService → Database → WebSocket → Web Interface

Telegram → Webhook → EnhancedTelegramService → MessageMirrorService → Database → WebSocket → Web Interface
```

## Configuration

### Environment Variables

```bash
# Primary bot configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Additional bots (optional)
TELEGRAM_BOT_TOKEN_2=second_bot_token
TELEGRAM_CHAT_ID_2=second_chat_id
TELEGRAM_CHAT_NAME_2=Second Chat

# Webhook configuration
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook/telegram

# Message queue settings
MESSAGE_QUEUE_DB_PATH=gui/data/message_queue.db
MESSAGE_QUEUE_MAX_RETRIES=3
```

### Webhook Setup

1. Configure your webhook URL in environment variables
2. The service automatically sets up webhooks on startup
3. Webhook endpoints are available at `/webhook/telegram/{chat_id}`

## API Endpoints

### Webhook Endpoints

- `POST /webhook/telegram/{chat_id}` - Receive Telegram updates
- `GET /webhook/telegram/{chat_id}/status` - Get chat status
- `POST /webhook/telegram/{chat_id}/send` - Send message to specific chat

### Management Endpoints

- `GET /webhook/telegram/chats` - List active chats
- `GET /webhook/telegram/queue/status` - Get message queue status
- `POST /webhook/telegram/queue/clear` - Clear message queue (admin)

## Features

### Bidirectional Communication

Messages sent through the web interface are automatically delivered to configured Telegram chats. Incoming Telegram messages are processed and displayed in the web interface in real-time.

### Message Queue System

- **Persistent storage** - Messages survive service restarts
- **Retry logic** - Failed messages are retried with exponential backoff
- **Status tracking** - Track message delivery status (pending, processing, delivered, failed)
- **Cleanup** - Automatic cleanup of old delivered/failed messages

### Multiple Chat Support

Configure multiple Telegram bots and chats:

```python
# Add new chat programmatically
telegram_service.add_chat(
    chat_id="new_chat_123",
    chat_name="New Chat",
    bot_token="bot_token_here"
)

# Remove/deactivate chat
telegram_service.remove_chat("chat_id")
```

### QnA Integration

The TelegramQnAHandler automatically detects questions in Telegram messages and processes them through the QnA system:

- **Question detection** - Uses pattern matching to identify questions
- **Context preservation** - Maintains conversation context
- **Response formatting** - Formats responses appropriately for Telegram
- **Bidirectional sync** - QnA conversations are mirrored to web interface

## Usage Examples

### Sending Messages from Web Interface

```python
# Send to specific chat
await telegram_service.send_message_to_chat(
    chat_id="chat_123",
    message="Hello from web interface!",
    message_type=MessageType.OUTBOUND,
    channel_id="channel_456"
)

# Broadcast to all chats
results = await telegram_service.send_message_to_all_chats(
    message="System notification",
    message_type=MessageType.SYSTEM_NOTIFICATION
)
```

### Handling Incoming Messages

```python
# Register custom webhook handler
async def custom_handler(chat_id: str, message_text: str, message_data: dict):
    if message_text.startswith("/custom"):
        # Handle custom command
        await telegram_service.send_message_to_chat(
            chat_id=chat_id,
            message="Custom command processed!",
            message_type=MessageType.SYSTEM_NOTIFICATION
        )

telegram_service.register_webhook_handler("custom", custom_handler)
```

### QnA Integration

```python
# Questions are automatically detected and processed
# Example Telegram message: "What is the latest video about?"
# → Processed by QnA system
# → Response sent back to Telegram
# → Conversation mirrored to web interface
```

## Monitoring and Troubleshooting

### Queue Status

```python
status = telegram_service.get_queue_status()
print(f"Pending messages: {status['persistent_queue_stats']['statistics']['pending']}")
print(f"Active chats: {status['active_chats']}")
```

### Health Checks

The service provides health check endpoints and logging for monitoring:

- Message delivery success/failure rates
- Queue processing performance
- Webhook reception status
- Database connectivity

### Common Issues

1. **Webhook not receiving messages**
   - Verify webhook URL is accessible from internet
   - Check Telegram bot token and permissions
   - Ensure webhook is properly registered

2. **Messages not being delivered**
   - Check message queue status
   - Verify chat IDs and bot tokens
   - Review error logs for API failures

3. **QnA not responding**
   - Ensure QnA service is properly initialized
   - Check question detection patterns
   - Verify QnA system integration

## Security Considerations

- **Token protection** - Bot tokens are loaded from environment variables only
- **Input validation** - All incoming webhook data is validated
- **Rate limiting** - Built-in rate limiting for API calls
- **Chat validation** - Only configured chats can send/receive messages
- **Message sanitization** - Content is sanitized before storage/display

## Performance

- **Asynchronous processing** - Non-blocking message handling
- **Persistent queue** - Survives service restarts
- **Connection pooling** - Efficient HTTP client usage
- **Batch processing** - Multiple messages processed efficiently
- **Memory management** - Automatic cleanup of old data

## Development

### Testing

```bash
# Run integration tests
python -m pytest gui/tests/test_enhanced_telegram_integration.py -v

# Test specific functionality
python -m pytest gui/tests/test_enhanced_telegram_integration.py::TestEnhancedTelegramIntegration::test_send_message_to_chat -v
```

### Adding New Features

1. Extend `EnhancedTelegramService` for new functionality
2. Add webhook handlers for custom message processing
3. Update message types in `MessageType` enum
4. Add corresponding API endpoints in `telegram_webhook.py`

## Migration from Basic Telegram Service

The enhanced service is backward compatible with the existing `TelegramService`. To migrate:

1. Update imports to use `EnhancedTelegramService`
2. Initialize with required dependencies (WebSocketManager, MessageMirrorService)
3. Configure environment variables for multiple chats if needed
4. Set up webhooks for bidirectional communication

## Future Enhancements

- **Message templates** - Predefined message formats
- **Scheduled messages** - Time-based message delivery
- **Message threading** - Group related messages
- **Rich media support** - Images, documents, voice messages
- **Bot commands** - Advanced command processing
- **Analytics integration** - Message delivery analytics