# Discord TTS Bot

A personal Discord bot that automatically reads messages for one user aloud in a voice channel using ElevenLabs API.

## Commands

- `/tts_join` - Manually join your current voice channel
- `/tts_leave` - Leave the voice channel
- `/tts_test <text>` - Test TTS with a custom message
- `/tts_status` - Display bot statistics and health
- `/tts_restart` - Restart the bot (requires Administrator)

NOTE: `/tts_restart` only restarts a systemd service

### Prerequisites

- Python 3.8 - 3.12
- ffmpeg
- Discord Bot Token
- ElevenLabs API Key

### Installation

```bash
git clone https://github.com/Grang404/cyborgee
cd cyborgee
pip install -r requirements.txt
python main.py
```

### Create a `.env` file in the root directory:

```env
BOT_KEY=your_discord_bot_token
API_KEY=your_elevenlabs_api_key
VOICE_ID=your_elevenlabs_voice_id
TARGET_USER=discord_user_id_to_read
TARGET_SERVER=discord_server_id
```
