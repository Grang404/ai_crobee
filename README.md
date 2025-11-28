# Discord TTS Bot

A personal Discord bot that automatically reads messages aloud in voice channels using ElevenLabs text-to-speech.

## Features

- **Automatic TTS**: Reads messages from a specific user when they're in a voice channel
- **Smart Voice Management**: Automatically joins and leaves voice channels based on user activity
- **Message Cleaning**: Converts Discord mentions, emojis, and markdown to readable text for clean voice output
- **Slash Commands**: Easy-to-use commands for manual control
- **Status Monitoring**: Check bot uptime, latency, and memory usage

## Commands

- `/tts_join` - Manually join your current voice channel
- `/tts_leave` - Leave the voice channel
- `/tts_test <text>` - Test TTS with a custom message
- `/tts_status` - Display bot statistics and health
- `/tts_restart` - Restart the bot (requires Administrator or "Bot Admin" role)

NOTE: `/tts_restart` only restarts a systemd service

## Setup

### Prerequisites

- Python 3.8+
- FFmpeg installed on your system
- Discord Bot Token
- ElevenLabs API Key

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd <repo-name>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory:
```env
BOT_KEY=your_discord_bot_token
API_KEY=your_elevenlabs_api_key
VOICE_ID=your_elevenlabs_voice_id
TARGET_USER=discord_user_id_to_read
TARGET_SERVER=discord_server_id
```

4. Run bot

```bash
python main.py
```

## Configuration

### Environment Variables

- `BOT_KEY` - Discord bot token from the [Discord Developer Portal](https://discord.com/developers/applications)
- `API_KEY` - ElevenLabs API key
- `VOICE_ID` - ElevenLabs voice ID you want to use
- `TARGET_USER` - Discord user ID whose messages will be read aloud
- `TARGET_SERVER` - Discord server ID where commands will be synced

### Getting Your Voice ID

1. Go to [ElevenLabs Voice Lab](https://elevenlabs.io/voice-lab)
2. Select or create a voice
3. Copy the Voice ID from the voice settings

## How It Works

1. The bot monitors messages from the configured target user
2. When the target user sends a message (that doesn't start with `!`), the bot:
   - Joins their voice channel if not already connected
   - Cleans the message text (removes URLs, converts mentions, etc.)
   - Generates TTS audio using ElevenLabs
   - Plays the audio in the voice channel
3. The bot automatically disconnects when the target user leaves voice

## Project Structure

```
.
├── main.py           # Bot initialization and startup
├── cogs/
│   ├── tts.py        # TTS listener and audio playback
│   └── commands.py   # Slash commands
└── .env              # Environment variables (not tracked)
```

## License

This is a personal project. Feel free to fork and modify for your own use.

## Notes

- The bot uses ElevenLabs' `eleven_multilingual_v2` model
- Voice settings are configured with 0.5 stability and similarity boost
- The bot requires the Message Content intent to read messages
