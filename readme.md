# SamBot 🤖

### Setup & Installation
```bash
mkdir -p mount/cache
nano mount/settings.json
```

Write the following to `mount/settings.json`
```json
{
    "MentionEveryone": {
        "AllowedChats": []
    },
    "TikTokDl": {
        "BannedUsers": []
    },
    "L360": {
        "Assignments": {},
        "AllowedChats": []
    },
    "RemindMe": {
        "AllowedChats": []
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
      - LIFE360_USERNAME=LIFE360_USERNAME
      - LIFE360_PASSWORD=LIFE360_PASSWORD
```

When the application starts up for the first time it will send an OTP code to either your telegram account or to your phone via SMS. Once you get the code, enter it into `mount/otp.code` file. This will create a new session. To test if you have successfully set everything up, you can try sending the message `.ping` to any chat and the message will be automatically edited to show information about the uptime of the bot



## Pipeline Segments (Features)

- `PingIndicator`: This segment is used to check if the bot is up. Can be triggered by sending the message `.ping` to any chat


- `TikTokDownloader`: This segment is used to download videos from links. To download things, the package [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) is used, it will work with TikTok, Instagram and YouTube. Check the package website for more information. The module can be triggered by replying to a message that contains a link with `.dl`.
- `MentionEveryone`: This segment is used to mention everyone in the chat. Mention @everyone within a chat to mention everyone in the chat. To avoid this being triggered in other chats, a whitelist is used. To add a chat send the command `.config mentioneveryone add` to a chat and now that chat will support mentioning everyone
- `BackTrace`: This segment fetches the last 100 messages sent in a chat and has ChatGPT summarize it and send it back in the chat. Can be triggered by sending `.backtrace` in a chat
- `Autopilot`: Not gonna even bother with this
- `TerminateSegment`: This will terminate the bot when `.terminate` is sent the by host
- `WordCloudGenerator`: This will generate a wordcloud from the last 24 hours
- `ReactionCounter`: This will generate a leaderboard with group chat members who yapped the most and who got the most number of reactions
- `WhoIsNoora`: Using this segment, we might finally uncover the mystery of who Noora is
- `Life360Integration`: Using this you can integrate Life360 and get users location by sending `.whereis @username` For this to work, you need the environment variables `Life360_Username` and `Life360_Password` set. You are going to need to also link each user to their Life360 account by replying to a users message `.config whereis setuser {CircleName}/{Username}` where `CircleName` is the circle the user is in and the `Username` is the firstname of the user
- `RemindMe`: Using this segment you can set reminders. To use it, send `.remindme 30s {reminder text here}`. You can use multiple time units for example `.remindme 2m30s Reminder for 2 minutes 30 seconds!`. To enable reminders for a chat, you can send `.config remindme allow` and to disable you can send `.config remindme disallow`



## More stuff

- [Adding new Segments](docs/adding-new-segments.md)
