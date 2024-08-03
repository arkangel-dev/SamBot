# SamBot 🤖

### Setup & Installation
```bash
mkdir -p mount/cache
nano mount/settings.json
```

Write the following to `mount/settings.json`
```json
{
    "mentioneveryone": {
        "allowed_chats": []
    }
}
```

Write this to `compose.yaml` 

```yaml
version: '3'
services:
  web:
    build: .
    image: ghcr.io/arkangel-dev/sambot:latest
    volumes:
      - ./ext-mount:/app/ext-mount
    environment:
      - PYROGRAM_PHONENUMBER=PHONE_NUMBER_HERE
      - PYROGRAM_APIID=API_ID
      - PYROGRAM_APIHASH=API_HASH
      - CHATGPT_USERNAME=CHAT_GPT_USERNAME
      - CHATGPT_PASSWORD=CHAT_GPT_PASSWORD
```

When the application starts up for the first time it will send an OTP code to either your telegram account or to your phone via SMS. Once you get the code, enter it into `mount/otp.code` file. This will create a new session. To test if you have successfully set everything up, you can try sending the message `.ping` to any chat and the message will be automatically edited to show information about the uptime of the bot



## Pipeline Segments (Features)

- `PingIndicator`: This segment is used to check if the bot is up. Can be triggered by sending the message `.ping` to any chat


- `TikTokDownloader`: This segment is used to download videos from links. To download things, the package [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) is used, it will work with TikTok, Instagram and YouTube. Check the package website for more information. The module can be triggered by replying to a message that contains a link with `.dl`.
- `MentionEveryone`: This segment is used to mention everyone in the chat. Mention @everyone within a chat to mention everyone in the chat. To avoid this being triggered in other chats, a whitelist is used. To add a chat send the command `.config mentioneveryone add` to a chat and now that chat will support mentioning everyone
- `BackTrace`: This segment fetches the last 100 messages sent in a chat and has ChatGPT summarize it and send it back in the chat. Can be triggered by sending `.backtrace` in a chat
- `Autopilot`: Not gonna even bother with this



## More stuff

- [Adding new Segments](docs/adding-new-segments.md)
